"""How many trades should the 2026-27 trader actually place?

Three multiplicative stages, measured not guessed:

  A  SIGNAL COUNT   per strategy per season, from MONITOR_SEASON_PNL.md and
                    PREREG_2026_27_PROSPECTIVE.md (historical, 8 and 3 seasons).
  B  HARD GATES     one trade per game (nba_live_trader claims `claimed[ev]`),
                    and NO-side blocked while NBA_NO_SIDE_VERIFIED is unset,
                    which removes every UNDER from PaceGap and MOVE.
  C  PRICE GATES    MIN_EDGE / MIN_PRICE / MAX_PRICE / MAX_SIGMA_DIST /
                    MIN_BOOK_SIZE, measured by replaying the REAL
                    candidates() and gate() from nba_live_trader against the
                    1,312 real pregame ladders of 2025-26.

Stage C is run in BOTH modes because they are different businesses:
  MAKE (the current default) posts at bid/bid+tick -- the spread becomes edge,
       but the order has to be FILLED to become a trade.
  TAKE (--take) lifts the ask -- fills are immediate but the edge pays the
       half-spread and the fee.

sigma comes from the EXECUTABLE BOUNDS identified set, never a midpoint, so
this measurement does not reproduce the defect it is measuring.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
TICK_SLACK = 0.005
BIG = 1e9
GAMES_REG = 1230

ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

# ---- A. signal counts per season (documented) ---------------------------
STRATS = {
    #                 hit     sides        signals/season   source
    'crewshock': dict(hit=0.5421, two=False, n=174, rng=(92, 238),
                      src='MONITOR_SEASON_PNL 8-season mean of 1,390'),
    'pacegap':   dict(hit=0.5259, two=True, n=352, rng=(330, 375),
                      src='PREREG_2026_27 n=1,056 over 3 seasons, 30.3% of slate'),
    'move':      dict(hit=0.5344, two=True, n=350, rng=(300, 400),
                      src='MONITOR_SEASON_PNL "~350 MOVE_COMBINED bets"'),
    'final7':    dict(hit=0.5529, two=False, n=67, rng=(62, 69),
                      src='MONITOR_SEASON_PNL 527 over 8 seasons'),
}
for k, v in STRATS.items():
    v['delta'] = T.delta_points(v['hit'])

print("=" * 76)
print("A. SIGNALS PER SEASON (documented historical rates)")
print("=" * 76)
print(f"  {'strategy':>10s} {'hit':>7s} {'delta pts':>10s} {'signals':>8s} {'range':>12s} {'sides':>6s}")
for k, v in STRATS.items():
    print(f"  {k:>10s} {v['hit']:7.4f} {v['delta']:10.3f} {v['n']:8d} "
          f"{str(v['rng']):>12s} {'2' if v['two'] else '1':>6s}")
print(f"  raw total {sum(v['n'] for v in STRATS.values())}")

# ---- B. hard structural gates -------------------------------------------
print("\n" + "=" * 76)
print("B. HARD GATES -- one trade per game, and NO-side blocked")
print("=" * 76)
for k, v in STRATS.items():
    v['tradeable'] = v['n'] // 2 if v['two'] else v['n']
    if v['two']:
        print(f"  {k:>10s} {v['n']:4d} -> {v['tradeable']:4d}  "
              f"(UNDER half blocked: NO-side unverified)")
    else:
        print(f"  {k:>10s} {v['n']:4d} -> {v['tradeable']:4d}  (OVER-only already)")
print(f"  tradeable signals {sum(v['tradeable'] for v in STRATS.values())}")

p_fire = {k: v['tradeable'] / GAMES_REG for k, v in STRATS.items()}
season_long = ['crewshock', 'pacegap', 'move']
p_none = np.prod([1 - p_fire[k] for k in season_long])
u_long = GAMES_REG * (1 - p_none)
u_f7 = STRATS['final7']['tradeable'] * p_none        # only unclaimed final-week games
union = u_long + u_f7
print(f"\n  one-trade-per-game collapses the sum to a UNION:")
print(f"    P(no season-long signal) = {p_none:.4f}")
print(f"    games with >=1 tradeable signal = {u_long:.0f} + {u_f7:.0f} (final7) "
      f"= {union:.0f}")
print(f"    vs {sum(v['tradeable'] for v in STRATS.values())} tradeable signals "
      f"-- {sum(v['tradeable'] for v in STRATS.values())-union:.0f} lost to claiming")

# ---- C. price gates, replayed on real ladders ---------------------------
print("\n" + "=" * 76)
print("C. PRICE GATES on 1,312 REAL pregame ladders (2025-26)")
print("=" * 76)
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                          m.pregame_yes_bid b, m.pregame_yes_ask a,
                          e.game_date, e.away_team, e.home_team
                   FROM markets m JOIN events e USING(event_ticker)
                   WHERE m.pregame_yes_bid IS NOT NULL
                     AND m.pregame_yes_ask IS NOT NULL
                     AND m.floor_strike IS NOT NULL""", con)
