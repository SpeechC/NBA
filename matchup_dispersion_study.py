"""MATCHUP DISPERSION STUDY -- historical team boxscores ONLY.

Question: are some identifiable PREGAME matchups systematically harder for the
closing total to price?  "Harder" = wider conditional distribution of

    D = actual total points - closing total

We are NOT predicting the sign of D.

HARD PROHIBITIONS OBSERVED
  * No Kalshi data, prices, mids, ladders or ladder-derived sigma. Nothing in
    this file reads a Kalshi source.
  * No current-game boxscore information in any predictor.
  * No random train/test split -- season blocks only.
  * `STD` is season-to-date, NOT standard deviation, and is never used.
  * DATASET_H is coalesced with `BIGDATABALL\\nDATASET_H`.
  * No in-sample fitted heteroskedasticity reported as evidence.
  * No new subgroup search after seeing test-period results.

Sections follow the agreed protocol: Part 0 audit, I point-in-time state,
II matchup interactions, III archetype screen on frozen cutoffs, IV conditional
scale model, V decisive OOS table, VI incremental to total and spread,
VII per-season replication, VIII inference, IX failure controls.
"""
import warnings, sys, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV, LinearRegression
from scipy import stats

SRC = '/mnt/c/NBA2/dfMaster_OT_2017-2026.csv'
TRAIN_END = 2021              # discovery seasons 2017-2021; test 2022-2025
WINDOWS = (5, 10, 20)
MINP = {5: 3, 10: 5, 20: 8}
RNG = np.random.default_rng(20260924)
OUT = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    OUT.append(s)


def hdr(t):
    say("\n" + "=" * 78)
    say(t)
    say("=" * 78)


# ============================================================ PART 0: audit
hdr("PART 0 -- DATA AUDIT")
raw = pd.read_csv(SRC, low_memory=False)
say(f"raw rows {len(raw)}   columns {len(raw.columns)}")

alt = 'BIGDATABALL\nDATASET_H'
ds = raw['DATASET_H']
if alt in raw.columns:
    n_before = ds.notna().sum()
    ds = ds.fillna(raw[alt])
    say(f"DATASET_H non-null {n_before} -> {ds.notna().sum()} after coalescing "
        f"with {alt!r}  (+{ds.notna().sum()-n_before} rows recovered)")
else:
    say(f"WARNING: {alt!r} not present")
ds = ds.astype(str)

d = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce'),
    'gid': raw['GAME-ID'],
    'th': raw['TEAM_H'].astype(str), 'tr': raw['TEAM_R'].astype(str),
    'total': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'spread': pd.to_numeric(raw['CLOSING SPREAD_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce'),
    'f_h': pd.to_numeric(raw['F_H'], errors='coerce'),
    'f_r': pd.to_numeric(raw['F_R'], errors='coerce'),
    'rest_h': raw['TEAM\nREST DAYS_H'].astype(str),
    'rest_r': raw['TEAM\nREST DAYS_R'].astype(str),
    'dataset': ds})
for side in ('H', 'R'):
    for c, nm in (('POSS', 'poss'), ('PACE', 'pace'), ('OEFF', 'oeff'), ('DEFF', 'deff'),
                  ('3PA', 'tpa'), ('3P', 'tpm'), ('FGA', 'fga'), ('FG', 'fgm'),
                  ('FTA', 'fta'), ('FT', 'ftm'), ('OR', 'orb'), ('DR', 'drb'),
                  ('TO', 'tov'), ('PF', 'pf')):
        d[f'{nm}_{side.lower()}'] = pd.to_numeric(raw[f'{c}_{side}'], errors='coerce')

d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)
d['playoff'] = d.dataset.str.contains('Playoff', case=False)

# one-game-per-event integrity
dups = d.gid.duplicated().sum()
say(f"duplicate GAME-ID rows: {dups}")
rec = (d.f_h + d.f_r - d.pts).abs()
bad_rec = (rec > 0.5).sum()
say(f"home+away points reconcile to TOTAL_PTS: {(len(d)-bad_rec)}/{len(d)} "
    f"({100*(1-bad_rec/len(d)):.2f}%)  max abs mismatch {rec.max():.1f}")

