"""SIDE FORECAST DIFFICULTY -- are some SPREADS / MONEYLINES harder to forecast?

The reverse of MATCHUP_DISPERSION_STUDY.md. There the closing total was the
FORECAST being graded. Here it is an EXPLANATORY VARIABLE, and the graded
forecasts are the side markets.

  spread     D_spr = actual home margin - closing-spread implied margin
                   = (F_H - F_R) + CLOSING SPREAD_H
             ask whether Var(D_spr | total, X) varies systematically.

  moneyline  de-vig the closing pair to p = P(home win), then grade with
             EXCESS BRIER = (Y - p)^2 - p(1-p).
             Under perfect calibration this has mean ZERO at every p, so it
             isolates "harder than the price says" from "closer to a coin flip".
             A raw Brier would simply rediscover that p near 0.5 is uncertain.

HIERARCHY (stop at the first failure):
  1  spread positive control     -- does margin-error SD rise with the total?
  2  moneyline positive control  -- does calibration/excess Brier depend on the
                                    total at a fixed implied probability?
  3  incremental                 -- do point-in-time matchup variables add
                                    anything beyond spread + total, OOS?
  4  OOS difficulty score        -- can we rank games by side-forecast
                                    imprecision out of sample?
  5  Kalshi                      -- NOT RUN unless 4 passes.

NO KALSHI DATA ANYWHERE IN THIS FILE. Same prohibitions as the totals study:
no random split, `STD` is season-to-date and unused, DATASET_H coalesced,
every feature shift(1) within season.
"""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from scipy import stats

SRC = '/mnt/c/NBA2/dfMaster_OT_2017-2026.csv'
TRAIN_END = 2021
WINDOWS = (5, 10, 20)
MINP = {5: 3, 10: 5, 20: 8}
RNG = np.random.default_rng(20260924)
OUT = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s); OUT.append(s)


def hdr(t):
    say("\n" + "=" * 78); say(t); say("=" * 78)


# ---------------------------------------------------------------- Part 0
hdr("PART 0 -- AUDIT")
raw = pd.read_csv(SRC, low_memory=False)
alt = 'BIGDATABALL\nDATASET_H'
ds = raw['DATASET_H'].fillna(raw[alt]).astype(str)

d = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce'),
    'gid': raw['GAME-ID'],
    'th': raw['TEAM_H'].astype(str), 'tr': raw['TEAM_R'].astype(str),
    'total': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'spread': pd.to_numeric(raw['CLOSING SPREAD_H'], errors='coerce'),
    'ml_h': pd.to_numeric(raw['MONEYLINE_H'], errors='coerce'),
    'ml_r': pd.to_numeric(raw['MONEYLINE_R'], errors='coerce'),
    'f_h': pd.to_numeric(raw['F_H'], errors='coerce'),
    'f_r': pd.to_numeric(raw['F_R'], errors='coerce'),
    'rest_h': raw['TEAM\nREST DAYS_H'].astype(str),
    'rest_r': raw['TEAM\nREST DAYS_R'].astype(str),
    'dataset': ds})
for side in ('H', 'R'):
    for c, nm in (('POSS', 'poss'), ('PACE', 'pace'), ('OEFF', 'oeff'), ('DEFF', 'deff'),
                  ('3PA', 'tpa'), ('3P', 'tpm'), ('FGA', 'fga'), ('FTA', 'fta'),
                  ('OR', 'orb'), ('DR', 'drb'), ('TO', 'tov'), ('PF', 'pf')):
        d[f'{nm}_{side.lower()}'] = pd.to_numeric(raw[f'{c}_{side}'], errors='coerce')

d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)
d['playoff'] = d.dataset.str.contains('Playoff', case=False)
d['margin'] = d.f_h - d.f_r
d['home_win'] = (d.margin > 0).astype(float)