con.close()
m['L'], m['U'] = m.b / 100.0, m.a / 100.0

raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
ms = pd.DataFrame({'ds': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
                   'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
                   'close': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
                   'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce')}).dropna()
m['h'] = m.home_team.map(ABBR); m['r'] = m.away_team.map(ABBR)
m = m.merge(ms, left_on=['game_date', 'h', 'r'], right_on=['ds', 'h', 'r'], how='inner')
print(f"  ladders joined to a posted line: {m.ev.nunique()} events")


def sigma_from_bounds(K, L, U):
    """Centre of the executable-bounds identified sigma set. NO midpoint."""
    Lo = np.clip(L - TICK_SLACK, 1e-9, 1 - 1e-9)
    Up = np.clip(U + TICK_SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return None
    return float(np.median(SIG_GRID[ok]))


rows = []
for ev, g in m.groupby('ev'):
    g = g.sort_values('K')
    K, L, U = g.K.values, g.L.values, g.U.values
    sig = sigma_from_bounds(K, L, U)
    if sig is None:
        sig = T.SIGMA_REF                      # fall back, as the trader would
    rungs = [dict(strike=float(k), ticker=t,
                  yes_ask=float(aa), yes_ask_size=50.0,
                  yes_bid=float(bb), yes_bid_size=50.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for k, t, bb, aa in zip(g.K, g.ticker, g.U * 0 + g.L, g.U)]
    # the trader stores yes_bid/yes_ask in DOLLARS; rebuild faithfully
    rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                  yes_bid_size=50.0, yes_ask_size=50.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
    for name, v in STRATS.items():
        ref = g['close'].iloc[0] if name in ('crewshock', 'final7') else g['open'].iloc[0]
        mu_hat = ref + v['delta']                       # OVER only
        for take in (False, True):
            cands = T.candidates(rungs, mu_hat, sig, ('OVER',), take=take)
            st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
            ok = [c for c in cands if T.gate(c, st) is None]
            rows.append(dict(ev=ev, strat=name, take=take, sigma=sig,
                             n_cand=len(cands), n_pass=len(ok),
                             best=max((c['edge'] for c in cands), default=np.nan)))
R = pd.DataFrame(rows)
print(f"\n  {'strategy':>10s} {'mode':>5s} {'events':>7s} {'% with a PASSING rung':>22s} "
      f"{'median best edge':>17s}")
passrate = {}
for (s, tk), g in R.groupby(['strat', 'take']):
    pr = (g.n_pass > 0).mean()
    passrate[(s, tk)] = pr
    print(f"  {s:>10s} {'TAKE' if tk else 'MAKE':>5s} {len(g):7d} {100*pr:21.1f}% "
          f"{g.best.median()*100:16.2f}c")

# ---- expected trades ----------------------------------------------------
print("\n" + "=" * 76)
print("EXPECTED TRADES PER SEASON")
print("=" * 76)
for tk in (False, True):
    lab = 'TAKE (ask)' if tk else 'MAKE (bid) -- ORDERS placed, not fills'
    eff = {k: STRATS[k]['tradeable'] * passrate[(k, tk)] for k in STRATS}
    pf = {k: eff[k] / GAMES_REG for k in STRATS}
    pn = np.prod([1 - pf[k] for k in season_long])
    tot = GAMES_REG * (1 - pn) + eff['final7'] * pn
    print(f"\n  {lab}")
    for k in STRATS:
        print(f"    {k:>10s} {STRATS[k]['tradeable']:4d} tradeable x "
              f"{100*passrate[(k,tk)]:5.1f}% = {eff[k]:6.1f}")
    print(f"    after one-trade-per-game union: {tot:.0f} per season")
    if not tk:
        for fill in (0.25, 0.50):
            print(f"      x {fill:.0%} fill rate -> {tot*fill:.0f} actual trades")

R.to_csv('/home/dpope/projects/nba_entropy_replication/expected_trade_count_detail.csv',
         index=False)
print("\n[detail -> expected_trade_count_detail.csv]")
