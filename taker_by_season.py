"""By-season hit rate, P&L and ROI for the four live strategies, TAKER basis.

STRATEGIES AS THE TRADER DEFINES THEM. Everything here is read from
nba_live_trader.STRATS -- which settlement line each rule grades against
(close for crewshock/final7, opener for move/pacegap) and which sides it is
allowed to take (OVER-only for crewshock/final7, both for move/pacegap). No
definition is restated locally, so this cannot drift from what trades.

A TRANSLATION FOR 2017-2024, A MEASUREMENT FOR NOTHING. Kalshi purges settled
markets, so no NBA book exists before 2025-26 and none ever will. These rows
reprice each season's REALISED hit rate at the measured Kalshi taker cost.
The hit rates are real; the Kalshi cost applied to them is a constant, not an
observed per-game quote.

WHY (h - c) IS THE WHOLE P&L. Buying one contract at ask `a` with fee `f`
returns (1 - a - f) on a win and -(a + f) on a loss. With c = a + f,

    E[pnl per contract] = h(1 - c) - (1 - h)c = h - c

so P&L per contract is exactly (h - c) and ROI is (h - c)/c. There is no
further assumption: the -110 break-even 0.5238 is replaced by c and nothing
else changes.

c IS MEASURED, NOT CHOSEN. It comes from offset_curve_full_board.csv, the
14,284 real 2025-26 rungs: the mean ask of the NEAREST-LINE rung (the rung
RUNG_RULE="nearline" actually buys) plus its mean fee. Printed below so the
reader can see it rather than trust it.

PUSHES are dropped -- a sportsbook push is a no-action, and it cannot happen
on Kalshi where every strike ends in .5.
"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T

OFFSET = 'offset_curve_full_board.csv'

# ---------------------------------------------------------------- the cost c
oc = pd.read_csv(OFFSET)
z = oc[oc.rung == 0]
ASK, FEE = float(z.ask.mean()), float(z.fee.mean())
C = ASK + FEE
BE110 = 1.1 / 2.1

# ---------------------------------------------------------------- game data
raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['open'] = pd.to_numeric(d['OPENING TOTAL_H'], errors='coerce')
d['actual'] = (pd.to_numeric(d['PTS_H'], errors='coerce')
               + pd.to_numeric(d['PTS_R'], errors='coerce'))
d['gid'] = d['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)

# ---------------------------------------------------------------- signals
SIG = {}
cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
SIG['crewshock'] = cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[
    ['ds', 'h', 'r']].assign(dir='OVER')
SIG['final7'] = d[d.days_left <= T.FINAL7_DAYS][['ds', 'h', 'r']].assign(dir='OVER')
mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[mv.MOVE_COMBINED_OOS.notna()].copy()
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv[mv.MOVE_COMBINED_OOS.abs() >= 1.0].merge(d[['gid', 'ds', 'h', 'r']], on='gid')
SIG['move'] = mv.assign(
    dir=np.where(mv.MOVE_COMBINED_OOS > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]
pg = pd.read_csv('pacegap_backfill_all.csv')
pg = pg[pg.bet_flag == 1]
SIG['pacegap'] = pg.rename(
    columns={'game_date': 'ds', 'TEAM_H': 'h', 'TEAM_R': 'r'}).assign(
    dir=np.where(pg.side.values > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]


def graded(strat):
    """Signals joined to outcomes, graded on the line the TRADER settles on."""
    cfg = T.STRATS[strat]
    line = cfg['line'] if cfg['line'] in ('open', 'close') else 'close'
    s = SIG[strat]
    s = s[s.dir.isin(cfg['sides'])]                 # the trader's own sides
    j = s.merge(d[['ds', 'h', 'r', 'season', line, 'actual']],
                on=['ds', 'h', 'r'], how='inner').dropna(subset=[line])
    j = j[j.actual != j[line]]                      # pushes: no action
    j['won'] = np.where(j.dir == 'OVER', j.actual > j[line], j.actual < j[line])
    return j


print("=" * 102)
print("BY-SEASON TAKER RECORD -- strategies exactly as nba_live_trader.STRATS defines them")
print("=" * 102)
print(f"  measured taker cost c = {C:.4f}   (nearest-line ask {ASK:.4f} + fee {FEE:.4f},")
print(f"                                     from {len(oc):,} real 2025-26 rungs, rung 0 n={len(z):,})")
print(f"  P&L per contract = (h - c);  ROI = (h - c)/c;  break-even h = {100*C:.2f}%")
print(f"  for reference, -110 break-even = {100*BE110:.2f}%  ->  taker costs "
      f"{100*(C-BE110):+.2f}pp of required hit rate")
print()
print("  P&L is shown BOTH ways: at 1 contract/bet (what the trader actually does,")
print("  MAX_CONTRACTS_GAME=1) and at $100/bet (comparable to the -110 tables).")

ALL = {}
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    cfg = T.STRATS[strat]
    g = graded(strat)
    ALL[strat] = g
    sides = '/'.join(cfg['sides'])
    tag = 'prereg' if cfg.get('prereg') else 'DISCRETIONARY'
    print()
    print(f"  {strat.upper()}   settles on the {cfg['line'].upper()}, sides {sides}, "
          f"{tag}, registered hit {cfg['hit']:.4f}")
    print(f"      {'season':>8}{'bets':>7}{'hit%':>8}{'ROI':>9}"
          f"{'P&L 1ct':>10}{'P&L $100':>11}")
    for s in sorted(g.season.unique()):
        x = g[g.season == s]
        h = x.won.mean()
        roi = (h - C) / C
        print(f"      {s:>8}{len(x):>7}{100*h:>7.2f}%{100*roi:>+8.2f}%"
              f"{len(x)*(h-C):>+10.2f}{roi*100*len(x):>+11.0f}")
    h = g.won.mean(); roi = (h - C) / C
    pos = sum(1 for s in g.season.unique() if g[g.season == s].won.mean() > C)
    nsea = g.season.nunique()
    worst = min((g[g.season == s].won.mean() - C) / C for s in g.season.unique())
    print(f"      {'ALL':>8}{len(g):>7}{100*h:>7.2f}%{100*roi:>+8.2f}%"
          f"{len(g)*(h-C):>+10.2f}{roi*100*len(g):>+11.0f}")
    se = np.sqrt(h * (1 - h) / len(g)) / C
    print(f"               {pos}/{nsea} seasons profitable; worst {100*worst:+.2f}%; "
          f"ROI se {100*se:.2f}pp -> 95% CI [{100*(roi-1.96*se):+.2f}%, "
          f"{100*(roi+1.96*se):+.2f}%]")

print()
print("=" * 102)
print("SENSITIVITY TO c -- the cost assumption moves everything together")
print("=" * 102)
print(f"      {'c':>8}" + ''.join(f"{s:>12}" for s in ALL))
for cc in (0.511, 0.5254, 0.532, 0.545):
    row = f"      {cc:>8.4f}"
    for strat, g in ALL.items():
        row += f"{100*(g.won.mean()-cc)/cc:>+11.2f}%"
    print(row + ("   <-- measured" if abs(cc - C) < 1e-6 else ""))
print()
print("  A 3.4c swing in c spans roughly 7pp of ROI -- wider than the gaps BETWEEN")
print("  strategies. The ranking is robust to c; the levels are not.")