say(f"rows {len(d)}   duplicate GAME-ID {d.gid.duplicated().sum()}")
say(f"closing spread present {100*d.spread.notna().mean():.2f}%   "
    f"moneyline pair present {100*(d.ml_h.notna()&d.ml_r.notna()).mean():.2f}%")
say(f"ties (margin == 0): {(d.margin==0).sum()}")

d = d.dropna(subset=['total', 'spread', 'margin']).copy()
d = d[d.margin != 0]
# ---- the two graded forecasts -------------------------------------------
d['D_spr'] = d.margin + d.spread            # >0 = home beat the spread
has_ml = d.ml_h.notna() & d.ml_r.notna() & (d.ml_h.abs() >= 100) & (d.ml_r.abs() >= 100)
a2p = lambda m: np.where(m < 0, -m / (-m + 100.0), 100.0 / (m + 100.0))
d['p'] = np.nan
rh, rr = a2p(d.loc[has_ml, 'ml_h']), a2p(d.loc[has_ml, 'ml_r'])
d.loc[has_ml, 'p'] = rh / (rh + rr)
d['xbrier'] = (d.home_win - d.p) ** 2 - d.p * (1 - d.p)

say(f"\nusable rows {len(d)}   with moneyline {int(has_ml.sum())}")
say(f"D_spread : mean {d.D_spr.mean():+.4f}  sd {d.D_spr.std():.4f}  "
    f"median {d.D_spr.median():+.3f}")
mm = d.dropna(subset=['p'])
say(f"moneyline: mean p {mm.p.mean():.4f}  home win rate {mm.home_win.mean():.4f}  "
    f"Brier {((mm.p-mm.home_win)**2).mean():.5f}")
say(f"           EXCESS Brier mean {mm.xbrier.mean():+.5f} "
    f"(zero under perfect calibration)")
say(f"           log loss {-(mm.home_win*np.log(mm.p)+(1-mm.home_win)*np.log(1-mm.p)).mean():.5f}")

# ---------------------------------------------------------------- Part 1
hdr("PART 1 -- SPREAD POSITIVE CONTROL: does margin-error SD rise with the total?")


def dtable(sub, score, label, target='D_spr', n_q=5):
    s = sub.dropna(subset=[target]).copy()
    s['q'] = pd.qcut(score.loc[s.index] if hasattr(score, 'loc') else score,
                     n_q, labels=False, duplicates='drop')
    say(f"\n{label}")
    say(f"  {'bucket':>10s} {'N':>6s} {'mean':>8s} {'SD':>8s} {'mean|.|':>8s} "
        f"{'P|.|>10':>8s} {'P|.|>15':>8s}")
    sds = []
    for q, g in s.groupby('q'):
        sds.append(g[target].std())
        say(f"  {'Q'+str(int(q)+1):>10s} {len(g):6d} {g[target].mean():+8.3f} "
            f"{g[target].std():8.3f} {g[target].abs().mean():8.3f} "
            f"{(g[target].abs()>10).mean():8.4f} {(g[target].abs()>15).mean():8.4f}")
    mono = all(sds[i] <= sds[i + 1] for i in range(len(sds) - 1))
    say(f"  SD Q5/Q1 = {sds[-1]/sds[0]:.4f}   monotone: {mono}")
    return sds[-1] / sds[0], mono


r_tot = dtable(d, d.total, "SD(D_spread) by closing-total quintile")
say("\n  same, by |closing spread| (the other market control):")
dtable(d, d.spread.abs(), "SD(D_spread) by |closing spread| quintile")

# is the total effect on margin dispersion mechanical? compare slopes
o = d.copy(); o['tb'] = pd.qcut(o.total, 8, duplicates='drop')
rr8 = o.groupby('tb', observed=True).agg(mid=('total', 'mean'), sd=('D_spr', 'std'))
sl = np.polyfit(rr8.mid, rr8.sd, 1)[0]
say(f"\n  8-bin slope of SD(D_spread) vs total: {sl:+.5f} pts per pt of total")
say(f"     (for comparison, SD(D_total) vs total was +0.04187)")

