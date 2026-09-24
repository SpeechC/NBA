"""Is closing-line precision systematically worse for some matchups?

    D_i = actual total_i - closing total_i

Question 1  Does Var(D | X) genuinely vary with pregame-observable matchup
            state?  Established FIRST as heteroskedasticity, not by training a
            classifier and reading its AUC.
Question 2  If it does -- is it worse than the market already prices?  The
            market's own dispersion expectation is whatever it normally applies
            to games with that total and spread, so the difficulty score is
            orthogonalised against (total, spread) before it is allowed to
            claim anything.

Only Question 2 can matter for trading. "These games are harder" is a fact
about basketball; "harder than the market realises" is a fact about the price.

POINT-IN-TIME. The TEAM_*_STD_* columns are season-to-date MEANS (the suffix is
not a standard deviation) and their timing relative to the game is not
documented, so nothing here uses them. Every feature is rebuilt from box scores
with shift(1) inside the season, which cannot see the game it describes.

PRIOR WORK, deliberately not reused: MATCHUP_HARDNESS.md tested 11 PREDEFINED
archetype classes and found sd 17.5-18.6, max VarRatio 1.109 against a 1.29
bar. This is a different operationalisation -- a FITTED continuous difficulty
score, trained on early seasons and read out of sample -- so it is run rather
than cited. If it lands in the same place, that is two operationalisations, not
one.
"""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy import stats

SRC = '/mnt/c/NBA2/dfMaster_OT_2017-2026.csv'
TRAIN_END = 2021          # fit on 2017-2021, read out of sample on 2022-2025
ROLL, MINP = 15, 5

raw = pd.read_csv(SRC, low_memory=False)
ds = raw['DATASET_H'].fillna(raw.get('BIGDATABALL\nDATASET_H')).astype(str)

d = pd.DataFrame({
    'date':   pd.to_datetime(raw['DATE'], errors='coerce'),
    'gid':    raw['GAME-ID'],
    'th':     raw['TEAM_H'].astype(str), 'tr': raw['TEAM_R'].astype(str),
    'total':  pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'spread': pd.to_numeric(raw['CLOSING SPREAD_H'], errors='coerce'),
    'otot':   pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts':    pd.to_numeric(raw['TOTAL_PTS'], errors='coerce'),
    'f_h':    pd.to_numeric(raw['F_H'], errors='coerce'),
    'f_r':    pd.to_numeric(raw['F_R'], errors='coerce'),
    'rest_h': raw['TEAM\nREST DAYS_H'].astype(str),
    'rest_r': raw['TEAM\nREST DAYS_R'].astype(str),
    'playoff': ds.str.contains('Playoff', case=False),
})
for side in ('H', 'R'):
    for c, nm in (('POSS', 'poss'), ('PACE', 'pace'), ('OEFF', 'oeff'), ('DEFF', 'deff'),
                  ('3PA', 'tpa'), ('FGA', 'fga'), ('FTA', 'fta'), ('3P', 'tpm'),
                  ('OR', 'orb'), ('DR', 'drb'), ('TO', 'tov')):
        d[f'{nm}_{side.lower()}'] = pd.to_numeric(raw[f'{c}_{side}'], errors='coerce')

d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)
d['D'] = d.pts - d.total                      # includes OT, as Kalshi settles
d = d.dropna(subset=['total', 'spread', 'pts', 'D']).sort_values('date').reset_index(drop=True)
print(f"games {len(d)}   seasons {d.season.min()}-{d.season.max()}   "
      f"mean D {d.D.mean():+.3f}   sd D {d.D.std():.3f}")

# ---------------------------------------------------------------- PIT team state
# One row per team-game, rolled with shift(1) inside the season, then re-joined.
long = []
for side, opp in (('h', 'r'), ('r', 'h')):
    long.append(pd.DataFrame({
        'gid': d.gid, 'season': d.season, 'date': d.date, 'side': side,
        'team': d[f't{side}'],
        'pace': d[f'pace_{side}'], 'oeff': d[f'oeff_{side}'], 'deff': d[f'deff_{side}'],
        'pts': d[f'f_{side}'], 'tpa': d[f'tpa_{side}'], 'fga': d[f'fga_{side}'],
        'fta': d[f'fta_{side}'], 'orb': d[f'orb_{side}'], 'drb': d[f'drb_{side}'],
        'tov': d[f'tov_{side}'], 'gtot': d.pts}))
