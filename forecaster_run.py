"""Executes PREREG_probabilistic_forecaster. Scored ONCE on holdout."""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold
from forecaster_build import build

FEATS = ["m", "CrewShock", "final7"]          # FROZEN, prereg §2
DEV, HOLD = [2021, 2022, 2023], [2024, 2025]
RNG = np.random.default_rng(42)

d = build()
tr, te = d[d.yr.isin(DEV)].copy(), d[d.yr.isin(HOLD)].copy()
print(f"development {len(tr):,}   holdout {len(te):,}")
print("NOTE: MOVE_COMBINED_OOS begins 2021-22, so the prereg's 2017-18 start is")
print("      unavailable. Split is forced by data, not chosen. Holdout n~2,000")
print("      is exactly the case prereg §3 priced at z=+1.09.\n")

Xtr, ytr = tr[FEATS].values, tr.y.values
Xte, yte = te[FEATS].values, te.y.values

# ---- Stage 1: logistic on development --------------------------------------
lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
print("STAGE 1  logistic  P(over) ~ m + CrewShock + final7")
for f, c in zip(FEATS, lr.coef_[0]):
    print(f"    {f:<12}{c:+.5f}")
print(f"    {'intercept':<12}{lr.intercept_[0]:+.5f}")

# ---- Stage 2: isotonic on OUT-OF-FOLD development predictions ---------------
oof = np.zeros(len(tr))
for a, b in KFold(5, shuffle=True, random_state=42).split(Xtr):
    oof[b] = LogisticRegression(max_iter=1000).fit(Xtr[a], ytr[a]).predict_proba(Xtr[b])[:, 1]
iso = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99).fit(oof, ytr)

p_raw = lr.predict_proba(Xte)[:, 1]
p = np.clip(iso.predict(p_raw), 0.01, 0.99)
print(f"\nholdout forecasts: mean {p.mean():.4f}  sd {p.std():.4f}  "
      f"range {p.min():.3f}-{p.max():.3f}")

# ---- P1 CALIBRATION SLOPE / INTERCEPT ---------------------------------------
lg = np.log(p / (1 - p))
cal = LogisticRegression(max_iter=1000).fit(lg.reshape(-1, 1), yte)
slope, icept = float(cal.coef_[0][0]), float(cal.intercept_[0])
ok_s = 0.8 <= slope <= 1.25
ok_i = -0.05 <= icept <= 0.05
print(f"\n=== P1 PRIMARY — calibration (prereg: slope [0.8,1.25], intercept [-0.05,+0.05]) ===")
print(f"    slope     {slope:+.4f}   {'PASS' if ok_s else 'FAIL'}")
print(f"    intercept {icept:+.4f}   {'PASS' if ok_i else 'FAIL'}")
print(f"    -> P1 {'PASSES' if (ok_s and ok_i) else 'FAILS'}")

# ---- P2 RELIABILITY ----------------------------------------------------------
print(f"\n=== P2 RELIABILITY — holdout deciles ===")
q = pd.qcut(p, 10, labels=False, duplicates="drop")
print(f"    {'decile':<8}{'n':>6}{'mean fcst':>11}{'actual':>9}{'gap':>9}")
gaps = []
for k in sorted(set(q)):
    mk = q == k
    mf, ac = p[mk].mean(), yte[mk].mean()
    gaps.append(abs(ac - mf))
    print(f"    {k+1:<8}{int(mk.sum()):>6}{100*mf:>10.2f}%{100*ac:>8.2f}%{100*(ac-mf):>+8.2f}pp")
print(f"    max |gap| {100*max(gaps):.2f}pp   mean |gap| {100*np.mean(gaps):.2f}pp")

# ---- P3 BRIER / LOG SCORE ----------------------------------------------------
b_model = (p - yte) ** 2
b_base = (0.5 - yte) ** 2
diff = b_base - b_model
se = diff.std() / math.sqrt(len(diff))
ll_m = -(yte*np.log(p) + (1-yte)*np.log(1-p)).mean()
ll_b = -np.log(0.5)
print(f"\n=== P3 BRIER / LOG SCORE (reported, NOT decisive — prereg §3) ===")
print(f"    Brier  model {b_model.mean():.5f}   baseline {b_base.mean():.5f}   "
      f"gain {diff.mean():+.6f}")
print(f"    paired se {se:.6f}   z = {diff.mean()/se:+.2f}   "
      f"(prereg predicted z~+1.09 at n~2,000)")
print(f"    log loss  model {ll_m:.5f}   baseline {ll_b:.5f}   "
      f"gain {ll_b-ll_m:+.6f}")

# ---- economics, reported only ------------------------------------------------
MULT, BE = 1 + (100/1.1)/100, 1.1/2.1
side = np.where(p >= 0.5, 1, 0)
win = (side == yte)
print(f"\n=== ECONOMICS (reported only, cannot pass or fail — prereg §6) ===")
print(f"    bet the model's side every game: {len(te):,} bets  "
      f"hit {100*win.mean():.2f}%  ROI {100*(MULT*win.mean()-1):+.2f}%")
for thr in (0.52, 0.54):
    m2 = (p >= thr) | (p <= 1-thr)
    if m2.sum() >= 50:
        w2 = win[m2]
        print(f"    |p-0.5| >= {thr-0.5:.2f}: {int(m2.sum()):>5} bets  "
              f"hit {100*w2.mean():.2f}%  ROI {100*(MULT*w2.mean()-1):+.2f}%")