# ---------------------------------------------------------------- Part 2
hdr("PART 2 -- MONEYLINE POSITIVE CONTROL: does calibration depend on the total?")
say("EXCESS Brier = (Y-p)^2 - p(1-p); mean zero under perfect calibration at any p")
say(f"\n  {'total quintile':>15s} {'N':>6s} {'mean p':>8s} {'win rate':>9s} "
    f"{'bias':>8s} {'Brier':>8s} {'xBrier':>9s} {'logloss':>8s}")
mm = d.dropna(subset=['p']).copy()
mm['tb'] = pd.qcut(mm.total, 5, labels=False, duplicates='drop')
xb = []
for q, g in mm.groupby('tb'):
    ll = -(g.home_win * np.log(g.p) + (1 - g.home_win) * np.log(1 - g.p)).mean()
    xb.append(g.xbrier.mean())
    say(f"  {'Q'+str(int(q)+1):>15s} {len(g):6d} {g.p.mean():8.4f} "
        f"{g.home_win.mean():9.4f} {g.home_win.mean()-g.p.mean():+8.4f} "
        f"{((g.p-g.home_win)**2).mean():8.5f} {g.xbrier.mean():+9.5f} {ll:8.5f}")
say(f"  xBrier Q5-Q1 = {xb[-1]-xb[0]:+.5f}")
# formal test: does total add to a logit in p?
from sklearn.linear_model import LogisticRegression
lg = np.log(mm.p / (1 - mm.p)).values
X2 = np.column_stack([lg, (mm.total - mm.total.mean()) / 10.0])
m0 = LogisticRegression(fit_intercept=True, C=1e6, max_iter=2000).fit(lg[:, None], mm.home_win)
m1 = LogisticRegression(fit_intercept=True, C=1e6, max_iter=2000).fit(X2, mm.home_win)
ll0 = -m0.predict_log_proba(lg[:, None])[np.arange(len(mm)), mm.home_win.astype(int)].sum()
ll1 = -m1.predict_log_proba(X2)[np.arange(len(mm)), mm.home_win.astype(int)].sum()
lr = 2 * (ll0 - ll1)
say(f"\n  logit(Y) ~ logit(p) [+ total/10]:  coef on total {m1.coef_[0][1]:+.5f}"
    f"   LR chi2 {lr:.3f}  p = {1-stats.chi2.cdf(lr,1):.4f}")
say(f"  coef on logit(p) {m1.coef_[0][0]:+.4f} (1.0 = perfectly calibrated slope)")

# ---------------------------------------------------------------- PIT features
hdr("PART 3 SETUP -- POINT-IN-TIME STATE (same builder as the totals study)")
long = []
for side, opp in (('h', 'r'), ('r', 'h')):
    long.append(pd.DataFrame({
        'gid': d.gid, 'season': d.season, 'date': d.date, 'side': side,
        'team': d[f't{side}'], 'poss': d[f'poss_{side}'], 'pace': d[f'pace_{side}'],
        'oeff': d[f'oeff_{side}'], 'deff': d[f'deff_{side}'],
        'pts': d[f'f_{side}'], 'opp_pts': d[f'f_{opp}'],
        'margin': d[f'f_{side}'] - d[f'f_{opp}'],
        'tpa': d[f'tpa_{side}'], 'tpm': d[f'tpm_{side}'], 'fga': d[f'fga_{side}'],
        'fta': d[f'fta_{side}'], 'orb': d[f'orb_{side}'], 'drb': d[f'drb_{side}'],
        'tov': d[f'tov_{side}'], 'pf': d[f'pf_{side}'],
        'o_tpa': d[f'tpa_{opp}'], 'o_fga': d[f'fga_{opp}'], 'o_fta': d[f'fta_{opp}'],
        'o_orb': d[f'orb_{opp}'], 'o_drb': d[f'drb_{opp}'], 'o_tov': d[f'tov_{opp}'],
        'o_pf': d[f'pf_{opp}']}))
