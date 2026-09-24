"""Normal vs frozen empirical shape, on IDENTICAL grids.

The first pass gave normal 30.1% and empirical 12.8%, but the two used
different grids -- the empirical run had a coarser location step (0.5 vs 0.25),
a coarser scale step (0.36 vs 0.10 pts) and a location range capped at +/-9 of
the strike mean. All three bias feasibility DOWN, so that comparison was not
apples to apples and is not reportable.

Here both shapes are evaluated on the same location grid, the same effective
scale resolution, and the same envelope, so the only thing that differs is the
SHAPE. Also reports the tight-body subsample, where narrower quotes improve
identification without fabricating precision.
"""
import sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

DB = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
RNG = np.random.default_rng(23)
FREEZE_END = 2024
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT m.event_ticker, m.floor_strike K, m.pregame_yes_bid b,
                          m.pregame_yes_ask a, e.game_date, e.away_team, e.home_team
                   FROM markets m JOIN events e USING(event_ticker)
                   WHERE m.pregame_yes_bid IS NOT NULL AND m.pregame_yes_ask IS NOT NULL
                     AND m.floor_strike IS NOT NULL""", con)
con.close()
m['L'] = m.b / 100.0; m['U'] = m.a / 100.0

raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
ms = pd.DataFrame({'date': pd.to_datetime(raw['DATE'], errors='coerce'),
                   'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
                   'posted': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
                   'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
ms['season'] = np.where(ms.date.dt.month >= 8, ms.date.dt.year, ms.date.dt.year - 1)
ms['D'] = ms.pts - ms.posted
ms['ds'] = ms.date.dt.strftime('%Y-%m-%d')
m['h'] = m.home_team.map(ABBR); m['r'] = m.away_team.map(ABBR)
m = m.merge(ms[['ds', 'h', 'r', 'posted']], left_on=['game_date', 'h', 'r'],
            right_on=['ds', 'h', 'r'], how='inner')

hist = ms[ms.season <= FREEZE_END].D.values
hist = hist[np.isfinite(hist)]
centre, scale = np.median(hist), hist.std()
Dstd = np.sort((hist - centre) / scale)
print(f"frozen shape: n={len(Dstd)} skew {pd.Series(hist).skew():+.4f} "
      f"exkurt {pd.Series(hist).kurtosis():+.4f} sd {scale:.3f}")

# --- IDENTICAL grids for both shapes ----------------------------------------
MU_OFF = np.arange(-14.0, 14.001, 0.25)      # location, offset from strike mean
SIG = np.arange(9.0, 30.001, 0.10)           # scale in POINTS, same for both
print(f"grids: {len(MU_OFF)} locations x {len(SIG)} scales (identical for both shapes)")


def surv_norm(z):
    return 1.0 - norm.cdf(z)


def surv_emp(z):
    return 1.0 - np.searchsorted(Dstd, z, side='right') / len(Dstd)


def run(shape_fn, tight=False):
    out = []
    for ev, g in m.groupby('event_ticker'):
        g = g.sort_values('K')
        if tight:
            body = g[(g.U <= 0.90) & (g.L >= 0.10)]
            if len(body) < 4 or (body.U - body.L).max() > 0.02:
                continue
            g = body
        K, L, U = g.K.values, g.L.values, g.U.values
        mu = K.mean() + MU_OFF
        # z[i,j,k] for location i, scale j, rung k
        z = (K[None, None, :] - mu[:, None, None]) / SIG[None, :, None]
        p = shape_fn(z)
        feas = ((p >= L[None, None, :] - 1e-12) & (p <= U[None, None, :] + 1e-12)).all(axis=2)
        d = dict(event=ev, posted=g.posted.iloc[0], feas=bool(feas.any()), n=len(g))
        if feas.any():
            si = np.where(feas.any(axis=0))[0]
            d['s_lo'], d['s_hi'] = SIG[si.min()], SIG[si.max()]
        out.append(d)
    return pd.DataFrame(out)


print("\n" + "=" * 74)
print("FEASIBILITY ON IDENTICAL GRIDS")
print("=" * 74)
res = {}
for nm, fn in (('normal', surv_norm), ('frozen empirical', surv_emp)):
    for tight in (False, True):
        F = run(fn, tight)
        lab = f"{nm}{' (tight body <=2c)' if tight else ' (all rungs)'}"
        res[(nm, tight)] = F
        band = (F.s_hi - F.s_lo).median() if F.feas.any() else np.nan
        print(f"  {lab:34s} {F.feas.mean()*100:5.1f}%  ({F.feas.sum():4d}/{len(F):4d})"
              f"   scale band median {band if band == band else float('nan'):.2f} pts")

print("\n" + "=" * 74)
print("SCALE SLOPE vs POSTED TOTAL  (required: +0.04187, CI [+0.01416,+0.07046])")
print("=" * 74)


def sl(x, y, nb=2000):
    s = np.polyfit(x, y, 1)[0]
    d = [np.polyfit(x[i], y[i], 1)[0] for i in
         (RNG.integers(0, len(x), len(x)) for _ in range(nb))]
    return s, *np.percentile(d, [2.5, 97.5])


for (nm, tight), F in res.items():
    if 's_lo' not in F.columns:
        print(f"  {nm}{' tight' if tight else ''}: no feasible events")
        continue
    G = F.dropna(subset=['s_lo'])
    if len(G) < 60:
        print(f"  {nm}{' tight' if tight else ''}: n={len(G)} too few")
        continue
    lab = f"{nm}{' tight' if tight else ''}"
    for col in ('s_lo', 's_hi'):
        s, lo, hi = sl(G.posted.values, G[col].values)
        inside = lo <= 0.04187 <= hi
        print(f"  {lab:22s} {col} slope {s:+.5f} CI [{lo:+.5f},{hi:+.5f}]"
              f"  {'covers required' if inside else 'EXCLUDES required'}")