L = pd.concat(long).sort_values(['team', 'date'])
L['tp_rate'] = L.tpa / L.fga.replace(0, np.nan)
L['ft_rate'] = L.fta / L.fga.replace(0, np.nan)

g = L.groupby(['team', 'season'])
FEATS = ['pace', 'oeff', 'deff', 'tp_rate', 'ft_rate', 'orb', 'drb', 'tov']
for c in FEATS:
    L[f'pit_{c}'] = g[c].transform(lambda s: s.shift(1).rolling(ROLL, min_periods=MINP).mean())
# team-level volatility: how variable this team's own games have been
L['pit_sd_pts'] = g['pts'].transform(lambda s: s.shift(1).rolling(ROLL, min_periods=MINP).std())
L['pit_sd_gtot'] = g['gtot'].transform(lambda s: s.shift(1).rolling(ROLL, min_periods=MINP).std())
L['pit_sd_pace'] = g['pace'].transform(lambda s: s.shift(1).rolling(ROLL, min_periods=MINP).std())

keep = ['gid', 'side'] + [c for c in L.columns if c.startswith('pit_')]
W = L[keep].pivot(index='gid', columns='side')
W.columns = [f'{a}_{b}' for a, b in W.columns]
d = d.merge(W, left_on='gid', right_index=True, how='left')

# ---------------------------------------------------------------- features
d['pace_sum'] = d.pit_pace_h + d.pit_pace_r
d['pace_gap'] = (d.pit_pace_h - d.pit_pace_r).abs()
d['vol_sum'] = d.pit_sd_pts_h + d.pit_sd_pts_r
d['vol_gtot'] = (d.pit_sd_gtot_h + d.pit_sd_gtot_r) / 2
d['pace_vol'] = d.pit_sd_pace_h + d.pit_sd_pace_r
d['tp_sum'] = d.pit_tp_rate_h + d.pit_tp_rate_r
d['tp_gap'] = (d.pit_tp_rate_h - d.pit_tp_rate_r).abs()
d['ft_sum'] = d.pit_ft_rate_h + d.pit_ft_rate_r
d['off_def_h'] = d.pit_oeff_h - d.pit_deff_r        # offence vs opposing defence
d['off_def_r'] = d.pit_oeff_r - d.pit_deff_h
d['eff_sum'] = d.pit_oeff_h + d.pit_oeff_r
d['reb_mismatch'] = (d.pit_orb_h - d.pit_drb_r).abs() + (d.pit_orb_r - d.pit_drb_h).abs()
d['tov_sum'] = d.pit_tov_h + d.pit_tov_r
d['absspread'] = d.spread.abs()
d['b2b_h'] = d.rest_h.str.contains('B2B').astype(int)
d['b2b_r'] = d.rest_r.str.contains('B2B').astype(int)
d['b2b_any'] = ((d.b2b_h + d.b2b_r) > 0).astype(int)
d['tot_move'] = (d.total - d.otot).abs()

X = ['pace_sum', 'pace_gap', 'vol_sum', 'vol_gtot', 'pace_vol', 'tp_sum', 'tp_gap',
     'ft_sum', 'off_def_h', 'off_def_r', 'eff_sum', 'reb_mismatch', 'tov_sum',
     'total', 'absspread', 'b2b_h', 'b2b_r', 'b2b_any', 'tot_move']
m = d.dropna(subset=X + ['D']).copy()
print(f"modelling rows {len(m)}  (lost {len(d)-len(m)} to PIT warm-up)")

# ================================================================ Q1
print("\n" + "=" * 78)
print("Q1.  IS THERE HETEROSKEDASTICITY AT ALL?  (no classifier yet)")
print("=" * 78)
tr, te = m[m.season <= TRAIN_END], m[m.season > TRAIN_END]
print(f"  train {tr.season.min()}-{tr.season.max()} n={len(tr)}   "
      f"test {te.season.min()}-{te.season.max()} n={len(te)}")

print("\n  Breusch-Pagan on the TRAIN seasons: regress D^2 on all features")
Xtr = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in X])
y = (tr.D.values ** 2)
beta, *_ = np.linalg.lstsq(Xtr, y, rcond=None)
yh = Xtr @ beta
ssr = ((yh - y.mean()) ** 2).sum()
lm = ssr / (2 * (y.mean() ** 2))                 # BP statistic
pbp = 1 - stats.chi2.cdf(lm, len(X))
r2 = 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
print(f"    BP LM = {lm:.2f} on {len(X)} df   p = {pbp:.4g}   R2 on D^2 = {r2:.5f}")

