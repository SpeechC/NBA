"""Is the NO side worth having AT ALL as a taker? Tested before anything is armed.

Only PaceGap and MOVE_COMBINED ever take the UNDER, and an UNDER is a NO buy.
Two things make the NO side structurally worse than the OVER side for a taker,
and both are measurable with zero money at risk:

  PRICE  no_ask == 1 - yes_bid, so lifting the NO ask pays the FULL spread
         measured on the YES book. There is no separate, tighter NO book.
  DEPTH  a NO buy consumes the YES BID book, so the size available is
         yes_bid_size -- the mirrored side, routinely far thinner than the
         quoted one. gate() enforces MIN_BOOK_SIZE=5 in take mode, so thin
         YES bids BLOCK the trade outright.

If NO-as-taker is not positive-EV with adequate depth, the schema probe is moot
and no order needs placing to establish that.

Outcome model mirrors the OVER work: a strategy claiming P(actual < L) = hit
implies actual = L + D - s with s = quantile(D, hit), so a NO at strike K wins
iff D < K - L + s. Empirical OT-skewed D, not a normal. No midpoint anywhere.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
STRATS = {'move': dict(hit=0.5344), 'pacegap': dict(hit=0.5259)}

# ---------------------------------------------------------------- 1. LIVE DEPTH
print("=" * 78)
print("1. LIVE DEPTH -- can a NO take even clear MIN_BOOK_SIZE=5?")
print("=" * 78)
k = NK.NBAKalshi()
rows = []
for ev in k.open_events():
    for r in k.ladder(ev['event_ticker']):
        if r['yes_bid'] is None or r['yes_ask'] is None:
            continue
        rows.append(dict(ev=ev['event_ticker'], strike=r['strike'],
                         yes_bid=r['yes_bid'], yes_ask=r['yes_ask'],
                         yes_ask_size=r['yes_ask_size'] or 0,
                         no_ask=r['no_ask'], no_ask_size=r['no_ask_size'] or 0,
                         spread_c=round((r['yes_ask'] - r['yes_bid']) * 100)))
L = pd.DataFrame(rows)
print(f"  {len(L)} live rungs across {L.ev.nunique()} open events (26OCT07 board)")
print(f"  YES take (consumes yes_ask book): size >= 5 on "
      f"{100*(L.yes_ask_size >= 5).mean():5.1f}% of rungs, median {L.yes_ask_size.median():.0f}")
print(f"  NO  take (consumes yes_bid book): size >= 5 on "
      f"{100*(L.no_ask_size >= 5).mean():5.1f}% of rungs, median {L.no_ask_size.median():.0f}")
band = L[(L.no_ask >= 0.12) & (L.no_ask <= 0.88)]
print(f"  inside the 0.12-0.88 price band ({len(band)} rungs): NO size >= 5 on "
      f"{100*(band.no_ask_size >= 5).mean():.1f}%")
print(f"  median quoted spread {L.spread_c.median():.0f}c  "
      f"(the NO taker pays this in full; there is no separate NO book)")

# ---------------------------------------------------------------- 2. ECONOMICS
print("\n" + "=" * 78)
print("2. NO-SIDE TAKER ECONOMICS on 1,312 real pregame ladders")
print("=" * 78)
raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
base = pd.DataFrame({
    'ds': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
Dopen = np.sort((base.pts - base['open']).values)
for v in STRATS.values():
    v['delta'] = T.delta_points(v['hit'])
    v['s_over'] = float(-np.quantile(Dopen, 1.0 - v['hit']))   # P(D > -s) = hit
    v['s_under'] = float(np.quantile(Dopen, v['hit']))         # P(D <  s) = hit

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


def mu_sigma(K, Lo_, Up_):
    Lo = np.clip(Lo_ - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(Up_ + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return None, T.SIGMA_REF
    i = ok[len(ok) // 2]
    return float((lo[i] + hi[i]) / 2.0), float(SIG_GRID[i])


# MIN_BOOK_SIZE cannot be tested historically (no pregame sizes stored), so it
# is switched off here and reported separately from the live board above.
T.NO_SIDE_VERIFIED = True          # measure the economics as if the schema worked
out = []
for ev, g in m.groupby('ev'):
    g = g.sort_values('K')
    mu_mkt, sig = mu_sigma(g.K.values, g.L.values, g.U.values)
    rungs = [dict(strike=float(kk), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                  yes_bid_size=999.0, yes_ask_size=999.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for kk, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
    Lref, pts = g['open'].iloc[0], g.pts.iloc[0]
    for name, v in STRATS.items():
        for dirn in ('OVER', 'UNDER'):
            sgn = 1.0 if dirn == 'OVER' else -1.0
            if mu_mkt is not None and sgn * (mu_mkt - Lref) < -abs(v['delta']):
                out.append(dict(strat=name, dir=dirn, traded=False)); continue
            cands = T.candidates(rungs, Lref + sgn * v['delta'], sig, (dirn,), take=True)
            st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
            ok = [x for x in cands if T.gate(x, st) is None]
            if not ok:
                out.append(dict(strat=name, dir=dirn, traded=False)); continue
            x = ok[0]
            if dirn == 'OVER':
                pw = float(np.mean(Dopen > (x['strike'] - Lref - v['s_over'])))
                won = pts > x['strike']
            else:
                pw = float(np.mean(Dopen < (x['strike'] - Lref + v['s_under'])))
                won = pts < x['strike']
            fee = NK.fee(x['price'], 1)
            out.append(dict(strat=name, dir=dirn, traded=True, ask=x['price'],
                            believed=x['edge'], p_emp=pw,
                            ev=pw * (1 - x['price']) - (1 - pw) * x['price'] - fee,
                            outlay=x['price'] + fee,
                            pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee)))
R = pd.DataFrame(out)
print(f"  {'strategy':>9s} {'dir':>6s} {'pass%':>6s} {'ask':>6s} {'believed':>9s} "
      f"{'p_emp':>7s} {'EV/ct':>8s} {'ROI':>7s}")
for (s, d), g in R.groupby(['strat', 'dir']):
    t = g[g.traded]
    if not len(t):
        print(f"  {s:>9s} {d:>6s}   0.0%  (never passes)"); continue
    print(f"  {s:>9s} {d:>6s} {100*len(t)/len(g):5.1f}% {t.ask.mean():6.3f} "
          f"{t.believed.mean()*100:+8.2f}c {t.p_emp.mean():7.4f} "
          f"{t.ev.mean()*100:+7.2f}c {100*t.ev.mean()/t.outlay.mean():+6.2f}%")
print("\n  MIN_BOOK_SIZE disabled here (no pregame sizes stored); depth is the")
print("  separate live measurement in section 1 and applies on top.")
R.to_csv('/home/dpope/projects/nba_entropy_replication/no_side_taker_detail.csv', index=False)
