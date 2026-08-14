"""Efficiency state -> closing-total dispersion. Pre-registered in
PREREG_eff_variance.md, which fixes the feature definition BEFORE any outcome
was examined.

    eff_level_20 = roll20(TEAM_OEFF, home) + roll20(TEAM_OEFF, away), lagged

    discovery  yr <= 2023      validation  yr in {2024, 2025}
    tail cutoff = discovery q80 of |total_error|, frozen
    quintile boundaries fitted on discovery, applied unchanged to validation

Hypothesis: higher eff_level_20 -> higher P(large |error|), monotonically, while
signed error stays unpredictable. Dispersion, not direction.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import optimize, stats

warnings.filterwarnings("ignore")

DISC_MAX = 2023
VALID = [2024, 2025]
WINDOWS = [(20, "eff_level_20"), (10, "eff_level_10"), (30, "eff_level_30")]


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["total"] = n("CLOSING TOTAL_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["oeff_H"], d["oeff_R"] = n("TEAM_OEFF_H"), n("TEAM_OEFF_R")
    d = d.dropna(subset=["total", "actual", "date"])
    d = d[d["total"].between(150, 300)].sort_values("date").reset_index(drop=True)
    d["total_error"] = d["actual"] - d["total"]
    d["abs_total_error"] = d["total_error"].abs()

    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({"gid": d["gid"], "yr": d["yr"],
                                  "date": d["date"], "team": d[f"TEAM_{s}"],
                                  "side": s, "oeff": d[f"oeff_{s}"]}))
    P = pd.concat(rows).sort_values("date")
    g = P.groupby(["yr", "team"])["oeff"]
    for w, name in WINDOWS:
        P[f"r{w}"] = g.transform(
            lambda s: s.shift(1).rolling(w, min_periods=max(6, w // 2)).mean())
    keep = ["gid", "side"] + [f"r{w}" for w, _ in WINDOWS]
    W = P[keep]
    h = W[W["side"] == "H"].drop(columns="side").add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = W[W["side"] == "R"].drop(columns="side").add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    d = d.merge(h, on="gid").merge(a, on="gid")
    for w, name in WINDOWS:
        d[name] = d[f"r{w}_h"] + d[f"r{w}_a"]
    return d


def logit_fit(X, y, alpha=1.0):
    def nll(b):
        p = np.clip(1 / (1 + np.exp(-(X @ b))), 1e-9, 1 - 1e-9)
        return (-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
                + alpha * (b[1:] @ b[1:]) / len(y))
    r = optimize.minimize(nll, np.zeros(X.shape[1]), method="L-BFGS-B")
    return r.x


def run(d, feat, label):
    print("\n" + "=" * 100)
    print(f"{label}   feature = {feat}")
    print("=" * 100)
    s = d.dropna(subset=[feat, "abs_total_error"]).copy()
    disc = s[s["yr"] <= DISC_MAX]
    val = s[s["yr"].isin(VALID)]
    if len(disc) < 500 or len(val) < 300:
        print("  insufficient data")
        return

    # ---- frozen on discovery ------------------------------------------------
    CUT = disc["abs_total_error"].quantile(0.80)
    QB = np.asarray(disc[feat].quantile([0, .2, .4, .6, .8, 1.0]).values,
                    dtype=float).copy()
    QB[0], QB[-1] = -np.inf, np.inf
    mu, sd = disc[feat].mean(), disc[feat].std()
    base = (disc["abs_total_error"] >= CUT).mean()
    print(f"  discovery n={len(disc):,}  validation n={len(val):,}")
    print(f"  FROZEN q80 cutoff = {CUT:.2f} pts   discovery tail rate "
          f"{100*base:.2f}%")
    print(f"  FROZEN quintile edges: "
          + " ".join(f"{v:.2f}" for v in QB[1:-1]))

    for x in (disc, val):
        x["large"] = (x["abs_total_error"] >= CUT).astype(float)
        x["q"] = pd.cut(x[feat], QB, labels=[1, 2, 3, 4, 5])
        x["z"] = (x[feat] - mu) / sd

    print("\n  1 — MONOTONIC BUCKETS (discovery-fitted edges)")
    for lab, x in (("DISCOVERY", disc), ("VALIDATION", val)):
        rows = []
        for q, gg in x.groupby("q", observed=True):
            rows.append({"Q": q, "n": len(gg),
                         "mean |e|": round(gg["abs_total_error"].mean(), 2),
                         "med |e|": round(gg["abs_total_error"].median(), 2),
                         "P(tail)": round(100 * gg["large"].mean(), 2),
                         "mean e": round(gg["total_error"].mean(), 2)})
        t = pd.DataFrame(rows)
        print(f"\n    {lab}")
        print(t.to_string(index=False))
        print(f"      P(tail) monotone: {t['P(tail)'].is_monotonic_increasing}"
              f"   Q5-Q1 {t['P(tail)'].iloc[-1]-t['P(tail)'].iloc[0]:+.2f}pp"
              f"   |e| Q5-Q1 {t['mean |e|'].iloc[-1]-t['mean |e|'].iloc[0]:+.2f}")

    print("\n  2 — WALK-FORWARD TAIL MODEL  logit P(large) = a + b*z")
    yrs = sorted(s["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr = s[s["yr"].isin(yrs[:i])].copy()
        te = s[s["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        tr["large"] = (tr["abs_total_error"] >= CUT).astype(float)
        te["large"] = (te["abs_total_error"] >= CUT).astype(float)
        m_, s_ = tr[feat].mean(), tr[feat].std()
        Xtr = np.column_stack([np.ones(len(tr)), (tr[feat] - m_) / s_])
        b = logit_fit(Xtr, tr["large"].values)
        Xte = np.column_stack([np.ones(len(te)), (te[feat] - m_) / s_])
        te["p"] = 1 / (1 + np.exp(-(Xte @ b)))
        te["p0"] = tr["large"].mean()
        te["beta"] = b[1]
        out.append(te)
    R = pd.concat(out)
    for lab, x in (("all OOS", R), ("VALIDATION only", R[R["yr"].isin(VALID)])):
        y = x["large"].values
        p, p0 = np.clip(x["p"], 1e-9, 1 - 1e-9), np.clip(x["p0"], 1e-9, 1 - 1e-9)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        ll0 = -np.mean(y * np.log(p0) + (1 - y) * np.log(1 - p0))
        br, br0 = np.mean((p - y) ** 2), np.mean((p0 - y) ** 2)
        print(f"    {lab:16} n={len(x):5,}  log loss {ll:.5f} vs {ll0:.5f} "
              f"(gain {ll0-ll:+.5f})   Brier {br:.5f} vs {br0:.5f} "
              f"(gain {br0-br:+.5f})")
    print("    season betas: " + "  ".join(
        f"{y}:{g['beta'].iloc[0]:+.4f}" for y, g in R.groupby("yr")))

    print("\n  3 — VARIANCE REGRESSION (validation)")
    for tgt in ("abs_total_error", "sq"):
        val["sq"] = val["total_error"] ** 2
        yv = val[tgt].values
        r = np.corrcoef(val["z"], yv)[0, 1]
        b = np.polyfit(val["z"], yv, 1)[0]
        t = r * np.sqrt(len(yv) - 2) / np.sqrt(1 - r * r)
        print(f"    {tgt:16} ~ z   slope {b:+.4f}  corr {r:+.4f}  t={t:+.2f}")

    print("\n  4 — FALSIFICATION: signed error must be unpredictable")
    for lab, x in (("discovery", disc), ("VALIDATION", val)):
        r = np.corrcoef(x["z"], x["total_error"])[0, 1]
        b = np.polyfit(x["z"], x["total_error"], 1)[0]
        t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
        print(f"    {lab:12} signed e ~ z   slope {b:+.4f}  corr {r:+.4f}  "
              f"t={t:+.2f}")

    print("\n  5 — VALIDATION REQUIREMENTS")
    vv = R[R["yr"].isin(VALID)]
    pooled_b = np.polyfit(vv["z"] if "z" in vv else
                          (vv[feat] - mu) / sd, vv["large"], 1)[0]
    checks = []
    checks.append(("pooled validation beta > 0", pooled_b > 0, f"{pooled_b:+.5f}"))
    per = {}
    for y_, g in vv.groupby("yr"):
        bb = np.polyfit((g[feat] - mu) / sd, g["large"], 1)[0]
        per[y_] = bb
    checks.append(("both validation seasons positive",
                   all(v > 0 for v in per.values()),
                   " ".join(f"{k}:{v:+.4f}" for k, v in per.items())))
    yv = vv["large"].values
    pv = np.clip(vv["p"], 1e-9, 1 - 1e-9)
    p0v = np.clip(vv["p0"], 1e-9, 1 - 1e-9)
    llg = (-np.mean(yv * np.log(p0v) + (1 - yv) * np.log(1 - p0v))
           + np.mean(yv * np.log(pv) + (1 - yv) * np.log(1 - pv)))
    brg = np.mean((p0v - yv) ** 2) - np.mean((pv - yv) ** 2)
    checks.append(("validation log-loss improvement > 0", llg > 0, f"{llg:+.5f}"))
    checks.append(("validation Brier improvement > 0", brg > 0, f"{brg:+.5f}"))
    tq = val.groupby("q", observed=True)["large"].mean()
    checks.append(("validation quintiles monotone",
                   tq.is_monotonic_increasing,
                   " ".join(f"{100*v:.1f}" for v in tq.values)))
    for name, ok, detail in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {name:38} {detail}")
    print(f"\n    OVERALL: "
          f"{'PASS' if all(c[1] for c in checks) else 'FAIL'}")


def main():
    d = build()
    print(f"{len(d):,} games  seasons {sorted(d['yr'].unique())}")
    run(d, "eff_level_20", "PRIMARY TEST")
    print("\n\n" + "#" * 100)
    print("# ROBUSTNESS — same mechanism, not independent evidence")
    print("#" * 100)
    d["eff_consensus"] = (d["eff_level_10"] + d["eff_level_30"]) / 2
    run(d, "eff_consensus", "ROBUSTNESS: 10+30 game consensus")


if __name__ == "__main__":
    main()