L = pd.concat(long).sort_values(['team', 'date']).reset_index(drop=True)
sp = lambda x, y: x / y.replace(0, np.nan)
L['tp_rate'] = sp(L.tpa, L.fga); L['ft_rate'] = sp(L.fta, L.fga)
L['o_tp_rate'] = sp(L.o_tpa, L.o_fga); L['o_ft_rate'] = sp(L.o_fta, L.o_fga)
L['orb_rate'] = sp(L.orb, L.orb + L.o_drb); L['drb_rate'] = sp(L.drb, L.drb + L.o_orb)
L['tov_rate'] = sp(L.tov, L.poss); L['ftov_rate'] = sp(L.o_tov, L.poss)
L['pf_rate'] = sp(L.pf, L.poss); L['o_pf_rate'] = sp(L.o_pf, L.poss)
L['net'] = L.oeff - L.deff

MEANS = ['pace', 'oeff', 'deff', 'net', 'tp_rate', 'ft_rate', 'o_tp_rate',
         'o_ft_rate', 'orb_rate', 'drb_rate', 'tov_rate', 'ftov_rate',
         'pf_rate', 'o_pf_rate']
SDS = ['pace', 'margin', 'pts', 'opp_pts', 'net', 'oeff', 'tpm']
g = L.groupby(['team', 'season'])
for w in WINDOWS:
    mp = MINP[w]
    for c in MEANS:
        L[f'{c}_m{w}'] = g[c].transform(lambda s: s.shift(1).rolling(w, min_periods=mp).mean())
    for c in SDS:
        L[f'{c}_sd{w}'] = g[c].transform(lambda s: s.shift(1).rolling(w, min_periods=mp).std())
L['n_prior'] = g.cumcount()
PIT = [c for c in L.columns if any(c.endswith(f'_m{w}') or c.endswith(f'_sd{w}')
                                   for w in WINDOWS)] + ['n_prior']
W = L[['gid', 'side'] + PIT].pivot(index='gid', columns='side')
W.columns = [f'{a}_{b}' for a, b in W.columns]
n0 = len(d)
d = d.merge(W, left_on='gid', right_index=True, how='left')
say(f"PIT features per team {len(PIT)}   join {n0} -> {len(d)}  gid unique {d.gid.is_unique}")

# matchup features aimed at MARGIN uncertainty
F = {}
F['margin_vol'] = d.margin_sd10_h + d.margin_sd10_r     # how variable each team's margins are
F['net_vol'] = d.net_sd10_h + d.net_sd10_r              # net-rating instability
F['net_gap'] = (d.net_m10_h - d.net_m10_r).abs()        # mismatch size
F['pace_sum'] = d.pace_m10_h + d.pace_m10_r             # more possessions -> wider margin
F['pace_vol'] = d.pace_sd10_h + d.pace_sd10_r
F['oeff_vol'] = d.oeff_sd10_h + d.oeff_sd10_r
F['tpm_vol'] = d.tpm_sd10_h + d.tpm_sd10_r              # 3pt variance drives blowouts
F['tp_dep'] = d.tp_rate_m10_h + d.tp_rate_m10_r
F['tp_exp'] = d.tp_rate_m10_h * d.o_tp_rate_m10_r + d.tp_rate_m10_r * d.o_tp_rate_m10_h
F['eff_h_vs_d_r'] = d.oeff_m10_h - d.deff_m10_r
F['eff_r_vs_d_h'] = d.oeff_m10_r - d.deff_m10_h
F['eff_mismatch'] = (F['eff_h_vs_d_r'] - F['eff_r_vs_d_h']).abs()
F['ft_exp'] = d.ft_rate_m10_h * d.o_pf_rate_m10_r + d.ft_rate_m10_r * d.o_pf_rate_m10_h
F['reb_sum'] = d.orb_rate_m10_h * (1 - d.drb_rate_m10_r) + d.orb_rate_m10_r * (1 - d.drb_rate_m10_h)
F['tov_exp'] = d.tov_rate_m10_h * d.ftov_rate_m10_r + d.tov_rate_m10_r * d.ftov_rate_m10_h
F['pts_vol'] = d.pts_sd10_h + d.pts_sd10_r
F['opp_pts_vol'] = d.opp_pts_sd10_h + d.opp_pts_sd10_r
for k, v in F.items():
    d[k] = v
