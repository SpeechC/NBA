"""2025-26: sportsbook -110 vs Kalshi taker, on MATCHED games.

Same season, same signals, same code path for the signal construction, so the
only thing varying is the instrument. That isolates the venue effect from the
season effect -- which the pre-2025-26 table cannot do.

Three rows per strategy:
  SB  all signals   the -110 basis on every signal, as the backtests report it
  SB  matched       the -110 basis on ONLY the games Kalshi actually traded
                    (the gate refuses some), so the comparison is like-for-like
  KALSHI taker      max-edge rung at the ASK, fee paid, settled on the actual

Stakes differ by construction -- $100 flat vs 1 contract at ~47c -- so ROI is
the comparable column. Kalshi P&L is also shown rescaled to a $100 stake per
trade purely for intuition; it is NOT a capacity claim.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
sys.path.insert(0, '.')
import nba_live_trader as T
import nba_kalshi as NK
from prepare_data import read_master, season_label

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9
WIN110, LOSE110 = 100.0 / 1.1, -100.0
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
DELTA = {'crewshock': T.delta_points(0.5421), 'final7': T.delta_points(0.5529)}

# ---------------------------------------------------------------- master, 2025-26
raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
S = d[d.season == 2025]
print(f"2025-26 regular season: {len(S)} games")

# ---------------------------------------------------------------- signals
cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
sig = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']],
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']]}
for k, v in sig.items():
    print(f"  {k}: {len(v)} signals")

# ---------------------------------------------------------------- Kalshi book
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
bk = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                           m.pregame_yes_bid b, m.pregame_yes_ask a,
                           e.game_date ds, e.away_team, e.home_team
                    FROM markets m JOIN events e USING(event_ticker)
                    WHERE m.pregame_yes_bid IS NOT NULL
                      AND m.pregame_yes_ask IS NOT NULL
                      AND m.floor_strike IS NOT NULL""", con)
con.close()
bk['L'], bk['U'] = bk.b / 100.0, bk.a / 100.0
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)


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


def run(strat):
    j = sig[strat].merge(bk, on=['ds', 'h', 'r'], how='inner')
    rows = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty or len(g) < 4:
            continue
        Lref, pts = float(m.close.iloc[0]), float(m.actual.iloc[0])
        mu_mkt, sg = mu_sigma(g.K.values, g.L.values, g.U.values)
        sb_won, sb_push = pts > Lref, pts == Lref
        if mu_mkt is not None and (Lref - mu_mkt) > abs(DELTA[strat]):
            rows.append(dict(traded=False, sb_won=sb_won, sb_push=sb_push)); continue
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
        c = [x for x in T.candidates(rungs, Lref + DELTA[strat], sg, ('OVER',))
             if T.gate(x, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not c:
            rows.append(dict(traded=False, sb_won=sb_won, sb_push=sb_push)); continue
        x = c[0]; fee = NK.fee(x['price'], 1); won = pts > x['strike']
        rows.append(dict(traded=True, sb_won=sb_won, sb_push=sb_push, won=bool(won),
                         strike=x['strike'], ask=x['price'],
                         pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                         outlay=x['price'] + fee))
    return pd.DataFrame(rows)


def sb(sub):
    b = sub[~sub.sb_push]
    p = np.where(b.sb_won, WIN110, LOSE110)
    return len(b), b.sb_won.mean(), p.sum(), p.sum() / (100 * len(b))


print("\n" + "=" * 86)
print("2025-26  -- SPORTSBOOK -110  vs  KALSHI TAKER, matched games")
print("=" * 86)
tot = {}
for strat in ('crewshock', 'final7'):
    R = run(strat)
    t = R[R.traded]
    n_a, h_a, p_a, roi_a = sb(R)
    n_m, h_m, p_m, roi_m = sb(t)
    kn, kh = len(t), t.won.mean()
    kp, ko = t.pnl.sum(), t.outlay.sum()
    tot[strat] = (n_m, p_m, kn, kp, ko)
    print(f"\n  {strat.upper()}")
    print(f"    {'basis':<26}{'n':>5}{'hit%':>9}{'P&L':>11}{'ROI':>9}")
    print(f"    {'SB -110, all signals':<26}{n_a:>5}{100*h_a:>8.2f}%{p_a:>+11.0f}{100*roi_a:>+8.2f}%")
    print(f"    {'SB -110, matched':<26}{n_m:>5}{100*h_m:>8.2f}%{p_m:>+11.0f}{100*roi_m:>+8.2f}%")
    print(f"    {'KALSHI taker, matched':<26}{kn:>5}{100*kh:>8.2f}%{kp:>+11.2f}{100*kp/ko:>+8.2f}%")
    print(f"    gate refused {n_a - n_m} of {n_a} signals;  "
          f"hit% line->rung {100*h_m:.2f} -> {100*kh:.2f} "
          f"({100*(kh-h_m):+.2f}pp);  ROI {100*roi_m:+.2f}% -> {100*kp/ko:+.2f}% "
          f"({100*(kp/ko-roi_m):+.2f}pp)")
    print(f"    Kalshi P&L rescaled to $100/trade: {100*kp/ko*n_m:+,.0f} "
          f"(intuition only, not a capacity claim)")

print("\n" + "-" * 86)
n_m = sum(v[0] for v in tot.values()); p_m = sum(v[1] for v in tot.values())
kn = sum(v[2] for v in tot.values()); kp = sum(v[3] for v in tot.values())
ko = sum(v[4] for v in tot.values())
print(f"  COMBINED (crewshock + final7, matched)")
print(f"    SB -110      {n_m:>5} bets  {p_m:>+9.0f}  ROI {100*p_m/(100*n_m):>+7.2f}%")
print(f"    KALSHI taker {kn:>5} trades {kp:>+9.2f}  ROI {100*kp/ko:>+7.2f}%")
print(f"\n  move and pacegap excluded: move's correct 09:00 ET book overlaps its")
print(f"  2025-26 signals on 1 game, and pacegap has no per-game signal export.")