say(f"\nseasons {sorted(d.season.unique())}")
tab = d.groupby('season').agg(games=('gid', 'nunique'),
                              playoffs=('playoff', 'sum'),
                              pct_total=('total', lambda s: 100 * s.notna().mean()),
                              pct_spread=('spread', lambda s: 100 * s.notna().mean()))
tab['regular'] = tab.games - tab.playoffs
say(tab[['games', 'regular', 'playoffs', 'pct_total', 'pct_spread']].round(2).to_string())
say(f"\nTOTAL games {d.gid.nunique()}   playoffs {d.playoff.sum()} "
    f"({100*d.playoff.mean():.1f}%)")
say(f"closing total present {100*d.total.notna().mean():.2f}%   "
    f"closing spread present {100*d.spread.notna().mean():.2f}%")

n0 = len(d)
d = d.dropna(subset=['total', 'spread', 'pts', 'date']).copy()
d = d[d.pts > 0]
say(f"rows dropped for missing total/spread/pts: {n0-len(d)}  -> {len(d)} remain")
d['D'] = d.pts - d.total

# ============================================================ baseline facts
hdr("BASELINE FACTS (positive control) -- reproduce before anything new")
say(f"SD(D) {d.D.std():.4f}   mean {d.D.mean():+.4f}   median {d.D.median():+.4f}")
say(f"P(|D|>15) {(d.D.abs()>15).mean():.4f}   P(|D|>20) {(d.D.abs()>20).mean():.4f}")


def qtable(sub, score, label, n_q=5):
    s = sub.copy()
    s['q'] = pd.qcut(score, n_q, labels=False, duplicates='drop')
    say(f"\n{label}")
    say(f"  {'bucket':>10s} {'N':>6s} {'meanD':>8s} {'SD(D)':>8s} {'mean|D|':>8s} "
        f"{'P|D|>15':>8s} {'P|D|>20':>8s} {'P D>15':>8s} {'P D<-15':>8s}")
    sds, p15s = [], []
    for q, g in s.groupby('q'):
        sds.append(g.D.std()); p15s.append((g.D.abs() > 15).mean())
        say(f"  {'Q'+str(int(q)+1):>10s} {len(g):6d} {g.D.mean():+8.3f} {g.D.std():8.3f} "
            f"{g.D.abs().mean():8.3f} {(g.D.abs()>15).mean():8.4f} "
            f"{(g.D.abs()>20).mean():8.4f} {(g.D>15).mean():8.4f} {(g.D<-15).mean():8.4f}")
    mono = all(sds[i] <= sds[i + 1] for i in range(len(sds) - 1))
    say(f"  SD Q5/Q1 = {sds[-1]/sds[0]:.4f}   P(|D|>15) Q5-Q1 = {p15s[-1]-p15s[0]:+.4f}"
        f"   monotone: {mono}")
    return sds[-1] / sds[0], p15s[-1] - p15s[0], mono


qtable(d, d.total, "Closing-total quintiles (ALL seasons)")

# ============================================================ PART I: PIT state
hdr("PART I -- POINT-IN-TIME TEAM STATE")
long = []
for side, opp in (('h', 'r'), ('r', 'h')):
    long.append(pd.DataFrame({
        'gid': d.gid, 'season': d.season, 'date': d.date, 'side': side,
        'team': d[f't{side}'],
        'poss': d[f'poss_{side}'], 'pace': d[f'pace_{side}'],
        'oeff': d[f'oeff_{side}'], 'deff': d[f'deff_{side}'],
        'pts': d[f'f_{side}'], 'opp_pts': d[f'f_{opp}'],
        'tpa': d[f'tpa_{side}'], 'tpm': d[f'tpm_{side}'], 'fga': d[f'fga_{side}'],
        'fta': d[f'fta_{side}'], 'orb': d[f'orb_{side}'], 'drb': d[f'drb_{side}'],
        'tov': d[f'tov_{side}'], 'pf': d[f'pf_{side}'],
        'o_tpa': d[f'tpa_{opp}'], 'o_tpm': d[f'tpm_{opp}'], 'o_fga': d[f'fga_{opp}'],
        'o_fta': d[f'fta_{opp}'], 'o_orb': d[f'orb_{opp}'], 'o_drb': d[f'drb_{opp}'],
        'o_tov': d[f'tov_{opp}'], 'o_pf': d[f'pf_{opp}'], 'gtot': d.pts}))
