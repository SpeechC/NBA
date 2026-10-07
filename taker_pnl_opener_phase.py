"""Taker economics for the OPENER-settled strategies, on the 09:00 ET book.

taker_pnl_2026_27.py priced all four strategies off `pregame_*`, which is a
LATE pregame snapshot. That is the correct book for CrewShock and final7 (they
settle vs the CLOSE and fill near tip) but the WRONG book for PaceGap and
MOVE_COMBINED, which settle vs the OPENER and fill at 09:00 ET. Pricing an
opener strategy against a near-close book selects on open-to-close movement and
inflates the measured edge.

This rebuilds the 09:00 ET ladder from the 1-minute candles (429 events,
Oct-Dec 2025) and re-prices those two strategies there.

Same rules throughout: ASK only, fee paid, sigma and mu from the executable
bounds, the trader's own stale-reference guard applied, outcomes from the
EMPIRICAL (OT-skewed) distribution.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T
import nba_kalshi as NK

CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9
TARGET_UTC_HOUR = 13          # 09:00 EDT

ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
STRATS = {'move': dict(hit=0.5344, n_sig=350), 'pacegap': dict(hit=0.5259, n_sig=352)}

raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
base = pd.DataFrame({
    'ds': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
Dopen = np.sort((base.pts - base['open']).values)
for k, v in STRATS.items():
    v['s'] = float(-np.quantile(Dopen, 1.0 - v['hit']))
    v['delta'] = T.delta_points(v['hit'])
p_win = lambda K, L, s: float(np.mean(Dopen > (K - L - s)))

con = sqlite3.connect('file:' + CAND + '?mode=ro', uri=True)
c = pd.read_sql("""SELECT event_ticker ev, ticker, end_period_ts ts, game_date,
                          strike_label K, yes_bid_close b, yes_ask_close a
                   FROM candles WHERE period_interval=1""", con)
mk = pd.read_sql("SELECT DISTINCT ticker, floor_strike FROM markets", con)
con.close()
c = c.merge(mk, on='ticker', how='left')
c['K'] = c.floor_strike.fillna(c.K)
c = c.dropna(subset=['K', 'b', 'a'])
c['hour'] = pd.to_datetime(c.ts, unit='s', utc=True).dt.hour
c['date'] = pd.to_datetime(c.ts, unit='s', utc=True).dt.strftime('%Y-%m-%d')
# last quote at or before 09:00 ET on the game date
c = c[(c.date == c.game_date) & (c.hour <= TARGET_UTC_HOUR)]
c = c.sort_values('ts').groupby(['ev', 'ticker'], as_index=False).last()
print(f"09:00 ET books rebuilt for {c.ev.nunique()} events "
      f"({len(c)} rungs, median {len(c)/max(c.ev.nunique(),1):.1f} per event)")

ev_meta = {}
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
em = pd.read_sql("SELECT DISTINCT event_ticker ev, away_team, home_team, game_date FROM events", con)
con.close()
c = c.merge(em, on='ev', how='left')
c['h'] = c.home_team.map(ABBR); c['r'] = c.away_team.map(ABBR)
c = c.merge(base, left_on=['game_date_x', 'h', 'r'], right_on=['ds', 'h', 'r'], how='inner')
c['L'], c['U'] = c.b / 100.0, c.a / 100.0
print(f"joined to an opener: {c.ev.nunique()} events")


def mu_sigma(K, L, U):
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


rows = []
for ev, g in c.groupby('ev'):
    g = g.sort_values('K')
    if len(g) < 4:
        continue
    mu_mkt, sig = mu_sigma(g.K.values, g.L.values, g.U.values)
    rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                  yes_bid_size=50.0, yes_ask_size=50.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
    Lref, pts = g['open'].iloc[0], g.pts.iloc[0]
    for name, v in STRATS.items():
        if mu_mkt is not None and (Lref - mu_mkt) > abs(v['delta']):
            rows.append(dict(ev=ev, strat=name, traded=False)); continue
        cands = T.candidates(rungs, Lref + v['delta'], sig, ('OVER',), take=True)
        st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
        ok = [x for x in cands if T.gate(x, st) is None]
        if not ok:
            rows.append(dict(ev=ev, strat=name, traded=False)); continue
        x = ok[0]
        pw = p_win(x['strike'], Lref, v['s'])
        fee = NK.fee(x['price'], 1)
        rows.append(dict(ev=ev, strat=name, traded=True, ask=x['price'],
                         believed=x['edge'], p_model=x['p_model'], p_emp=pw,
                         ev_emp=pw * (1 - x['price']) - (1 - pw) * x['price'] - fee,
                         outlay=x['price'] + fee,
                         pnl=(1 - x['price'] - fee) if pts > x['strike'] else (-x['price'] - fee)))
R = pd.DataFrame(rows)
print("\n" + "=" * 74)
print("OPENER-SETTLED STRATEGIES ON THE 09:00 ET BOOK -- TAKER")
print("=" * 74)
print(f"  {'strategy':>10s} {'boards':>7s} {'pass%':>6s} {'ask':>6s} {'believed':>9s} "
      f"{'p_emp':>7s} {'EV/ct':>8s} {'realised/ct':>12s}")
for s, g in R.groupby('strat'):
    t = g[g.traded]
    if not len(t):
        print(f"  {s:>10s} {len(g):7d}   0.0%   --"); continue
    print(f"  {s:>10s} {len(g):7d} {100*len(t)/len(g):5.1f}% {t.ask.mean():6.3f} "
          f"{t.believed.mean()*100:+8.2f}c {t.p_emp.mean():7.4f} "
          f"{t.ev_emp.mean()*100:+7.2f}c {t.pnl.mean()*100:+11.2f}c")
print("\n  'realised/ct' is the actual 2025-26 settlement outcome of those very")
print("  trades -- a one-season read, n is small, treat as a sanity check only.")
R.to_csv('/home/dpope/projects/nba_entropy_replication/taker_pnl_opener_detail.csv', index=False)
