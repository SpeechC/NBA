"""One falsification of the C2 moneyline pattern. No feature mining.

C2 produced the only clean monotone market-error pattern in the project:

    variance quartile   implied   actual    gap
    Q1                  56.35%    53.44%   -2.91pp
    Q4                  56.82%    59.20%   +2.39pp

DK prices all four groups near 56%, yet realised outcomes rise monotonically --
so it is not the trivial statement that Q4 holds stronger favourites. But team
variance does NOT persist (r = +0.109), so `vstate` cannot be measuring variance
in the evaluation window. It must be proxying for something, or be noise.

THE TEST, and only this:

  1 what does vstate correlate with?  frozen team quality: win pct and point
    differential, both from the SAME 2017-2020 window
  2 outcome ~ logit(p_DK) + vstate + team_quality
  3 residualise vstate against quality AT TEAM LEVEL IN THE FROZEN WINDOW,
    outside the evaluation sample, then rerun the exact quartiles

DECISION, fixed in advance:
  coefficient collapses or ordering disappears -> confounded, close it
  residualised vstate still gives a monotone ~5pp swing -> something real is
  attached; identify it before any ROI

No rest, pace, turnover, conference or age. That would turn a falsification into
a search.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegression

EARLY = [2017, 2018, 2020]
LATE = [2021, 2022, 2023]


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d = d.dropna(subset=["spread", "mlh", "mla", "margin"])
    d["ats"] = d["margin"] + d["spread"]
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p_home"] = ph / (ph + pa)
    d = d[(d["p_home"] > 0.03) & (d["p_home"] < 0.97)].copy()
    d["home_win"] = (d["margin"] > 0).astype(float)
    d["logit"] = np.log(d["p_home"] / (1 - d["p_home"]))

    # frozen team characteristics from EARLY only
    rows = []
    for side, opp in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "yr": d["yr"], "team": d[f"TEAM_{side}"],
            "ats": d["ats"] * (1 if side == "H" else -1),
            "win": (d[f"PTS_{side}"] > d[f"PTS_{opp}"]).astype(float),
            "pd": d[f"PTS_{side}"] - d[f"PTS_{opp}"]}))
    A = pd.concat(rows)
    E = A[A["yr"].isin(EARLY)]
    frozen = E.groupby("team").agg(vstate=("ats", "std"), n=("ats", "size"),
                                   wpct=("win", "mean"),
                                   ptdiff=("pd", "mean")).reset_index()
    frozen = frozen[frozen["n"] >= 100]
    return d, frozen


def quartiles(te, col, lab):
    te = te.copy()
    te["q"] = pd.qcut(te[col], 4, labels=[1, 2, 3, 4])
    rows = []
    for q, s in te.groupby("q", observed=True):
        gap = s["home_win"].mean() - s["p_home"].mean()
        se = np.sqrt(s["home_win"].mean() * (1 - s["home_win"].mean()) / len(s))
        rows.append({"Q": q, "n": len(s), "mean state": round(s[col].mean(), 3),
                     "implied %": round(100 * s["p_home"].mean(), 2),
                     "actual %": round(100 * s["home_win"].mean(), 2),
                     "gap pp": round(100 * gap, 2),
                     "se pp": round(100 * se, 2)})
    t = pd.DataFrame(rows)
    print(f"\n  {lab}")
    print(t.to_string(index=False))
    mono = t["gap pp"].is_monotonic_increasing
    swing = t["gap pp"].iloc[-1] - t["gap pp"].iloc[0]
    print(f"    monotone: {mono}   Q4-Q1 swing {swing:+.2f}pp")
    return mono, swing


def main():
    d, frozen = build()
    print(f"frozen team characteristics from {EARLY}: {len(frozen)} teams")

    print("\n" + "=" * 92)
    print("1 — WHAT IS vstate PROXYING FOR?")
    print("=" * 92)
    for c in ("wpct", "ptdiff"):
        r = np.corrcoef(frozen["vstate"], frozen[c])[0, 1]
        t = r * np.sqrt(len(frozen) - 2) / np.sqrt(1 - r * r)
        print(f"  corr(vstate, {c:7}) = {r:+.3f}   t={t:+.2f}")

    # residualise vstate against quality, at team level, in the frozen window
    X = np.column_stack([np.ones(len(frozen)), frozen["wpct"], frozen["ptdiff"]])
    b, *_ = np.linalg.lstsq(X, frozen["vstate"].values, rcond=None)
    frozen["vperp"] = frozen["vstate"] - X @ b
    r2 = 1 - (frozen["vperp"] ** 2).sum() / ((frozen["vstate"]
                                              - frozen["vstate"].mean()) ** 2).sum()
    print(f"  vstate ~ wpct + ptdiff : R^2 = {r2:.3f}  "
          f"-> {100*r2:.0f}% of vstate is team quality")

    te = d[d["yr"].isin(LATE)].copy()
    for suf, col in (("_h", "TEAM_H"), ("_a", "TEAM_R")):
        te = te.merge(frozen[["team", "vstate", "vperp", "wpct", "ptdiff"]]
                      .add_suffix(suf).rename(columns={f"team{suf}": col}),
                      on=col, how="inner")
    for c in ("vstate", "vperp", "wpct", "ptdiff"):
        te[c] = (te[f"{c}_h"] + te[f"{c}_a"]) / 2
        te[c] = te[c] - te[c].mean()
    print(f"  evaluation window {LATE}: {len(te):,} games")

    print("\n" + "=" * 92)
    print("2 — outcome ~ logit(p_DK) + vstate + team quality")
    print("=" * 92)
    y = te["home_win"].values
    specs = [("p_DK only", ["logit"]),
             ("+ vstate", ["logit", "vstate"]),
             ("+ vstate + quality", ["logit", "vstate", "wpct", "ptdiff"]),
             ("+ vperp (residualised)", ["logit", "vperp"])]
    for lab, cols in specs:
        X = te[cols].values
        m = LogisticRegression(max_iter=1000).fit(X, y)
        p = m.predict_proba(X)[:, 1]
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        co = "  ".join(f"{c}={v:+.4f}" for c, v in zip(cols, m.coef_[0])
                       if c != "logit")
        print(f"  {lab:26} log-loss {ll:.5f}   {co}")

    print("\n" + "=" * 92)
    print("3 — THE DECISIVE QUARTILES")
    print("=" * 92)
    m1, s1 = quartiles(te, "vstate", "original vstate (reproduction)")
    m2, s2 = quartiles(te, "vperp", "vstate RESIDUALISED against team quality")
    m3, s3 = quartiles(te, "ptdiff", "team quality alone, for reference")

    print("\n" + "=" * 92)
    print("VERDICT")
    print("=" * 92)
    print(f"  original vstate : monotone={m1}  swing {s1:+.2f}pp")
    print(f"  residualised    : monotone={m2}  swing {s2:+.2f}pp")
    if (not m2) or abs(s2) < 0.5 * abs(s1):
        print("\n  -> CONFOUNDED. The pattern rides on team quality, not on the")
        print("     old variance estimate. Close it.")
    else:
        print("\n  -> SURVIVES. Something real is attached to the frozen vstate")
        print("     that is not team quality. Identify it before any ROI.")


if __name__ == "__main__":
    main()