L = pd.concat(long).sort_values(['team', 'date']).reset_index(drop=True)

sp = lambda x, y: x / y.replace(0, np.nan)
L['tp_rate'] = sp(L.tpa, L.fga)              # 3PA share of shots
L['tp_pct'] = sp(L.tpm, L.tpa)
L['tp_share_pts'] = sp(3 * L.tpm, L.pts)     # fraction of scoring from threes
L['ft_rate'] = sp(L.fta, L.fga)
L['o_tp_rate'] = sp(L.o_tpa, L.o_fga)        # 3PA rate ALLOWED
L['o_tp_pct'] = sp(L.o_tpm, L.o_tpa)
L['o_ft_rate'] = sp(L.o_fta, L.o_fga)
L['orb_rate'] = sp(L.orb, L.orb + L.o_drb)
L['drb_rate'] = sp(L.drb, L.drb + L.o_orb)
L['tov_rate'] = sp(L.tov, L.poss)
L['ftov_rate'] = sp(L.o_tov, L.poss)         # forced turnovers
L['pf_rate'] = sp(L.pf, L.poss)
L['o_pf_rate'] = sp(L.o_pf, L.poss)          # fouls drawn
L['ppp'] = sp(L.pts, L.poss)
L['oppp'] = sp(L.opp_pts, L.poss)

MEANS = ['pace', 'poss', 'oeff', 'deff', 'ppp', 'oppp', 'tp_rate', 'tp_pct',
         'tp_share_pts', 'ft_rate', 'o_tp_rate', 'o_tp_pct', 'o_ft_rate',
         'orb_rate', 'drb_rate', 'tov_rate', 'ftov_rate', 'pf_rate', 'o_pf_rate']
SDS = ['pace', 'pts', 'opp_pts', 'gtot', 'oeff', 'tpm']

g = L.groupby(['team', 'season'])
for w in WINDOWS:
    mp = MINP[w]
    for c in MEANS:
        L[f'{c}_m{w}'] = g[c].transform(
            lambda s: s.shift(1).rolling(w, min_periods=mp).mean())
    for c in SDS:
        L[f'{c}_sd{w}'] = g[c].transform(
            lambda s: s.shift(1).rolling(w, min_periods=mp).std())
L['pace_trend'] = L['pace_m5'] - L['pace_m20']
L['n_prior'] = g.cumcount()

PIT = [c for c in L.columns if any(c.endswith(f'_m{w}') or c.endswith(f'_sd{w}')
                                   for w in WINDOWS)] + ['pace_trend', 'n_prior']
say(f"point-in-time features per team: {len(PIT)}  "
    f"(windows {WINDOWS}, all shift(1) within season)")

W = L[['gid', 'side'] + PIT].pivot(index='gid', columns='side')
W.columns = [f'{a}_{b}' for a, b in W.columns]
n_before = len(d)
d = d.merge(W, left_on='gid', right_index=True, how='left')
say(f"join audit: rows {n_before} -> {len(d)} (no duplication)  "
    f"gid unique {d.gid.is_unique}")

