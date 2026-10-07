"""2025-26 side by side: sportsbook -110 vs Kalshi taker, per strategy.

BOOK    $100 flat at -110, graded against the strategy's own settlement line
        (the CLOSE for crewshock/final7, the OPENER for move/pacegap). Pushes
        dropped -- a sportsbook push is a no-action and cannot occur on Kalshi,
        where every strike ends in .5.

KALSHI  the live configuration: max-edge rung bought AT THE ASK, Kalshi fee,
        (mu, sigma) from EXECUTABLE BOUNDS, reference per strategy as signals()
        sets it, drift guard, MIN_EDGE and price band, settled on the actual.
        NO side disabled, so UNDER signals cannot trade -- the book column is
        therefore also shown restricted to OVER for a like-for-like read.

Picks up pacegap automatically once pacegap_backfill_2025_26.csv exists.
"""
import sys, os, sqlite3
import numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
WIN, LOSE = 100.0 / 1.1, -100.0
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
CFG = {'crewshock': dict(hit=0.5421, line='close', ref='kalshi', book='pregame'),
       'final7':    dict(hit=0.5529, line='close', ref='kalshi', book='pregame'),
       'move':      dict(hit=0.5344, line='open',  ref='open',   book='0900'),
       'pacegap':   dict(hit=0.5259, line='open',  ref='open',   book='0900')}
