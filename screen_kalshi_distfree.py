"""Distribution-free ladder inference: is the 70% normal rejection a SHAPE
rejection, and does the executable book widen with the total?

Sequence (no midpoint anywhere, no normality assumed):

 1  EXECUTABLE INTERVALS.  L_K = max(YES bid, 1 - NO ask),
                           U_K = min(YES ask, 1 - NO bid).
    VERIFIED on 470 live markets across 4 series: no_bid == 1-yes_ask and
    no_ask == 1-yes_bid, 0 violations. The NO book is the mechanical
    complement, so the two-sided tightening collapses to [yes_bid, yes_ask].
    Step 1 is therefore satisfied exactly, not approximated.

 2  MONOTONE FEASIBILITY, distribution-free.  Does ANY decreasing survival
    curve fit inside the intervals?  Greedy is exact here: S_1 = U_1,
    S_j = min(U_j, S_{j-1}); feasible iff S_j >= L_j throughout.
    If nearly all ladders pass, the normal's 70% failure is a SHAPE rejection.
    If many fail, part of that "curvature" is stale/asynchronous cross-rung
    quoting, not distributional shape.

 3  NONPARAMETRIC QUANTILE WIDTH.  S is decreasing, so the crossing K*(s) of
    level s is bounded by
        K* >  max{K : L_K > s}      and      K* <  min{K : U_K < s}
    giving identified intervals for Q16 (s=.84), Q50 (s=.50), Q84 (s=.16) and
    the quartiles. W68 = Q84 - Q16 and IQR = Q75 - Q25 are pure widths; skew is
    allowed automatically.

 4  FROZEN EMPIRICAL SHAPE.  Rather than ask Kalshi to match a skew family, use
    the historical NBA residual distribution itself, standardised, as the shape:
        Y = m + s * D_hist        (D_hist frozen on 2017-2024, Kalshi is 2025-26)
    and identify which scale multipliers s are compatible with the envelope.
    Feasibility rising from 30% (normal) to high under this shape would say
    Kalshi's non-normality IS the historical higher-moment structure.

THE EVENT IS THE UNIT OF INFERENCE throughout. One pregame ladder per event.
"""
import sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