# ============================================================ PART II: matchups
hdr("PART II -- MATCHUP INTERACTIONS (each with a basketball interpretation)")
F = {}
F['pace_sum'] = d.pace_m10_h + d.pace_m10_r                      # combined tempo
F['pace_gap'] = (d.pace_m10_h - d.pace_m10_r).abs()              # tempo clash
F['pace_vol'] = d.pace_sd10_h + d.pace_sd10_r                    # tempo instability
F['pace_trend_gap'] = (d.pace_trend_h - d.pace_trend_r).abs()
F['score_vol'] = d.pts_sd10_h + d.pts_sd10_r                     # own scoring vol
F['gtot_vol'] = (d.gtot_sd10_h + d.gtot_sd10_r) / 2              # game-total vol
F['oeff_vol'] = d.oeff_sd10_h + d.oeff_sd10_r
F['tpm_vol'] = d.tpm_sd10_h + d.tpm_sd10_r                       # 3pt make variance
F['tp_dep'] = d.tp_share_pts_m10_h + d.tp_share_pts_m10_r        # 3pt dependence
F['tp_exp_h'] = d.tp_rate_m10_h * d.o_tp_rate_m10_r              # 3PA x allowance
F['tp_exp_r'] = d.tp_rate_m10_r * d.o_tp_rate_m10_h
F['tp_exp_sum'] = F['tp_exp_h'] + F['tp_exp_r']
F['tp_gap'] = (d.tp_rate_m10_h - d.tp_rate_m10_r).abs()
F['eff_h_vs_d_r'] = d.oeff_m10_h - d.deff_m10_r                  # off x opposing def
F['eff_r_vs_d_h'] = d.oeff_m10_r - d.deff_m10_h
F['eff_sum'] = d.oeff_m10_h + d.oeff_m10_r
F['eff_mismatch'] = (F['eff_h_vs_d_r'] - F['eff_r_vs_d_h']).abs()
F['volxvol'] = d.oeff_sd10_h * d.oeff_sd10_r                     # vol x opposing vol
F['ft_exp'] = d.ft_rate_m10_h * d.o_pf_rate_m10_r + d.ft_rate_m10_r * d.o_pf_rate_m10_h
F['foul_sum'] = d.pf_rate_m10_h + d.pf_rate_m10_r
F['reb_h'] = d.orb_rate_m10_h * (1 - d.drb_rate_m10_r)           # OREB x opposing DREB
F['reb_r'] = d.orb_rate_m10_r * (1 - d.drb_rate_m10_h)
F['reb_sum'] = F['reb_h'] + F['reb_r']
F['tov_exp'] = d.tov_rate_m10_h * d.ftov_rate_m10_r + d.tov_rate_m10_r * d.ftov_rate_m10_h
F['pace_x_eff'] = F['pace_sum'] * F['eff_sum'] / 100.0
F['n_prior'] = np.minimum(d.n_prior_h, d.n_prior_r)
for k, v in F.items():
    d[k] = v
d['b2b_h'] = d.rest_h.str.contains('B2B').astype(int)
d['b2b_r'] = d.rest_r.str.contains('B2B').astype(int)
d['b2b_any'] = ((d.b2b_h + d.b2b_r) > 0).astype(int)
d['three_in_four'] = (d.rest_h.str.contains('3IN4') | d.rest_r.str.contains('3IN4')).astype(int)
d['is_playoff'] = d.playoff.astype(int)
d['absspread'] = d.spread.abs()

MATCH = list(F.keys()) + ['b2b_h', 'b2b_r', 'b2b_any', 'three_in_four', 'is_playoff']
MARKET = ['total', 'absspread']
ALLF = MATCH + MARKET
say(f"matchup features: {len(MATCH)}   market controls: {MARKET}")

say("\nmissingness per feature (%):")
miss = (d[ALLF].isna().mean() * 100).round(2).sort_values(ascending=False)
say(miss.to_string())

m = d.dropna(subset=ALLF + ['D']).copy()
say(f"\nmodelling rows {len(m)} of {len(d)} (lost {len(d)-len(m)} to PIT warm-up)")
tr = m[m.season <= TRAIN_END].copy()
te = m[m.season > TRAIN_END].copy()
say(f"TRAIN seasons {sorted(tr.season.unique())} n={len(tr)}")
say(f"TEST  seasons {sorted(te.season.unique())} n={len(te)}")

