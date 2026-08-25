"""PREREG_spread_ml_variance.md — run once per window.

Is the book's moneyline internally consistent with its own spread?
  implied sigma from (spread, devigged ML)  vs  realised sd(margin + S)
"""
import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
warnings.filterwarnings("ignore")
from prepare_data import CSV, season_label

BUCKETS = [(0, 3), (3, 6), (6, 9), (9, 12), (12, 99)]


def dec(ml):
    ml = np.asarray(ml, float)
    return np.where(ml > 0, 1 + ml / 100.0, 1 + 100.0 / np.abs(ml))


def devig(oh, oa, how):
    ih, ia = 1 / oh, 1 / oa
    if how == "proportional":
        return ih / (ih + ia)
    if how == "additive":
        ov = ih + ia - 1.0
        return np.clip(ih - ov / 2.0, 1e-6, 1 - 1e-6)
    if how == "power":                       # solve p^k + q^k = 1
        lo, hi = np.full_like(ih, 0.5), np.full_like(ih, 1.5)
        for _ in range(60):
            k = (lo + hi) / 2
            s = ih ** k + ia ** k
            hi = np.where(s > 1, hi, k)
            lo = np.where(s > 1, k, lo)
        k = (lo + hi) / 2
        ph = ih ** k
        return np.clip(ph / (ph + ia ** k), 1e-6, 1 - 1e-6)
    raise ValueError(how)


def load():
    raw = pd.read_csv(CSV, low_memory=False)
    lbl = season_label(raw).astype(str)
    m = lbl.str.contains("Regular Season", na=False)
    d, lbl = raw[m].copy(), lbl[m]
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    g = pd.DataFrame({
        "season": lbl.str.extract(r"(\d{4})")[0].astype(int).values,
        "S": n("CLOSING SPREAD_H"),           # negative when home favoured
        "mlh": n("MONEYLINE_H"), "mla": n("MONEYLINE_R"),
        "margin": n("PTS_H") - n("PTS_R")}).dropna()
    g = g[g.S.abs() > 0].reset_index(drop=True)
    g["oh"], g["oa"] = dec(g.mlh), dec(g.mla)
    g["resid"] = g.margin + g.S               # E[margin] = -S
    g["home_win"] = (g.margin > 0).astype(float)
    g["absS"] = g.S.abs()
    g["overround"] = 1 / g.oh + 1 / g.oa - 1
    return g


def run(g, lab):
    print(f"\n{'='*94}\n{lab}   n={len(g):,}   mean overround {100*g.overround.mean():.2f}%")
    print("="*94)
    rows = []
    for lo, hi in BUCKETS:
        x = g[(g.absS >= lo) & (g.absS < hi)]
        if len(x) < 100:
            continue
        sd_real = x.resid.std()
        r = {"bucket": f"[{lo},{hi})", "n": len(x), "sd_real": sd_real,
             "absS": x.absS.mean()}
        for how in ("proportional", "additive", "power"):
            p = devig(x.oh.values, x.oa.values, how)
            # p_home = Phi(-S/sigma)  ->  sigma = -S / Phi^-1(p)
            z = norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))
            sig = np.where(np.abs(z) > 1e-6, -x.S.values / z, np.nan)
            r[f"sig_{how[:4]}"] = np.nanmedian(sig)
            # win-prob gap: book's p vs p under REALISED sigma
            p_true = norm.cdf(-x.S.values / sd_real)
            r[f"gap_{how[:4]}"] = 100 * np.mean(p - p_true)   # + = fav overpriced
        rows.append(r)
    T = pd.DataFrame(rows)
    print(f"  {'bucket':>9}{'n':>7}{'sd_real':>9}{'sig_prop':>10}{'sig_addi':>10}"
          f"{'sig_powe':>10}{'gap_prop':>10}{'gap_addi':>10}{'gap_powe':>10}")
    for _, r in T.iterrows():
        print(f"  {r.bucket:>9}{int(r.n):>7,}{r.sd_real:>9.2f}{r.sig_prop:>10.2f}"
              f"{r.sig_addi:>10.2f}{r.sig_powe:>10.2f}{r.gap_prop:>+10.2f}"
              f"{r.gap_addi:>+10.2f}{r.gap_powe:>+10.2f}")
    # PRED-1/2: is implied sigma flat while realised rises?
    a = np.polyfit(T.absS, T.sd_real, 1)[0]
    b = np.polyfit(T.absS, T.sig_prop, 1)[0]
    print(f"\n  slope of REALISED sd vs |S|: {a:+.4f} pts per pt   "
          f"IMPLIED sigma slope: {b:+.4f}")
    # continuous test of PRED-2 with a t-stat
    q = pd.qcut(g.absS, 10, duplicates="drop")
    sdq = g.groupby(q).resid.std()
    mq = g.groupby(q).absS.mean()
    cc = np.corrcoef(mq, sdq)[0, 1]
    print(f"  decile check: corr(|S|, sd(resid)) = {cc:+.4f}  "
          f"sd rises {sdq.iloc[0]:.2f} -> {sdq.iloc[-1]:.2f}")
    z2 = (g.resid / g.resid.std()) ** 2
    bb = np.polyfit(g.absS, z2, 1)
    se = np.sqrt(np.sum((z2 - np.polyval(bb, g.absS))**2) / (len(g)-2)
                 / np.sum((g.absS - g.absS.mean())**2))
    print(f"  heteroskedasticity slope on z^2: {bb[0]:+.5f} (t={bb[0]/se:+.2f})")
    # economics: back the underdog ML in the top bucket
    print(f"\n  {'bucket':>9}{'dog n':>7}{'dog win%':>10}{'dog ROI%':>10}"
          f"{'fav ROI%':>10}")
    for lo, hi in BUCKETS:
        x = g[(g.absS >= lo) & (g.absS < hi)]
        if len(x) < 100:
            continue
        dog_home = x.S > 0
        dog_odds = np.where(dog_home, x.oh, x.oa)
        dog_win = np.where(dog_home, x.home_win, 1 - x.home_win)
        roi_d = 100 * (dog_win * dog_odds - 1).mean()
        fav_odds = np.where(dog_home, x.oa, x.oh)
        fav_win = 1 - dog_win
        roi_f = 100 * (fav_win * fav_odds - 1).mean()
        print(f"  {f'[{lo},{hi})':>9}{len(x):>7,}{100*dog_win.mean():>9.2f}%"
              f"{roi_d:>+10.2f}{roi_f:>+10.2f}")
    return T


if __name__ == "__main__":
    g = load()
    print(f"loaded {len(g):,} games with closing spread + both moneylines")
    dev = g[g.season <= 2023]
    hold = g[g.season >= 2024]
    Td = run(dev, "DEVELOPMENT (<= 2023-24)")
    Th = run(hold, "HOLDOUT (2024-25 + 2025-26)")