d['b2b_h'] = d.rest_h.str.contains('B2B').astype(int)
d['b2b_r'] = d.rest_r.str.contains('B2B').astype(int)
d['b2b_any'] = ((d.b2b_h + d.b2b_r) > 0).astype(int)
d['is_playoff'] = d.playoff.astype(int)
d['absspread'] = d.spread.abs()

MATCH = list(F.keys()) + ['b2b_h', 'b2b_r', 'b2b_any', 'is_playoff']
MARKET = ['total', 'absspread', 'spread']
say(f"matchup features {len(MATCH)}   market controls {MARKET}")

m = d.dropna(subset=MATCH + MARKET + ['D_spr']).copy()
tr, te = m[m.season <= TRAIN_END].copy(), m[m.season > TRAIN_END].copy()
say(f"modelling rows {len(m)}   train {len(tr)}   test {len(te)}")

# ---------------------------------------------------------------- Part 3/4
hdr("PART 3/4 -- DOES MATCHUP STATE ADD BEYOND SPREAD + TOTAL?  (OOS)")


def fitp(train, test, feats, target, kind='gbm'):
    X, y = train[feats].values, train[target].values
    if kind == 'ridge':
        mu, sd = X.mean(0), X.std(0) + 1e-9
        mdl = RidgeCV(alphas=np.logspace(-2, 4, 25)).fit((X - mu) / sd, y)
        return ((test[feats].values - mu) / sd) @ mdl.coef_ + mdl.intercept_
    mdl = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.05, max_depth=3,
                                        min_samples_leaf=100, l2_regularization=1.0,
                                        random_state=0).fit(X, y)
    return mdl.predict(test[feats].values)


tr['absD'] = tr.D_spr.abs(); te['absD'] = te.D_spr.abs()
say("TARGET: |D_spread|")
for nm, ff in (('market only (total,|spr|,spr)', MARKET),
               ('matchup only', MATCH),
               ('market + matchup', MARKET + MATCH)):
    p = fitp(tr, te, ff, 'absD')
    say(f"  {nm:30s} OOS corr {np.corrcoef(p, te.absD)[0,1]:+.4f}   "
        f"MAE {np.abs(p-te.absD).mean():.4f}")
te['score'] = fitp(tr, te, MATCH, 'absD')
ins = fitp(tr, tr, MATCH, 'absD')
say(f"\n  in-sample corr {np.corrcoef(ins, tr.absD)[0,1]:+.4f}  vs  "
    f"OOS {np.corrcoef(te.score, te.absD)[0,1]:+.4f}")
r_spr = dtable(te, te.score, "DECISIVE OOS TABLE -- spread difficulty score")

A = np.column_stack([np.ones(len(te)), te.total, te.absspread, te.season,
                     te.total ** 2, te.absspread ** 2])
bb, *_ = np.linalg.lstsq(A, te.score.values, rcond=None)
te['score_res'] = te.score.values - A @ bb
r_spr_res = dtable(te, te.score_res, "RESIDUALISED on total, |spread|, season")

# moneyline branch
hdr("PART 4b -- MONEYLINE: can matchup state predict EXCESS BRIER?")
mm2 = m.dropna(subset=['xbrier']).copy()
trm, tem = mm2[mm2.season <= TRAIN_END], mm2[mm2.season > TRAIN_END].copy()
say(f"train {len(trm)}  test {len(tem)}")
for nm, ff in (('market only', MARKET), ('matchup only', MATCH),
               ('market + matchup', MARKET + MATCH)):
    p = fitp(trm, tem, ff, 'xbrier')
    say(f"  {nm:20s} OOS corr with xBrier {np.corrcoef(p, tem.xbrier)[0,1]:+.4f}")