# ============================================================ PART IX-a: timing audit
hdr("PART IX -- FEATURE-TIMING AUDIT (prove game t is excluded)")
samp = L[(L.n_prior >= 12)].sample(3, random_state=1)
for _, r in samp.iterrows():
    prior = L[(L.team == r.team) & (L.season == r.season) & (L.date < r.date)].tail(10)
    say(f"\n  {r.team} {r.season} game on {r.date.date()}  own pace this game "
        f"{r.pace:.2f}")
    say(f"    pace_m10 stored = {r.pace_m10:.4f}")
    say(f"    mean of the 10 PRIOR games = {prior.pace.mean():.4f}  "
        f"(dates {prior.date.min().date()} .. {prior.date.max().date()})")
    incl = np.isclose(r.pace_m10, pd.concat([prior.pace, pd.Series([r.pace])]).tail(10).mean())
    say(f"    matches prior-only: {np.isclose(r.pace_m10, prior.pace.mean())}   "
        f"would match if current game INCLUDED: {incl}")

# ============================================================ PART III: archetypes
hdr("PART III -- ARCHETYPE SCREEN (cutoffs frozen on TRAIN, applied to TEST)")
SCREEN = ['pace_sum', 'pace_gap', 'pace_vol', 'score_vol', 'tp_dep', 'tp_exp_sum',
          'eff_mismatch', 'ft_exp', 'reb_sum', 'tov_exp', 'total', 'absspread']
say(f"  {'feature':>14s} {'SD Q1':>8s} {'SD Q5':>8s} {'ratio':>7s} "
    f"{'m|D|Q1':>8s} {'m|D|Q5':>8s} {'P15 Q1':>7s} {'P15 Q5':>7s} {'Levene p':>9s}")
arch = []
for c in SCREEN:
    cut = np.quantile(tr[c], [0.2, 0.4, 0.6, 0.8])
    b = np.digitize(te[c], cut)
    q1, q5 = te.D[b == 0], te.D[b == 4]
    if len(q1) < 100 or len(q5) < 100:
        continue
    lp = stats.levene(q1, q5, center='median').pvalue
    arch.append((c, q5.std() / q1.std(), lp))
    say(f"  {c:>14s} {q1.std():8.3f} {q5.std():8.3f} {q5.std()/q1.std():7.4f} "
        f"{q1.abs().mean():8.3f} {q5.abs().mean():8.3f} {(q1.abs()>15).mean():7.4f} "
        f"{(q5.abs()>15).mean():7.4f} {lp:9.3g}")
say("\n  (interesting would be ~16.0 vs 21.0; 17.5 vs 18.2 is not)")

# ============================================================ PART IV/V: model
hdr("PART IV/V -- CONDITIONAL-SCALE MODEL, OUT OF SAMPLE")
say("target |D|; season-block design; no random split; no model tournament")


def fit_predict(train, test, feats, kind='gbm'):
    X, y = train[feats].values, train.D.abs().values
    if kind == 'gbm':
        mdl = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.05,
                                            max_depth=3, min_samples_leaf=100,
                                            l2_regularization=1.0, random_state=0)
    elif kind == 'ridge':
        mdl = RidgeCV(alphas=np.logspace(-2, 4, 25))
        mu, sd = X.mean(0), X.std(0) + 1e-9
        mdl.fit((X - mu) / sd, y)
        return (test[feats].values - mu) / sd @ mdl.coef_ + mdl.intercept_
    else:
        mdl = LinearRegression()
    mdl.fit(X, y)
    return mdl.predict(test[feats].values)