DB = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
RNG = np.random.default_rng(23)
FREEZE_END = 2024          # empirical shape frozen before the Kalshi season

ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT m.event_ticker, m.floor_strike K,
                          m.pregame_yes_bid b, m.pregame_yes_ask a,
                          e.game_date, e.away_team, e.home_team
                   FROM markets m JOIN events e USING(event_ticker)
                   WHERE m.pregame_yes_bid IS NOT NULL
                     AND m.pregame_yes_ask IS NOT NULL
                     AND m.floor_strike IS NOT NULL""", con)
con.close()
m['L'] = m.b / 100.0
m['U'] = m.a / 100.0

raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
ms = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'posted': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
ms['season'] = np.where(ms.date.dt.month >= 8, ms.date.dt.year, ms.date.dt.year - 1)
ms['D'] = ms.pts - ms.posted
ms['ds'] = ms.date.dt.strftime('%Y-%m-%d')
m['h'] = m.home_team.map(ABBR); m['r'] = m.away_team.map(ABBR)
m = m.merge(ms[['ds', 'h', 'r', 'posted', 'pts']], left_on=['game_date', 'h', 'r'],
            right_on=['ds', 'h', 'r'], how='inner')
print(f"rungs {len(m)}  events {m.event_ticker.nunique()}")

# ======================================================== 2. monotone feasible
def mono_feasible(L, U):
    """Exact: greedy upper envelope. Returns (ok, n_violations)."""
    s = U[0]; bad = 0
    for j in range(len(L)):
        s = min(s, U[j]) if j else U[0]
        if s < L[j] - 1e-12:
            bad += 1
            s = L[j]          # continue to count all violations
    return bad == 0, bad


recs = []
for ev, g in m.groupby('event_ticker'):
    g = g.sort_values('K')
    ok, bad = mono_feasible(g.L.values, g.U.values)
    body = g[(g.U <= 0.90) & (g.L >= 0.10)]
    okb, badb = (mono_feasible(body.L.values, body.U.values) if len(body) >= 3
                 else (None, None))
    recs.append(dict(event=ev, posted=g.posted.iloc[0], pts=g.pts.iloc[0],
                     n=len(g), mono=ok, nbad=bad, mono_body=okb,
                     maxw=(g.U - g.L).max(), medw_body=(body.U - body.L).median()
                     if len(body) else np.nan))
R = pd.DataFrame(recs)
print("\n" + "=" * 74)
print("2. DISTRIBUTION-FREE MONOTONE FEASIBILITY")
print("=" * 74)
print(f"  ALL rungs : {R.mono.mean()*100:5.1f}% of {len(R)} ladders admit a "
      f"monotone survival curve inside their executable quotes")
print(f"  BODY only : {R.mono_body.mean()*100:5.1f}%")
print(f"  among failures, median violated rungs {R.loc[~R.mono,'nbad'].median():.0f} "
      f"of {R.n.median():.0f}")
print(f"  -> normal feasibility was 30.1%.  Gap to monotone feasibility is the "
      f"SHAPE rejection;\n     any monotone failure is stale/asynchronous cross-rung quoting.")

# ======================================================== 3. quantile widths
def cross_bounds(K, L, U, s):
    """(lo, hi) bracketing the strike where the survival curve crosses s."""
    below = K[U < s - 1e-12]
    above = K[L > s + 1e-12]
    hi = below.min() if len(below) else np.nan
    lo = above.max() if len(above) else np.nan
    return lo, hi


LEVELS = {'Q16': 0.84, 'Q25': 0.75, 'Q50': 0.50, 'Q75': 0.25, 'Q84': 0.16}
qrows = []
for ev, g in m.groupby('event_ticker'):
    g = g.sort_values('K')
    K, L, U = g.K.values, g.L.values, g.U.values
    d = dict(event=ev, posted=g.posted.iloc[0])
    for nm, s in LEVELS.items():
        lo, hi = cross_bounds(K, L, U, s)
        d[nm + '_lo'], d[nm + '_hi'] = lo, hi
    qrows.append(d)
Q = pd.DataFrame(qrows)
Q['W68_lo'] = Q.Q84_lo - Q.Q16_hi
Q['W68_hi'] = Q.Q84_hi - Q.Q16_lo
Q['IQR_lo'] = Q.Q75_lo - Q.Q25_hi
Q['IQR_hi'] = Q.Q75_hi - Q.Q25_lo

print("\n" + "=" * 74)
print("3. NONPARAMETRIC QUANTILE WIDTHS FROM THE ENVELOPE")
print("=" * 74)
for nm in ('W68', 'IQR'):
    idf = Q[[nm + '_lo', nm + '_hi']].notna().all(axis=1)
    print(f"  {nm}: identified on both sides for {idf.sum()} of {len(Q)} events "
          f"({100*idf.mean():.1f}%)")
    if idf.sum():
        sub = Q[idf]
        print(f"       band width median {(sub[nm+'_hi']-sub[nm+'_lo']).median():.2f} pts")

# realised conditional widths from the box scores
print("\n  realised vs executable, by posted-total tercile:")
ok = Q[Q[['W68_lo', 'W68_hi', 'IQR_lo', 'IQR_hi']].notna().all(axis=1)].copy()
allg = ms.dropna(subset=['D']).copy()
if len(ok) > 30:
    ok['tb'] = pd.qcut(ok.posted, 3, duplicates='drop')
    allg['tb'] = pd.cut(allg.posted, pd.IntervalIndex(ok.tb.cat.categories))
    print(f"    {'posted':>16s} {'n_k':>5s} {'W68 book lo':>12s} {'W68 book hi':>12s} "
          f"{'W68 realised':>13s} {'n_hist':>7s}")
    for b in ok.tb.cat.categories:
        kk = ok[ok.tb == b]; hh = allg[allg.tb == b]
        if len(hh) < 50:
            continue
        w = np.percentile(hh.D, 84) - np.percentile(hh.D, 16)
        print(f"    {str(b):>16s} {len(kk):5d} {kk.W68_lo.mean():12.2f} "
              f"{kk.W68_hi.mean():12.2f} {w:13.2f} {len(hh):7d}")

# ======================================================== 4. frozen empirical shape
print("\n" + "=" * 74)
print(f"4. FROZEN EMPIRICAL SHAPE  (D_hist from seasons <= {FREEZE_END})")
print("=" * 74)
hist = ms[(ms.season <= FREEZE_END)].D.values
hist = hist[np.isfinite(hist)]
centre, scale = np.median(hist), hist.std()
Dstd = np.sort((hist - centre) / scale)
print(f"  n={len(Dstd)}  skew {pd.Series(hist).skew():+.4f}  "
      f"kurtosis {pd.Series(hist).kurtosis():+.4f}  sd {scale:.3f}")
print(f"  (a normal would be skew 0.0000, excess kurtosis 0.0000)")

MG = np.arange(-9.0, 9.01, 0.5)      # location offset from the ladder centre
SG = np.arange(0.55, 1.85, 0.02)     # scale multiplier on the frozen shape


def emp_surv(x):
    """P(Dstd > x) from the frozen empirical shape."""
    return 1.0 - np.searchsorted(Dstd, x, side='right') / len(Dstd)


fe = []
for ev, g in m.groupby('event_ticker'):
    g = g.sort_values('K')
    K, L, U = g.K.values, g.L.values, g.U.values
    c0 = K.mean()
    mm = c0 + MG
    # p[i,j,k] = P(Y > K_k) with m=mm[i], s=SG[j]
    z = (K[None, None, :] - mm[:, None, None]) / (SG[None, :, None] * scale)
    p = emp_surv(z)
    feas = ((p >= L[None, None, :] - 1e-12) & (p <= U[None, None, :] + 1e-12)).all(axis=2)
    d = dict(event=ev, posted=g.posted.iloc[0], feas=bool(feas.any()))
    if feas.any():
        si = np.where(feas.any(axis=0))[0]
        d['s_lo'], d['s_hi'] = SG[si.min()], SG[si.max()]
    fe.append(d)
F = pd.DataFrame(fe)
print(f"\n  FEASIBILITY under the frozen empirical shape: "
      f"{F.feas.mean()*100:.1f}%  ({F.feas.sum()} of {len(F)})")
print(f"  versus                       normal shape:  30.1%")

G = F.dropna(subset=['s_lo'])
if len(G) > 50:
    print(f"\n  identified scale band: median width "
          f"{(G.s_hi-G.s_lo).median():.3f}   s_lo med {G.s_lo.median():.3f}  "
          f"s_hi med {G.s_hi.median():.3f}")
    G = G.copy(); G['tb'] = pd.qcut(G.posted, 5, duplicates='drop')
    print(f"\n  {'posted total':>14s} {'n':>5s} {'s_lo':>7s} {'s_hi':>7s}")
    for b, gg in G.groupby('tb', observed=True):
        print(f"  {gg.posted.mean():14.1f} {len(gg):5d} {gg.s_lo.mean():7.3f} "
              f"{gg.s_hi.mean():7.3f}")

    def sl(x, y, nb=2000):
        s = np.polyfit(x, y, 1)[0]
        d = [np.polyfit(x[i], y[i], 1)[0]
             for i in (RNG.integers(0, len(x), len(x)) for _ in range(nb))]
        return s, *np.percentile(d, [2.5, 97.5])
    for nm, col in (('s_lo', 's_lo'), ('s_hi', 's_hi')):
        s, lo, hi = sl(G.posted.values, G[col].values)
        print(f"  slope of {nm} per point of total: {s:+.6f} CI [{lo:+.6f},{hi:+.6f}]")
    # what the realised scaling requires, in the same multiplier units
    allg2 = ms.dropna(subset=['D']).copy()
    allg2['tb'] = pd.qcut(allg2.posted, 8, duplicates='drop')
    rr = allg2.groupby('tb', observed=True).agg(mid=('posted', 'mean'), sd=('D', 'std'))
    req = np.polyfit(rr.mid, rr.sd / scale, 1)[0]
    print(f"  REQUIRED by realised dispersion:       {req:+.6f} "
          f"(= +{req*scale:+.5f} sigma pts/pt)")
