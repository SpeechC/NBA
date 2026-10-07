"""Taker-perspective P&L and ROI for the four live strategies.

STANDING CONSTRAINT: we are takers only. Every P&L/ROI number in this project
must therefore be computed at the ASK, with the fee, on a real book. The
previously quoted ~$19.70/season was a MAKER figure (edge measured against the
bid) and is superseded by this file.

METHOD -- no normal assumption, no midpoint.

  1  Real books. 1,312 actual pregame ladders from 2025-26, bid/ask only.
  2  Real outcome distribution. A strategy's published hit rate h is defined
     against the LINE, so write actual = L + D. Rather than assume D is normal,
     take the EMPIRICAL distribution of D from 2017-2025 (which carries the OT
     right-skew and the fat tails) and find the shift s with P(D > -s) = h.
     Then a rung at strike K wins with probability P(D > K - L - s).
  3  Taker pricing. Buy the max-edge rung AT THE ASK, pay
     ceil(0.07*p*(1-p)*n*1000)/1000, settle against the real distribution.

Reports the trader's OWN believed edge beside the empirical one, because the
trader prices rungs off a NORMAL. Where those diverge, the trader is
mis-sizing its own edge -- and the programme already knows the normal is wrong
in the direction of OT skew.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9
GAMES_REG = 1230

ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

STRATS = {
    'crewshock': dict(hit=0.5421, line='close', n_sig=174, two=False),
    'final7':    dict(hit=0.5529, line='close', n_sig=67,  two=False),
    'move':      dict(hit=0.5344, line='open',  n_sig=350, two=True),
    'pacegap':   dict(hit=0.5259, line='open',  n_sig=352, two=True),
}

# ---------------------------------------------------- empirical D and the shift
raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
base = pd.DataFrame({
    'ds': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'close': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
D = {k: np.sort((base.pts - base[k]).values) for k in ('close', 'open')}
for k, v in D.items():
    print(f"empirical D vs {k}: n={len(v)} mean {v.mean():+.3f} sd {v.std():.3f} "
          f"skew {pd.Series(v).skew():+.4f} P(D>0)={np.mean(v>0):.4f}")


def shift_for(hit, line):
    """s such that P(D > -s) = hit, on the EMPIRICAL distribution."""
    d = D[line]
    return float(-np.quantile(d, 1.0 - hit))


def p_win(K, L, s, line):
    """P(actual > K) = P(D > K - L - s) from the empirical distribution."""
    d = D[line]
    return float(np.mean(d > (K - L - s)))


print()
for k, v in STRATS.items():
    v['s'] = shift_for(v['hit'], v['line'])
    v['delta_norm'] = T.delta_points(v['hit'])
    print(f"  {k:>10s} hit {v['hit']:.4f}  empirical shift {v['s']:+.3f} pts   "
          f"normal delta {v['delta_norm']:+.3f} pts   gap {v['s']-v['delta_norm']:+.3f}")

# ---------------------------------------------------- real ladders
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                          m.pregame_yes_bid b, m.pregame_yes_ask a,
                          e.game_date, e.away_team, e.home_team
                   FROM markets m JOIN events e USING(event_ticker)
                   WHERE m.pregame_yes_bid IS NOT NULL AND m.pregame_yes_ask IS NOT NULL
                     AND m.floor_strike IS NOT NULL""", con)
con.close()
m['L'], m['U'] = m.b / 100.0, m.a / 100.0
m['h'] = m.home_team.map(ABBR); m['r'] = m.away_team.map(ABBR)
m = m.merge(base, left_on=['game_date', 'h', 'r'], right_on=['ds', 'h', 'r'], how='inner')
print(f"\nladders joined: {m.ev.nunique()} events")