print("\n  Single-feature variance ratio, TRAIN (top vs bottom quintile of each):")
print(f"    {'feature':>14s} {'sd(D) Q1':>9s} {'sd(D) Q5':>9s} {'VarRatio':>9s} {'Levene p':>10s}")
rows = []
for c in X:
    q = pd.qcut(tr[c], 5, duplicates='drop', labels=False)
    a, b = tr.D[q == 0], tr.D[q == q.max()]
    if len(a) < 50 or len(b) < 50:
        continue
    vr = b.var() / a.var()
    lp = stats.levene(a, b, center='median').pvalue
    rows.append((c, a.std(), b.std(), vr, lp))
for c, s1, s5, vr, lp in sorted(rows, key=lambda r: -abs(np.log(r[3]))):
    print(f"    {c:>14s} {s1:9.3f} {s5:9.3f} {vr:9.4f} {lp:10.2g}")

# ================================================================ Q2
print("\n" + "=" * 78)
print("Q2.  FITTED DIFFICULTY SCORE, READ OUT OF SAMPLE")
print("=" * 78)


def table(sub, score, label):
    s = sub.copy()
    s['q'] = pd.qcut(score, 5, labels=False, duplicates='drop')
    print(f"\n  {label}")
    print(f"    {'quintile':>10s} {'N':>6s} {'mean dev':>9s} {'SD(dev)':>8s} {'mean|dev|':>10s} "
          f"{'P|d|>15':>8s} {'P d>15':>8s} {'P d<-15':>8s}")
    out = []
    for q, gq in s.groupby('q'):
        out.append((gq.D.std(), gq.D.abs().mean()))
        print(f"    {'Q'+str(int(q)+1):>10s} {len(gq):6d} {gq.D.mean():+9.3f} {gq.D.std():8.3f} "
              f"{gq.D.abs().mean():10.3f} {(gq.D.abs()>15).mean():8.4f} "
              f"{(gq.D>15).mean():8.4f} {(gq.D<-15).mean():8.4f}")
    sds = [o[0] for o in out]
    mono = all(sds[i] <= sds[i + 1] for i in range(len(sds) - 1))
    print(f"    spread Q5-Q1 = {sds[-1]-sds[0]:+.3f} sd pts   VarRatio = "
          f"{(sds[-1]/sds[0])**2:.4f}   monotone: {mono}")
    return sds


mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                    max_depth=4, min_samples_leaf=80,
                                    l2_regularization=1.0, random_state=0)
mdl.fit(tr[X], tr.D.abs())
te = te.copy()
te['score'] = mdl.predict(te[X])
tr_pred = mdl.predict(tr[X])
print(f"  in-sample corr(score, |D|)  {np.corrcoef(tr_pred, tr.D.abs())[0,1]:+.4f}")
print(f"  OUT-OF-SAMPLE corr(score, |D|) {np.corrcoef(te.score, te.D.abs())[0,1]:+.4f}")
table(te, te.score, "RAW difficulty score  (test seasons)")

# --- the market's own expectation: whatever it prices for that total & spread --
print("\n  " + "-" * 74)
print("  ORTHOGONALISED: score residualised against (total, spread, |spread|).")
print("  This is the part of 'difficulty' the market is NOT already pricing.")
A = np.column_stack([np.ones(len(te)), te.total, te.spread, te.absspread,
                     te.total ** 2, te.absspread ** 2])
bb, *_ = np.linalg.lstsq(A, te.score.values, rcond=None)
te['score_orth'] = te.score.values - A @ bb
print(f"    R2 of (total, spread) explaining the score: "
      f"{1-((te.score_orth)**2).sum()/((te.score-te.score.mean())**2).sum():.4f}")
table(te, te.score_orth, "ORTHOGONAL difficulty  (test seasons)")

# --- and the market's own dispersion benchmark, directly ---------------------
print("\n  " + "-" * 74)
print("  CONTROL: sd(D) by closing TOTAL quintile alone (what the market prices)")
table(te, te.total, "closing total (test seasons)")