for kind in ('ridge', 'gbm'):
    te[f'score_{kind}'] = fit_predict(tr, te, MATCH, kind)
    ins = fit_predict(tr, tr, MATCH, kind)
    say(f"\n{kind.upper()}  in-sample corr(score,|D|) "
        f"{np.corrcoef(ins, tr.D.abs())[0,1]:+.4f}   "
        f"OUT-OF-SAMPLE {np.corrcoef(te[f'score_{kind}'], te.D.abs())[0,1]:+.4f}")

BEST = 'gbm'
r_gbm = qtable(te, te[f'score_{BEST}'], f"DECISIVE OOS TABLE -- {BEST} matchup score")
qtable(te, te['score_ridge'], "OOS table -- ridge matchup score")

# ============================================================ PART VI: incremental
hdr("PART VI -- INCREMENTAL TO CLOSING TOTAL AND SPREAD")
say("A. matchup score residualised on total, |spread|, season")
A = np.column_stack([np.ones(len(te)), te.total, te.absspread, te.season,
                     te.total ** 2, te.absspread ** 2])
bb, *_ = np.linalg.lstsq(A, te[f'score_{BEST}'].values, rcond=None)
te['score_res'] = te[f'score_{BEST}'].values - A @ bb
r2 = 1 - (te.score_res ** 2).sum() / ((te[f'score_{BEST}'] -
                                       te[f'score_{BEST}'].mean()) ** 2).sum()
say(f"   R2 of (total, |spread|, season) explaining the score: {r2:.4f}")
r_res = qtable(te, te.score_res, "OOS table -- RESIDUALISED matchup difficulty")

say("\nB. does matchup add OOS accuracy beyond f(total,|spread|)?")
base = fit_predict(tr, te, MARKET, 'gbm')
full = fit_predict(tr, te, MARKET + MATCH, 'gbm')
y = te.D.abs().values
for nm, p in (('total+spread only', base), ('total+spread+matchup', full)):
    say(f"   {nm:24s} OOS corr {np.corrcoef(p,y)[0,1]:+.4f}   "
        f"MAE {np.abs(p-y).mean():.4f}   RMSE {np.sqrt(((p-y)**2).mean()):.4f}")
say("   POSITIVE CONTROL: total+spread alone must reproduce the known effect")
qtable(te, base, "OOS table -- total+spread benchmark (positive control)")

# ============================================================ PART VII: replication
hdr("PART VII -- PER-SEASON REPLICATION")
say(f"  {'season':>8s} {'n':>6s} {'SD Q5/Q1':>9s} {'m|D| Q5-Q1':>11s} {'P15 Q5-Q1':>10s}")
for s, gs in te.groupby('season'):
    q = pd.qcut(gs[f'score_{BEST}'], 5, labels=False, duplicates='drop')
    a, b = gs.D[q == 0], gs.D[q == 4]
    say(f"  {s:8d} {len(gs):6d} {b.std()/a.std():9.4f} "
        f"{b.abs().mean()-a.abs().mean():+11.3f} "
        f"{(b.abs()>15).mean()-(a.abs()>15).mean():+10.4f}")
rs = te[~te.is_playoff.astype(bool)]
ps = te[te.is_playoff.astype(bool)]
say(f"\n  regular season n={len(rs)}   playoffs n={len(ps)} (secondary)")

# ============================================================ PART VIII: inference
hdr("PART VIII -- INFERENCE (season-block bootstrap + permutation null)")
seasons = te.season.unique()
boot = []
for _ in range(2000):
    pick = RNG.choice(seasons, len(seasons), replace=True)
    sub = pd.concat([te[te.season == s] for s in pick])
    q = pd.qcut(sub[f'score_{BEST}'], 5, labels=False, duplicates='drop')
    a, b = sub.D[q == 0], sub.D[q == 4]
    if len(a) > 50 and len(b) > 50:
        boot.append(b.std() / a.std())
lo, hi = np.percentile(boot, [2.5, 97.5])
say(f"  SD Q5/Q1 = {r_gbm[0]:.4f}   season-block 95% CI [{lo:.4f}, {hi:.4f}]")
say(f"  residualised SD Q5/Q1 = {r_res[0]:.4f}")

