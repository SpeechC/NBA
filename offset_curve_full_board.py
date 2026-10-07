"""Offset curve on the FULL 2025-26 board -- unconditional taker cost by rung.

The signal-conditioned curve (rung_selection_taker.py) used the 280 games with a
crewshock or final7 signal. This uses every event on the board, which measures a
different and more basic thing: **where on the ladder is taking cheapest,
independent of any signal?**

That decomposition matters. If the UNCONDITIONAL curve also peaks at the line,
then "buy nearest the line" is not a fact about our strategies at all -- it is
the ladder's own cost structure, and the signal-conditioned peak inherits it.

Everything is an OVER bought AT THE ASK with the Kalshi fee, settled against the
actual final total. Offsets are expressed in RUNGS from the closing total, since
strikes sit 3 points apart and a points axis would alias.

Reported per rung offset:
  ask          what a taker pays
  hit%         realised settlement frequency
  ask - hit    the overpayment in percentage points (the spread you crossed)
  fee          the Kalshi fee at that price
  P&L/ct, ROI  the realised result
"""
import sqlite3, numpy as np, pandas as pd
import sys
sys.path.insert(0, '.')
from prepare_data import read_master, season_label

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
MIN_PRICE, MAX_PRICE = 0.12, 0.88
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw.copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d = d.dropna(subset=['date', 'close', 'actual'])
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
d = d[['ds', 'h', 'r', 'close', 'actual', 'lbl']]

con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
bk = pd.read_sql("""SELECT m.event_ticker ev, m.floor_strike K,
                           m.pregame_yes_bid b, m.pregame_yes_ask a,
                           e.game_date ds, e.away_team, e.home_team
                    FROM markets m JOIN events e USING(event_ticker)
                    WHERE m.pregame_yes_bid IS NOT NULL
                      AND m.pregame_yes_ask IS NOT NULL
                      AND m.floor_strike IS NOT NULL""", con)
con.close()
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)
m = bk.merge(d, on=['ds', 'h', 'r'], how='inner')
print(f"full board: {m.ev.nunique()} events, {len(m)} rungs joined to a close+result")

m['ask'] = m.a / 100.0
m['bidp'] = m.b / 100.0
m['spread'] = m.ask - m.bidp
m['fee'] = np.ceil(0.07 * m.ask * (1 - m.ask) * 1000) / 1000.0
m['hit'] = (m.actual > m.K).astype(float)
m['pnl'] = np.where(m.hit == 1, 1 - m.ask - m.fee, -m.ask - m.fee)
m['outlay'] = m.ask + m.fee
m['rung'] = np.round((m.K - m.close) / 3.0).astype(int)

band = m[(m.ask >= MIN_PRICE) & (m.ask <= MAX_PRICE)].copy()
print(f"in the 0.12-0.88 price band: {len(band)} rungs "
      f"({100*len(band)/len(m):.1f}%)\n")


def table(sub, title):
    print("=" * 98)
    print(title)
    print("=" * 98)
    print(f"  {'rungs from line':>16}{'n':>7}{'ask':>8}{'hit%':>8}{'ask-hit':>9}"
          f"{'spread':>8}{'fee':>7}{'P&L/ct':>9}{'ROI':>9}")
    g = sub.groupby('rung')
    for k, gg in g:
        if len(gg) < 40:
            continue
        print(f"  {k:>+16d}{len(gg):>7}{gg.ask.mean():>8.3f}{100*gg.hit.mean():>7.2f}%"
              f"{100*(gg.ask.mean()-gg.hit.mean()):>+8.2f}{100*gg.spread.mean():>7.2f}c"
              f"{100*gg.fee.mean():>6.2f}c{100*gg.pnl.mean():>+8.2f}c"
              f"{100*gg.pnl.sum()/gg.outlay.sum():>+8.2f}%")
    print(f"  {'ALL':>16}{len(sub):>7}{sub.ask.mean():>8.3f}{100*sub.hit.mean():>7.2f}%"
          f"{100*(sub.ask.mean()-sub.hit.mean()):>+8.2f}{100*sub.spread.mean():>7.2f}c"
          f"{100*sub.fee.mean():>6.2f}c{100*sub.pnl.mean():>+8.2f}c"
          f"{100*sub.pnl.sum()/sub.outlay.sum():>+8.2f}%")


table(band, "UNCONDITIONAL -- buy EVERY in-band OVER rung at the ask, full board")

print()
reg = band[band.lbl.str.contains('Regular Season', na=False)]
table(reg, "REGULAR SEASON ONLY")

# ---- is the shape significant? block bootstrap by EVENT --------------------
print("\n" + "=" * 98)
print("INFERENCE -- is ROI really best at the line? event-clustered bootstrap")
print("=" * 98)
rng = np.random.default_rng(17)
evs = band.ev.unique()
idx = {e: g.index.values for e, g in band.groupby('ev')}
best = []
for _ in range(1000):
    pick = rng.choice(evs, len(evs), replace=True)
    s = band.loc[np.concatenate([idx[e] for e in pick])]
    r = s.groupby('rung').apply(
        lambda gg: gg.pnl.sum() / gg.outlay.sum() if len(gg) >= 40 else np.nan)
    r = r.dropna()
    if len(r):
        best.append(r.idxmax())
best = pd.Series(best)
print(f"  rung with the best ROI, across 1000 event-clustered resamples:")
for k, v in best.value_counts().sort_index().items():
    print(f"    rung {k:+d}: {100*v/len(best):5.1f}% of resamples")
print(f"\n  modal best rung = {best.mode().iloc[0]:+d}")
band.to_csv('offset_curve_full_board.csv', index=False)
print("\n  [rows -> offset_curve_full_board.csv]")