def mu_sigma_bounds(K, L, U):
    """(mu, sigma) from the EXECUTABLE-bounds identified set. No midpoint.
    The trader's own fit_ladder() uses mids, which is a separate defect; this
    measurement must not reproduce it."""
    Lo = np.clip(L - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(U + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return None, T.SIGMA_REF
    i = ok[len(ok) // 2]
    return float((lo[i] + hi[i]) / 2.0), float(SIG_GRID[i])


def sigma_bounds(K, L, U):
    Lo = np.clip(L - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(U + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    return float(np.median(SIG_GRID[ok])) if len(ok) else T.SIGMA_REF


rows = []
for ev, g in m.groupby('ev'):
    g = g.sort_values('K')
    mu_mkt, sig = mu_sigma_bounds(g.K.values, g.L.values, g.U.values)
    rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                  yes_bid_size=50.0, yes_ask_size=50.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
    for name, v in STRATS.items():
        Lref = g[v['line']].iloc[0]
        mu_hat = Lref + v['delta_norm']                     # what the trader does
        # STALE-REFERENCE GUARD, as nba_live_trader.run() applies it: if the
        # market has moved further than our own delta AGAINST the bet, the
        # edge is already spent and the trade is declined. Omitting this
        # manufactures edge out of open-vs-close disagreement for the two
        # opener-settled strategies.
        if mu_mkt is not None and (Lref - mu_mkt) > abs(v['delta_norm']):
            rows.append(dict(ev=ev, strat=name, traded=False, declined_drift=True))
            continue
        cands = T.candidates(rungs, mu_hat, sig, ('OVER',), take=True)
        st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
        ok = [c for c in cands if T.gate(c, st) is None]
        if not ok:
            rows.append(dict(ev=ev, strat=name, traded=False))
            continue
        c = ok[0]                                           # highest believed edge
        pw = p_win(c['strike'], Lref, v['s'], v['line'])
        fee = NK.fee(c['price'], 1)
        ev_emp = pw * (1 - c['price']) - (1 - pw) * c['price'] - fee
        won = g.pts.iloc[0] > c['strike']
        pnl = (1 - c['price'] - fee) if won else (-c['price'] - fee)
        rows.append(dict(ev=ev, strat=name, traded=True, strike=c['strike'],
                         ask=c['price'], believed=c['edge'], p_model=c['p_model'],
                         p_emp=pw, ev_emp=ev_emp, fee=fee, won=bool(won), pnl=pnl,
                         outlay=c['price'] + fee))
R = pd.DataFrame(rows)
R.to_csv('/home/dpope/projects/nba_entropy_replication/taker_pnl_detail.csv', index=False)

print("\n" + "=" * 78)
print("TAKER ECONOMICS PER TRADE  (max-edge rung at the ASK, fee paid)")
print("=" * 78)
print(f"  {'strategy':>10s} {'boards':>7s} {'pass%':>6s} {'ask':>6s} {'believed':>9s} "
      f"{'p_model':>8s} {'p_emp':>7s} {'EV/ct':>8s}")
res = {}
for s, g in R.groupby('strat'):
    t = g[g.traded]
    pr = len(t) / len(g)
    res[s] = dict(pass_rate=pr, ask=t.ask.mean(), believed=t.believed.mean(),
                  p_model=t.p_model.mean(), p_emp=t.p_emp.mean(),
                  ev=t.ev_emp.mean(), outlay=t.outlay.mean())
    print(f"  {s:>10s} {len(g):7d} {100*pr:5.1f}% {t.ask.mean():6.3f} "
          f"{t.believed.mean()*100:+8.2f}c {t.p_model.mean():8.4f} "
          f"{t.p_emp.mean():7.4f} {t.ev_emp.mean()*100:+7.2f}c")
print("\n  'believed' is the trader's own edge off a NORMAL; EV/ct is the same")
print("  trade priced against the EMPIRICAL (OT-skewed) outcome distribution.")

print("\n" + "=" * 78)
print("SEASON PROJECTION AT 1 CONTRACT -- TAKER")
print("=" * 78)
eff = {s: STRATS[s]['n_sig'] // (2 if STRATS[s]['two'] else 1) * res[s]['pass_rate']
       for s in STRATS}
pf = {s: eff[s] / GAMES_REG for s in STRATS}
pn = np.prod([1 - pf[s] for s in ('crewshock', 'pacegap', 'move')])
n_f7 = eff['final7'] * pn
scale = {s: (eff[s] * (1 - 0) if s != 'final7' else n_f7) for s in STRATS}
# allocate the claiming loss proportionally among the three season-long strategies
long_sum = sum(eff[s] for s in ('crewshock', 'pacegap', 'move'))
long_union = GAMES_REG * (1 - pn)
for s in ('crewshock', 'pacegap', 'move'):
    scale[s] = eff[s] * long_union / long_sum
tot_n = sum(scale.values())
print(f"  {'strategy':>10s} {'trades':>7s} {'EV/ct':>8s} {'season EV':>10s} "
      f"{'outlay':>8s} {'ROI':>7s}")
tot_ev = tot_out = 0.0
for s in STRATS:
    e = scale[s] * res[s]['ev']
    o = scale[s] * res[s]['outlay']
    tot_ev += e; tot_out += o
    print(f"  {s:>10s} {scale[s]:7.0f} {res[s]['ev']*100:+7.2f}c {e:+10.2f} "
          f"{o:8.2f} {100*e/o if o else 0:+6.2f}%")
print(f"  {'TOTAL':>10s} {tot_n:7.0f} {'':8s} {tot_ev:+10.2f} {tot_out:8.2f} "
      f"{100*tot_ev/tot_out:+6.2f}%")
print(f"\n  (NO-side armed would add the UNDER half of pacegap and move;"
      f" trades ~471)")
print(f"  SUPERSEDES the ~$19.70 maker figure.")