tem['mlscore'] = fitp(trm, tem, MATCH, 'xbrier')
tem['q'] = pd.qcut(tem.mlscore, 5, labels=False, duplicates='drop')
say(f"\n  {'bucket':>8s} {'N':>6s} {'mean p':>8s} {'win rate':>9s} {'xBrier':>10s} {'Brier':>8s}")
xq = []
for q, g in tem.groupby('q'):
    xq.append(g.xbrier.mean())
    say(f"  {'Q'+str(int(q)+1):>8s} {len(g):6d} {g.p.mean():8.4f} {g.home_win.mean():9.4f} "
        f"{g.xbrier.mean():+10.5f} {((g.p-g.home_win)**2).mean():8.5f}")
say(f"  xBrier Q5-Q1 = {xq[-1]-xq[0]:+.5f}  (positive = Q5 genuinely harder)")

# ---------------------------------------------------------------- inference
hdr("INFERENCE -- season-block bootstrap and permutation null (spread branch)")
seasons = te.season.unique()
boot = []
for _ in range(2000):
    pick = RNG.choice(seasons, len(seasons), replace=True)
    sub = pd.concat([te[te.season == s] for s in pick])
    q = pd.qcut(sub.score, 5, labels=False, duplicates='drop')
    a, b = sub.D_spr[q == 0], sub.D_spr[q == 4]
    if len(a) > 50 and len(b) > 50:
        boot.append(b.std() / a.std())
say(f"  SD Q5/Q1 {r_spr[0]:.4f}  season-block 95% CI "
    f"[{np.percentile(boot,2.5):.4f}, {np.percentile(boot,97.5):.4f}]")
perm = []
for _ in range(300):
    t2 = tr.copy()
    t2['absD'] = t2.groupby('season').absD.transform(lambda s: RNG.permutation(s.values))
    sc = fitp(t2, te, MATCH, 'absD')
    q = pd.qcut(sc, 5, labels=False, duplicates='drop')
    perm.append(te.D_spr[q == 4].std() / te.D_spr[q == 0].std())
perm = np.array(perm)
say(f"  permutation null median {np.median(perm):.4f}  95th {np.percentile(perm,95):.4f}"
    f"  max {perm.max():.4f}")
say(f"  observed {r_spr[0]:.4f}  ->  p = {(perm >= r_spr[0]).mean():.4f}")

say("\nPER-SEASON REPLICATION (spread branch)")
for s, gs in te.groupby('season'):
    q = pd.qcut(gs.score, 5, labels=False, duplicates='drop')
    say(f"  {s}  n={len(gs):5d}  SD Q5/Q1 {gs.D_spr[q==4].std()/gs.D_spr[q==0].std():.4f}")

hdr("DECISION")
c1 = r_spr[1]; c2 = r_spr[0] >= 1.15; c3 = r_spr_res[0] >= 1.15
c5 = (perm >= r_spr[0]).mean() < 0.05
say(f"  1. spread positive control (SD rises with total) : "
    f"{r_tot[0]:.4f} ratio, monotone {r_tot[1]}")
say(f"  2. moneyline calibration depends on total        : see Part 2 LR test")
say(f"  3. orders dispersion OOS / monotone              : {c1}")
say(f"  4. SD Q5/Q1 >= 1.15                              : {c2} ({r_spr[0]:.4f})")
say(f"  5. survives conditioning on total+spread         : {c3} ({r_spr_res[0]:.4f})")
say(f"  6. beats permutation null                        : {c5}")
say("")
say("  STAGE 5 (Kalshi) IS GATED ON 3-6 AND IS NOT RUN HERE.")

with open('/home/dpope/projects/nba_entropy_replication/side_forecast_results.txt', 'w') as f:
    f.write("\n".join(OUT))
print("\n[written to side_forecast_results.txt]")
