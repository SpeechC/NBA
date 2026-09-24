"""Event-level sigma from REPEATED shifted ladders, with no midpoint.

The identified set from ONE snapshot is ~1.0 pt of sigma wide, mostly because
KXNBATOTAL quotes on a 1c grid. As mu_t drifts, the SAME sigma is rounded onto
DIFFERENT cent grids, so rounding error decorrelates across snapshots while
sigma does not. Intersecting the per-snapshot feasible sets should tighten the
band without ever averaging a bid and an ask.

THREE RESTRICTIONS, imposed by design:

 1  DISTINCT BOOK STATES ONLY. A quote sitting unchanged for four hours is one
    constraint, not four hundred. Snapshots are de-duplicated on the exact
    (L, U) vector across the ladder, and optionally thinned further by
    requiring the implied location interval to have MOVED by >= MIN_MU_MOVE.
    Reported against the raw minute count so the shrinkage cannot be an artefact
    of recounting one constraint.

 2  SIGMA STABILITY IS TESTED, NOT ASSUMED. Common-sigma is plausible over a few
    pregame hours and implausible across weeks as lineups and injuries land.
    Sigma is identified SEPARATELY in an early and a late window and the two are
    compared BEFORE any pooled estimate is reported.

 3  NORMAL IS THE DEFAULT SHAPE, tick-aware. The frozen empirical shape fit
    WORSE (22.9% vs 29.9% on identical grids) and is not resurrected. Skew is
    introduced only if repeated-snapshot residuals demand it.

CLOSED FORM. For rung K with executable bounds [L, U]:
    L <= 1 - Phi((K-mu)/sigma) <= U   <=>   mu in [K - sigma*z_L, K - sigma*z_U]
with z_L = Phi^-1(1-L), z_U = Phi^-1(1-U). A snapshot is feasible at sigma iff
those per-rung intervals intersect. No mu grid, and no midpoint anywhere.
"""
import sqlite3, argparse, numpy as np, pandas as pd
from scipy.stats import norm

CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG = np.arange(9.0, 30.001, 0.05)
TICK_SLACK = 0.005          # +/-0.5c: the 1c grid's own rounding unit
BIG = 1e9
RNG = np.random.default_rng(31)

ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}


def load():
    con = sqlite3.connect('file:' + CAND + '?mode=ro', uri=True)
    c = pd.read_sql("""SELECT event_ticker ev, ticker, end_period_ts ts,
                              strike_label K, yes_bid_close b, yes_ask_close a
                       FROM candles WHERE period_interval=1""", con)
    mk = pd.read_sql("SELECT DISTINCT ticker, floor_strike FROM markets", con)
    con.close()
    # tipoff_ts is NULL throughout the candles DB; the totals DB carries it
    # from the schedule for 5,747 of 5,900 markets.
    con2 = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    tip = pd.read_sql("SELECT DISTINCT event_ticker ev, tipoff_ts FROM markets "
                      "WHERE tipoff_ts IS NOT NULL", con2)
    con2.close()
    c = c.merge(mk, on='ticker', how='left')
    c['K'] = c.floor_strike.fillna(c.K)
    c = c.dropna(subset=['K', 'b', 'a'])
    c = c.merge(tip.groupby('ev').tipoff_ts.max().reset_index(), on='ev', how='left')
    c['L'] = c.b / 100.0
    c['U'] = c.a / 100.0
    c['hrs'] = (c.tipoff_ts - c.ts) / 3600.0
    return c


def sigma_set(K, L, U, slack=TICK_SLACK):
    """Boolean over SIG: is this single ladder snapshot feasible at each sigma?"""
    Lo = np.clip(L - slack, 1e-9, 1 - 1e-9)
    Up = np.clip(U + slack, 1e-9, 1 - 1e-9)
    zL = norm.ppf(1 - Lo)      # larger
    zU = norm.ppf(1 - Up)      # smaller
    zL = np.where(np.isfinite(zL), zL, BIG)
    zU = np.where(np.isfinite(zU), zU, -BIG)
    lo = K[None, :] - SIG[:, None] * zL[None, :]
    hi = K[None, :] - SIG[:, None] * zU[None, :]
    return lo.max(axis=1) <= hi.min(axis=1) + 1e-9