perm = []
for _ in range(400):
    t2 = tr.copy()
    t2['D'] = t2.groupby('season').D.transform(lambda s: RNG.permutation(s.values))
    sc = fit_predict(t2, te, MATCH, 'gbm')
    q = pd.qcut(sc, 5, labels=False, duplicates='drop')
    a, b = te.D[q == 0], te.D[q == 4]
    perm.append(b.std() / a.std())
perm = np.array(perm)
say(f"  PERMUTATION null (target shuffled within TRAIN season, 400 draws):")
say(f"    median {np.median(perm):.4f}   95th {np.percentile(perm,95):.4f}   "
    f"max {perm.max():.4f}")
say(f"    observed {r_gbm[0]:.4f}  ->  p = {(perm >= r_gbm[0]).mean():.4f}")

# ============================================================ PART IX: controls
hdr("PART IX -- REMAINING FAILURE CONTROLS")
say("Leakage control: shift every rolling feature back ONE ADDITIONAL game.")
g2 = L.groupby(['team', 'season'])
for c in ['pace', 'oeff', 'tp_rate']:
    L[f'{c}_lag'] = g2[c].transform(lambda s: s.shift(2).rolling(10, min_periods=5).mean())
W2 = L[['gid', 'side', 'pace_lag', 'oeff_lag', 'tp_rate_lag']].pivot(index='gid', columns='side')
W2.columns = [f'{a}_{b}' for a, b in W2.columns]
mm = m.merge(W2, left_on='gid', right_index=True, how='left')
mm['pace_sum_lag'] = mm.pace_lag_h + mm.pace_lag_r
mm['eff_sum_lag'] = mm.oeff_lag_h + mm.oeff_lag_r
mm['tp_dep_lag'] = mm.tp_rate_lag_h + mm.tp_rate_lag_r
sub = mm.dropna(subset=['pace_sum_lag', 'eff_sum_lag', 'tp_dep_lag'])
t2, e2 = sub[sub.season <= TRAIN_END], sub[sub.season > TRAIN_END]
LAGF = ['pace_sum_lag', 'eff_sum_lag', 'tp_dep_lag']
NOWF = ['pace_sum', 'eff_sum', 'tp_dep']
for nm, ff in (('shift(1) [normal]', NOWF), ('shift(2) [extra lag]', LAGF)):
    p = fit_predict(t2, e2, ff, 'gbm')
    say(f"   {nm:22s} OOS corr {np.corrcoef(p, e2.D.abs())[0,1]:+.4f}")
say("   (an extra lag should NOT improve things; improvement would suggest leakage)")

# ============================================================ decision
hdr("DECISION RULE")
c1 = r_gbm[2]
c2 = r_gbm[0] >= 1.15
c3 = r_res[0] >= 1.15
c4 = None
c5 = (perm >= r_gbm[0]).mean() < 0.05
say(f"  1. orders realised dispersion OOS (monotone)   : {c1}")
say(f"  2. SD Q5/Q1 >= 1.15                            : {c2}  (got {r_gbm[0]:.4f})")
say(f"  3. survives conditioning on total and spread   : {c3}  (got {r_res[0]:.4f})")
say(f"  4. replicates across test seasons              : see Part VII")
say(f"  5. beats permutation null                      : {c5}")
say("")
if c1 and c2 and c3 and c5:
    say("  PASS -- historical sportsbook data identifies reproducible matchup")
    say("  classes with materially different closing-total residual dispersion.")
else:
    say("  FAIL -- conclude NARROWLY: the available point-in-time team boxscore")
    say("  and matchup information does not identify persistent differences in")
    say("  closing-total forecast precision beyond the dispersion associated")
    say("  with the market total/spread. This does NOT mean every NBA game has")
    say("  identical uncertainty.")

with open('/home/dpope/projects/nba_entropy_replication/matchup_dispersion_results.txt', 'w') as f:
    f.write("\n".join(OUT))
print("\n[results written to matchup_dispersion_results.txt]")
