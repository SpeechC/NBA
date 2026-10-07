"""Why does the same model perform differently on Kalshi vs the book in 2025-26?

The venues post the SAME distribution (reconciled: Kalshi minus book = +0.047
points of line, 0.50 inside the executable bracket on 89.6% of events), so the
difference cannot be the line. Decompose it instead.

A bet is beating the market by more than the cost of trading. Write both venues
in those terms, with the MARKET's own probability as the common reference:

  sportsbook   bet the LINE L.  market says 0.50.
               edge_L = realised P(actual > L) - 0.50
               cost   = the vig, 52.381% - 50% = 2.381pp
               ROI    = 1.909 * edge_L - 4.55%

  Kalshi       bet the STRIKE K. market says mkt_K = 1 - Phi((K-mu)/sigma),
               mu and sigma from the EXECUTABLE BOUNDS.
               edge_K = realised P(actual > K) - mkt_K
               cost_K = (ask + fee) - mkt_K          the spread and fee paid
               ROI    = (edge_K - cost_K) / (ask + fee)

So the two venues differ in exactly two places: whether the strategy's edge
survives moving from L to K, and whether the Kalshi cost is bigger or smaller
than the vig. This measures both.
"""
import sys, sqlite3
import numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
CFG = {'crewshock': 0.5421, 'final7': 0.5529}
DELTA = {k: T.delta_points(v) for k, v in CFG.items()}

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
SIG = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']],
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
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)
bk['L'], bk['U'] = bk.b / 100.0, bk.a / 100.0

print("=" * 92)
print("DECOMPOSITION -- 2025-26, same signals, same games")
print("=" * 92)
for strat in ('crewshock', 'final7'):
    j = SIG[strat].merge(bk, on=['ds', 'h', 'r'], how='inner')
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty or len(g) < 4:
            continue
        close, pts = float(m.close.iloc[0]), float(m.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(x), yes_ask=float(y),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, x, y in zip(g.K, g.ticker, g.L, g.U)]
        mu, sg, feas = T.fit_ladder_detail(rungs)
        if mu is None:
            continue
        c = [x for x in T.candidates(rungs, mu + DELTA[strat], sg, ('OVER',))
             if T.gate(x, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not c:
            continue
        x = c[0]
        fee = NK.fee(x['price'], 1)
        mkt_K = float(1.0 - norm.cdf((x['strike'] - mu) / sg))
        out.append(dict(hit_L=int(pts > close), push_L=int(pts == close),
                        hit_K=int(pts > x['strike']), mkt_K=mkt_K,
                        ask=x['price'], outlay=x['price'] + fee,
                        cost_K=(x['price'] + fee) - mkt_K,
                        off=x['strike'] - mu, p_model=x['p_model']))
    R = pd.DataFrame(out)
    nL = R[R.push_L == 0]
    hL, hK = nL.hit_L.mean(), R.hit_K.mean()
    edge_L = hL - 0.5
    edge_K = hK - R.mkt_K.mean()
    cost_K = R.cost_K.mean()
    roi_sb = 1.909090909 * hL - 1.0
    roi_k = (hK - R.outlay.mean()) / R.outlay.mean()
    seL = np.sqrt(hL * (1 - hL) / len(nL)); seK = np.sqrt(hK * (1 - hK) / len(R))
    print(f"\n  {strat.upper()}   n={len(R)}   mean strike offset {R.off.mean():+.2f} pts "
          f"from the Kalshi centre")
    print(f"    {'':<34}{'BOOK (bet the line)':>22}{'KALSHI (bet the strike)':>26}")
    print(f"    {'what the market says':<34}{0.5:>22.4f}{R.mkt_K.mean():>26.4f}")
    print(f"    {'what the model says':<34}{CFG[strat]:>22.4f}{R.p_model.mean():>26.4f}")
    print(f"    {'what actually happened':<34}{hL:>22.4f}{hK:>26.4f}")
    print(f"    {'EDGE over the market':<34}{100*edge_L:>+21.2f}pp{100*edge_K:>+25.2f}pp")
    print(f"    {'   se':<34}{100*seL:>22.2f}{100*seK:>26.2f}")
    print(f"    {'COST of trading':<34}{2.381:>+21.2f}pp{100*cost_K:>+25.2f}pp")
    print(f"    {'NET (edge - cost)':<34}{100*edge_L-2.381:>+21.2f}pp"
          f"{100*(edge_K-cost_K):>+25.2f}pp")
    print(f"    {'stake per bet':<34}{1.0:>22.3f}{R.outlay.mean():>26.3f}")
    print(f"    {'ROI':<34}{100*roi_sb:>+21.2f}%{100*roi_k:>+25.2f}%")
    print(f"    model error vs reality: at the line {100*(hL-CFG[strat]):+.2f}pp, "
          f"at the strike {100*(hK-R.p_model.mean()):+.2f}pp")

print("\n" + "=" * 92)
print("READING IT")
print("=" * 92)
print("  Both venues reduce to  edge over the market  minus  cost of trading.")
print("  The COST side is small and known: the vig is a flat 2.381pp, the Kalshi")
print("  cost is the half-spread plus the fee above the market's own fair value.")
print("  So any large ROI gap has to come from the EDGE side -- whether the")
print("  strategy still beats the market once you move from the line to the strike.")