def event_states(g, min_move):
    """Distinct book states, ordered in time, optionally thinned by mu movement."""
    piv_b = g.pivot_table(index='ts', columns='K', values='L')
    piv_a = g.pivot_table(index='ts', columns='K', values='U')
    idx = piv_b.index.intersection(piv_a.index)
    piv_b, piv_a = piv_b.loc[idx].ffill(), piv_a.loc[idx].ffill()
    ok = piv_b.notna().all(axis=1) & piv_a.notna().all(axis=1)
    piv_b, piv_a = piv_b[ok], piv_a[ok]
    if len(piv_b) == 0:
        return None, None, None, 0
    key = np.concatenate([piv_b.values, piv_a.values], axis=1)
    keep = np.ones(len(key), bool)
    keep[1:] = (np.abs(np.diff(key, axis=0)) > 1e-12).any(axis=1)
    piv_b, piv_a = piv_b[keep], piv_a[keep]
    K = piv_b.columns.values.astype(float)
    if min_move > 0 and len(piv_b) > 1:
        # crude executable location proxy: strike where the book brackets 50c,
        # taken from the BOUNDS, never a midpoint
        loc = []
        for i in range(len(piv_b)):
            L, U = piv_b.values[i], piv_a.values[i]
            below = K[U < 0.5]
            above = K[L > 0.5]
            lo = above.max() if len(above) else K.min()
            hi = below.min() if len(below) else K.max()
            loc.append((lo + hi) / 2.0)
        loc = np.array(loc)
        sel = [0]
        for i in range(1, len(loc)):
            if abs(loc[i] - loc[sel[-1]]) >= min_move:
                sel.append(i)
        piv_b, piv_a = piv_b.iloc[sel], piv_a.iloc[sel]
    return K, piv_b.values, piv_a.values, len(piv_b)


def band(K, Lm, Um):
    """Intersect feasible sigma sets over all snapshots."""
    if Lm is None or len(Lm) == 0:
        return None
    feas = np.ones(len(SIG), bool)
    for i in range(len(Lm)):
        feas &= sigma_set(K, Lm[i], Um[i])
        if not feas.any():
            return None
    w = np.where(feas)[0]
    return SIG[w.min()], SIG[w.max()], len(w)


def main(lo_h, hi_h, min_move, max_states):
    c = load()
    c = c[(c.hrs >= hi_h) & (c.hrs <= lo_h)]
    print(f"window T-{lo_h}h .. T-{hi_h}h   rows {len(c):,}   events {c.ev.nunique()}")
    out = []
    for ev, g in c.groupby('ev'):
        raw_min = g.ts.nunique()
        K, Lm, Um, ns = event_states(g, min_move)
        if K is None or len(K) < 4 or ns == 0:
            continue
        if ns > max_states:                       # spread evenly across the window
            pick = np.linspace(0, ns - 1, max_states).astype(int)
            Lm, Um, ns = Lm[pick], Um[pick], max_states
        r1 = band(K, Lm[:1], Um[:1])              # first snapshot alone
        rA = band(K, Lm, Um)                      # all admitted snapshots
        out.append(dict(ev=ev, raw_min=raw_min, states=ns,
                        one_lo=r1[0] if r1 else np.nan, one_hi=r1[1] if r1 else np.nan,
                        all_lo=rA[0] if rA else np.nan, all_hi=rA[1] if rA else np.nan))
    R = pd.DataFrame(out)
    if len(R) == 0:
        print("  no events in window"); return R
    R["one_w"] = R.one_hi - R.one_lo
    R['all_w'] = R.all_hi - R.all_lo
    fe = R.all_lo.notna()
    print(f"  events with a non-empty JOINT set: {fe.sum()} of {len(R)} "
          f"({100*fe.mean():.1f}%)")
    print(f"  raw minutes per event   median {R.raw_min.median():.0f}")
    print(f"  DISTINCT states used    median {R.states.median():.0f}")
    print(f"  band from ONE snapshot  median {R.one_w.median():.2f} pts")
    print(f"  band from ALL snapshots median {R.all_w.median():.2f} pts")
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-move", type=float, default=0.0)
    ap.add_argument("--max-states", type=int, default=60)
    a = ap.parse_args()

    print("=" * 74)
    print("RESTRICTION 2 FIRST: is sigma stable across the pregame window?")
    print("=" * 74)
    early = main(6.0, 3.0, a.min_move, a.max_states)
    print()
    late = main(1.0, 0.5, a.min_move, a.max_states)
    j = early.merge(late, on='ev', suffixes=('_e', '_l')).dropna(
        subset=['all_lo_e', 'all_lo_l'])
    print(f"\n  events with both windows identified: {len(j)}")
    if len(j):
        overlap = ((j.all_lo_e <= j.all_hi_l) & (j.all_lo_l <= j.all_hi_e))
        print(f"  early and late bands OVERLAP on {100*overlap.mean():.1f}% of events")
        mid_e = (j.all_lo_e + j.all_hi_e) / 2
        mid_l = (j.all_lo_l + j.all_hi_l) / 2
        d = mid_l - mid_e
        print(f"  late minus early band centre: mean {d.mean():+.3f} "
              f"median {d.median():+.3f} sd {d.std():.3f} pts")
        print(f"  -> common-sigma across the whole window is "
              f"{'SUPPORTED' if overlap.mean() > 0.8 else 'NOT SUPPORTED'}")