for v in CFG.values():
    v['delta'] = T.delta_points(v['hit'])

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['open'] = pd.to_numeric(d['OPENING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d['gid'] = d['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
S = d[d.season == 2025]

# ---------------------------------------------------------------- signals
cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
SIG = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']].assign(dir='OVER'),
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']].assign(dir='OVER')}
mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[(mv.SEASON == 2025) & mv.MOVE_COMBINED_OOS.notna()].copy()
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv[mv.MOVE_COMBINED_OOS.abs() >= 1.0].merge(S[['gid', 'ds', 'h', 'r']], on='gid')
SIG['move'] = mv.assign(dir=np.where(mv.MOVE_COMBINED_OOS > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]
PG = 'pacegap_backfill_2025_26.csv'
if os.path.exists(PG):
    pg = pd.read_csv(PG)
    pg = pg[pg.bet_flag == 1]
    SIG['pacegap'] = pg.rename(columns={'game_date': 'ds', 'TEAM_H': 'h', 'TEAM_R': 'r'}) \
        .assign(dir=np.where(pg.side.values > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]
    print(f"pacegap backfill loaded: {len(SIG['pacegap'])} bet_flag=1 signals")
else:
    print("pacegap backfill not present yet -- will show as pending")

# ---------------------------------------------------------------- books
def pregame_book():
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    b = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                              m.pregame_yes_bid bb, m.pregame_yes_ask aa,
                              e.game_date ds, e.away_team, e.home_team
                       FROM markets m JOIN events e USING(event_ticker)
                       WHERE m.pregame_yes_bid IS NOT NULL
                         AND m.pregame_yes_ask IS NOT NULL
                         AND m.floor_strike IS NOT NULL""", con)
    con.close(); return b


def book_0900():
    con = sqlite3.connect('file:' + CAND + '?mode=ro', uri=True)
    c = pd.read_sql("""SELECT event_ticker ev, ticker, end_period_ts ts, game_date ds,
                              strike_label K, yes_bid_close bb, yes_ask_close aa
                       FROM candles WHERE period_interval=1""", con)
    mk = pd.read_sql("SELECT DISTINCT ticker, floor_strike FROM markets", con)
    con.close()
    c = c.merge(mk, on='ticker', how='left')
    c['K'] = c.floor_strike.fillna(c.K); c = c.dropna(subset=['K', 'bb', 'aa'])
    tsu = pd.to_datetime(c.ts, unit='s', utc=True)
    c = c[(tsu.dt.strftime('%Y-%m-%d') == c.ds) & (tsu.dt.hour <= 13)]
    c = c.sort_values('ts').groupby(['ev', 'ticker'], as_index=False).last()
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    em = pd.read_sql("SELECT DISTINCT event_ticker ev, away_team, home_team FROM events", con)
    con.close(); return c.merge(em, on='ev', how='left')


BOOKS = {}
for nm, fn in (('pregame', pregame_book), ('0900', book_0900)):
    b = fn(); b['h'], b['r'] = b.home_team.map(ABBR), b.away_team.map(ABBR)
    b['L'], b['U'] = b.bb / 100.0, b.aa / 100.0
    BOOKS[nm] = b


def book_result(strat, over_only):
    c = CFG[strat]
    s = SIG[strat]
    if over_only:
        s = s[s.dir == 'OVER']
    j = s.merge(S[['ds', 'h', 'r', c['line'], 'actual']], on=['ds', 'h', 'r'], how='inner')
    j = j.dropna(subset=[c['line']])
    won = np.where(j.dir == 'OVER', j.actual > j[c['line']], j.actual < j[c['line']])
    push = j.actual == j[c['line']]
    j = j[~push]; won = won[~push.values]
    if not len(j):
        return None
    pnl = np.where(won, WIN, LOSE)
    return dict(n=len(j), hit=won.mean(), pnl=pnl.sum(), roi=pnl.sum() / (100 * len(j)))


def kalshi_result(strat):
    c = CFG[strat]
    s = SIG[strat][SIG[strat].dir == 'OVER']          # NO side disabled
    j = s.merge(BOOKS[c['book']], on=['ds', 'h', 'r'], how='inner')
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty or len(g) < 4:
            continue
        pts = float(m.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(x), yes_ask=float(y),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, x, y in zip(g.K, g.ticker, g.L, g.U)]
        mu, sg, _ = T.fit_ladder_detail(rungs)
        if mu is None:
            continue
        ref = mu if c['ref'] == 'kalshi' else float(m['open'].iloc[0])
        if not np.isfinite(ref):
            continue
        if (ref - mu) > abs(c['delta']):
            continue
        cand = [x for x in T.candidates(rungs, ref + c['delta'], sg, ('OVER',))
                if T.gate(x, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not cand:
            continue
        x = cand[0]; fee = NK.fee(x['price'], 1); won = pts > x['strike']
        out.append(dict(hit=int(won), pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                        outlay=x['price'] + fee))
    R = pd.DataFrame(out)
    if not len(R):
        return None
    return dict(n=len(R), hit=R.hit.mean(), pnl=R.pnl.sum(), outlay=R.outlay.sum(),
                roi=R.pnl.sum() / R.outlay.sum())


print("\n" + "=" * 104)
print("2025-26 SIDE BY SIDE -- sportsbook -110 ($100 flat) vs Kalshi taker (1 contract)")
print("=" * 104)
print(f"  {'strategy':>10} | {'BOOK all sig':>26} | {'BOOK OVER-only':>26} | "
      f"{'KALSHI taker (OVER)':>28}")
print(f"  {'':>10} | {'n':>5}{'hit%':>8}{'ROI':>9} | {'n':>5}{'hit%':>8}{'ROI':>9} | "
      f"{'n':>5}{'hit%':>8}{'ROI':>9}{'P&L':>8}")
print("  " + "-" * 100)
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    if strat not in SIG:
        print(f"  {strat:>10} | {'backfill still running':>26} |")
        continue
    ba, bo, ka = book_result(strat, False), book_result(strat, True), kalshi_result(strat)
    f = lambda x: (f"{x['n']:>5}{100*x['hit']:>7.2f}%{100*x['roi']:>+8.2f}%"
                   if x else f"{'--':>5}{'--':>8}{'--':>9}")
    extra = f"{ka['pnl']:>+8.2f}" if ka else f"{'--':>8}"
    print(f"  {strat:>10} | {f(ba):>26} | {f(bo):>26} | {f(ka):>26}{extra}")
print("\n  BOOK stake $100/bet; KALSHI stake ~$0.47/contract. ROI is the comparable")
print("  column -- an identical loss per bet is a larger % of the smaller stake.")
print("  Kalshi OVER-only because the NO side is disabled (NBA_NO_SIDE_VERIFIED unset).")
print("  move/pacegap Kalshi use the 09:00 ET book, which exists for only 54 events.")
