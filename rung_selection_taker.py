"""Which rung should a TAKER buy? Real 2025-26 books, realised settlement.

The trader buys the MAX-EDGE rung. That rule's +24% advantage over the
at-the-line rung was measured in the MAKER framing (edge against the bid). As a
taker the trade-off inverts: the max-edge rung sits ABOVE the line for an OVER
and so hits 5-10pp less often, while an at-the-line rung hits near the
sportsbook rate but sits near 50c where the Kalshi fee peaks at 1.75c.

Policies compared, all bought AT THE ASK with the fee, settled on the actual:
  A  max-edge, gated      the current trader
  B  nearest-line, gated  same gate, different rung choice
  C  nearest-line, always the faithful translation of the sportsbook strategy,
                          which always bets the line -- gate bypassed except
                          for a sane price band
Plus the full offset curve: realised taker economics of EVERY rung, bucketed by
(strike - reference line), which shows the shape rather than two points.

Strategies: crewshock and final7 -- the two whose settlement line is the CLOSE
and whose correct book is the pregame snapshot.
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
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
DELTA = {'crewshock': T.delta_points(0.5421), 'final7': T.delta_points(0.5529)}

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

cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
sig = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']],
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']]}

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


def pnl_of(c, pts):
    fee = NK.fee(c['price'], 1)
    won = pts > c['strike']
    return (dict(hit=bool(won), ask=c['price'], outlay=c['price'] + fee,
                 pnl=(1 - c['price'] - fee) if won else (-c['price'] - fee),
                 off=c['strike'] - c['_Lref'], edge=c['edge']))


rows, curve = [], []
for strat in ('crewshock', 'final7'):
    j = sig[strat].merge(bk, on=['ds', 'h', 'r'], how='inner')
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty or len(g) < 4:
            continue
        Lref, pts = float(m.close.iloc[0]), float(m.actual.iloc[0])
        mu_mkt, sg = mu_sigma(g.K.values, g.L.values, g.U.values)
        if mu_mkt is not None and (Lref - mu_mkt) > abs(DELTA[strat]):
            continue
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
        cands = T.candidates(rungs, Lref + DELTA[strat], sg, ('OVER',))
        # MAX EDGE IS THE TAKER EDGE. candidates() defaults to take=True since
        # 2a86820, so edge = p_model - ASK - fee and price IS the ask. Asserted
        # rather than trusted: a maker-priced edge would rank rungs differently.
        for c in cands:
            assert c['take'] is True, 'candidates() is not in taker mode'
            match = [x for x in rungs if x['ticker'] == c['ticker']][0]
            assert abs(c['price'] - match['yes_ask']) < 1e-9, 'price is not the ask'
            c['_Lref'] = Lref
        st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
        gated = [c for c in cands if T.gate(c, st) is None]
        inband = [c for c in cands if T.MIN_PRICE <= c['price'] <= T.MAX_PRICE]
        # full offset curve
        for c in inband:
            curve.append(dict(strat=strat, **pnl_of(c, pts)))
        rec = dict(strat=strat, ev=ev)
        if gated:
            rec['A'] = pnl_of(max(gated, key=lambda c: c['edge']), pts)
            nl = min(gated, key=lambda c: abs(c['strike'] - Lref))
            rec['B'] = pnl_of(nl, pts)
        if inband:
            rec['C'] = pnl_of(min(inband, key=lambda c: abs(c['strike'] - Lref)), pts)
        rows.append(rec)

R = pd.DataFrame(rows)
C = pd.DataFrame(curve)

POL = [('A', 'max-edge, gated   (CURRENT)'),
       ('B', 'nearest-line, gated'),
       ('C', 'nearest-line, always')]
print(f"edge basis verified: take=True and price==yes_ask on every candidate")
print("=" * 88)
print("RUNG SELECTION AS A TAKER -- 2025-26 real books, realised settlement")
print("=" * 88)
for strat in ('crewshock', 'final7'):
    sub = R[R.strat == strat]
    print(f"\n  {strat.upper()}  ({len(sub)} games with a usable board)")
    print(f"    {'policy':<30}{'n':>5}{'hit%':>8}{'avg ask':>9}{'mean off':>10}"
          f"{'P&L':>9}{'ROI':>9}{'c/ct':>8}")
    for key, lbl in POL:
        t = [x[key] for _, x in sub.iterrows() if isinstance(x.get(key), dict)]
        if not t:
            print(f"    {lbl:<30}    0   --"); continue
        t = pd.DataFrame(t)
        print(f"    {lbl:<30}{len(t):>5}{100*t.hit.mean():>7.2f}%{t.ask.mean():>9.3f}"
              f"{t.off.mean():>+10.2f}{t.pnl.sum():>+9.2f}"
              f"{100*t.pnl.sum()/t.outlay.sum():>+8.2f}%{100*t.pnl.mean():>+7.2f}c")

print("\n" + "=" * 88)
print("FULL OFFSET CURVE -- every in-band rung, realised, pooled")
print("=" * 88)
C['bkt'] = pd.cut(C.off, [-30, -9, -6, -3, 0, 3, 6, 9, 30], right=False)
print(f"  {'strike - line':>16}{'n':>7}{'hit%':>8}{'avg ask':>9}{'P&L/ct':>9}{'ROI':>9}")
for b, g in C.groupby('bkt', observed=True):
    print(f"  {str(b):>16}{len(g):>7}{100*g.hit.mean():>7.2f}%{g.ask.mean():>9.3f}"
          f"{100*g.pnl.mean():>+8.2f}c{100*g.pnl.sum()/g.outlay.sum():>+8.2f}%")
print("\n  (pooled across both strategies and all games -- this is the shape of the")
print("   ladder as a taker, not a policy; the gate and one-rung-per-game apply above.)")
C.to_csv('rung_selection_curve.csv', index=False)

# ---- paired inference: same games, two policies -------------------------
print("\n" + "=" * 88)
print("PAIRED TEST -- nearest-line MINUS max-edge, per game (same board)")
print("=" * 88)
_rng = np.random.default_rng(5)
for _strat in ('crewshock', 'final7'):
    _sub = R[R.strat == _strat]
    _dif = np.array([x['B']['pnl'] - x['A']['pnl'] for _, x in _sub.iterrows()
                     if isinstance(x.get('A'), dict) and isinstance(x.get('B'), dict)])
    if len(_dif) < 20:
        continue
    _bs = [_rng.choice(_dif, len(_dif), replace=True).mean() for _ in range(5000)]
    _lo, _hi = np.percentile(_bs, [2.5, 97.5])
    _t = _dif.mean() / (_dif.std(ddof=1) / np.sqrt(len(_dif)))
    print(f"  {_strat:<10} n={len(_dif):<4} mean diff {100*_dif.mean():+6.2f}c/game"
          f"   t {_t:+5.2f}   95% CI [{100*_lo:+.2f}c, {100*_hi:+.2f}c]"
          f"   {'EXCLUDES 0' if _lo > 0 else 'includes 0'}")
    print(f"             rung differs on {int((_dif != 0).sum())} of {len(_dif)} games")
