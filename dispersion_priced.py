"""Is team scoring DISPERSION priced into the closing total?

Section 0 verifies the vendor _STD columns are venue-split averages (that team's
average on the metric while at that venue), which is what they were said to be
and is consistent with them holding levels rather than standard deviations.

Then the pricing question, in the project's usual Stage order.

MOTIVATION. Within-game points-per-possession dispersion was just shown to be a
persistent team characteristic (season-to-season r = +0.67, as persistent as
offensive efficiency itself). A persistent, measurable team property is exactly
the kind of thing a bookmaker's pricing transformation might simplify away,
because a symmetric over/under at -110 is priced off the MEAN and dispersion
only bites through the skew of the total distribution.

FEATURE, frozen before looking at any outcome:

    sigma_i      = PBP_PTS_POSS_SD_i * sqrt(PBP_POSS_i)
                   possession-level scoring SD scaled to a per-game points SD
    disp_state   = sqrt(sigma_home^2 + sigma_away^2)   implied total-points SD
                   built from each team's PRIOR games only: shift(1),
                   rolling 20, min_periods 10, within season
    mu_state     = trailing mean points scored by home + by away, same window

COVERAGE CONSTRAINT. PBP_PTS_POSS_SD exists for develop plus 2024-25 only, so
the validation window is 2024-25 (one season). 2025-26 cannot be used. This is
stated in advance, not discovered afterwards.

TESTS
  S1  does disp_state predict realised dispersion?          (sports side)
  S2  does the BOOK move its total with disp_state, and     (pricing side)
      does the ACTUAL total move with it? Compare the two
      coefficients -- the c_true vs c_market structure used
      for the rematch-pace test.
  S3  does disp_state predict |e|, the error magnitude?
  S4  does disp_state predict the over rate? (skew channel)
  S5  holdout confirmation on 2024-25 of whatever S3/S4 show
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
BE = 110 / 210


def section0():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    print("=" * 96)
    print("0 — WHAT ARE THE _STD COLUMNS?  (venue-split average, or overall?)")
    print("=" * 96)
    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "yr": d["yr"], "date": d["date"], "team": d[f"TEAM_{s}"], "side": s,
            "pts": n(f"PTS_{s}"), "pace": n(f"PACE_{s}"),
            "v_pts": n(f"TEAM_PTS_STD_{s}"), "v_pace": n(f"TEAM_PACE_STD_{s}")}))
    P = pd.concat(rows).sort_values("date")
    g_all = P.groupby(["yr", "team"])
    g_ven = P.groupby(["yr", "team", "side"])
    cands = {
        "all-games STD, prior": lambda gg, c: gg[c].transform(
            lambda s: s.shift(1).expanding(min_periods=3).mean()),
        "VENUE STD, prior only": lambda gg, c: gg[c].transform(
            lambda s: s.shift(1).expanding(min_periods=3).mean()),
        "VENUE STD, incl. this game": lambda gg, c: gg[c].transform(
            lambda s: s.expanding(min_periods=1).mean()),
        "VENUE roll20, prior": lambda gg, c: gg[c].transform(
            lambda s: s.shift(1).rolling(W, min_periods=3).mean()),
    }
    for src, vend, lab in (("pts", "v_pts", "TEAM_PTS_STD"),
                           ("pace", "v_pace", "TEAM_PACE_STD")):
        print(f"\n  {lab}")
        for name, fn in cands.items():
            gg = g_all if name.startswith("all") else g_ven
            P["cand"] = fn(gg, src)
            q = P.dropna(subset=[vend, "cand"])
            r = np.corrcoef(q[vend], q["cand"])[0, 1]
            exact = (q[vend].round(2) == q["cand"].round(2)).mean()
            print(f"    {name:28} corr {r:+.4f}   matches to 2dp "
                  f"{100*exact:5.1f}%   n={len(q):,}")
    print("\n  Highest corr / exact-match rate identifies the construction.")
    print("  'incl. this game' winning would mean the column is NOT knowable")
    print("  pregame and must never be used as a feature.")


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    d["total"], d["open"] = n("CLOSING TOTAL_H"), n("OPENING TOTAL_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["total", "actual", "date"])
    d = d[d["total"].between(150, 300)].copy()
    d["e"] = d["actual"] - d["total"]
    d["abs_e"] = d["e"].abs()

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = [f"{v}_{s}" for v in ("PBP_PTS_POSS_SD", "PBP_POSS") for s in ("H", "R")]
    adv = adv[["gid"] + cols]
    assert not (set(adv.columns) & set(d.columns)) - {"gid"}
    n0 = len(d)
    d = d.merge(adv, on="gid", how="left")
    assert len(d) == n0

    for s in ("H", "R"):
        d[f"sig_{s}"] = d[f"PBP_PTS_POSS_SD_{s}"] * np.sqrt(d[f"PBP_POSS_{s}"])
    d["realised_disp"] = np.sqrt(d["sig_H"] ** 2 + d["sig_R"] ** 2)

    P = pd.concat([
        pd.DataFrame({"gid": d["gid"], "yr": d["yr"], "date": d["date"],
                      "team": d[f"TEAM_{s}"], "side": s,
                      "pts": pd.to_numeric(d[f"PTS_{s}"], errors="coerce"),
                      "sig": d[f"sig_{s}"]})
        for s in ("H", "R")]).sort_values("date").reset_index(drop=True)
    g = P.groupby(["yr", "team"])
    P["m_pts"] = g["pts"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    P["m_var"] = g["sig"].transform(
        lambda s: (s ** 2).shift(1).rolling(W, min_periods=MINP).mean())
    W2 = P[["gid", "side", "m_pts", "m_var"]]
    h = W2[W2["side"] == "H"].drop(columns="side").add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = W2[W2["side"] == "R"].drop(columns="side").add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    assert not (set(h.columns) | set(a.columns)) & set(d.columns) - {"gid"}
    d = d.merge(h, on="gid").merge(a, on="gid")
    d["mu_state"] = d["m_pts_h"] + d["m_pts_a"]
    d["disp_state"] = np.sqrt(d["m_var_h"] + d["m_var_a"])
    return d.dropna(subset=["mu_state", "disp_state"])


def ols(y, X):
    X = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    s2 = r @ r / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return b, se, b / se


def qtable(df, feat, lab):
    df = df.copy()
    df["q"] = df.groupby("yr")[feat].transform(
        lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
    rows = []
    for q, g in df.groupby("q", observed=True):
        ov = (g["e"] > 0).mean()
        rows.append({"Q": int(q) + 1, "n": len(g),
                     feat: round(g[feat].mean(), 2),
                     "total": round(g["total"].mean(), 1),
                     "mean e": round(g["e"].mean(), 3),
                     "|e|": round(g["abs_e"].mean(), 2),
                     "over %": round(100 * ov, 2),
                     "1.96se": round(100 * 1.96 * np.sqrt(ov * (1 - ov) / len(g)), 2)})
    T = pd.DataFrame(rows)
    print(f"\n  {lab}")
    print(T.to_string(index=False))
    print(f"    Q5-Q1  |e| {T['|e|'].iloc[-1]-T['|e|'].iloc[0]:+.2f}   "
          f"over% {T['over %'].iloc[-1]-T['over %'].iloc[0]:+.2f}pp   "
          f"(break-even needs {100*BE:.2f}%)")
    return T


def main():
    section0()
    d = build()
    dev = d[d["yr"] <= 2023]
    hold = d[d["yr"] == 2024]
    print("\n" + "=" * 96)
    print("DISPERSION PRICING")
    print("=" * 96)
    print(f"  {len(d):,} games with the frozen lagged state, "
          f"seasons {sorted(d['yr'].unique())}")
    print(f"  develop (<=2023-24) {len(dev):,}   validation (2024-25) "
          f"{len(hold):,}   [2025-26 has no play-by-play]")
    print(f"  disp_state: mean {d['disp_state'].mean():.2f}  "
          f"sd {d['disp_state'].std():.2f}   "
          f"mu_state: mean {d['mu_state'].mean():.1f}  "
          f"sd {d['mu_state'].std():.1f}")
    print(f"  corr(disp_state, mu_state) = "
          f"{np.corrcoef(d['disp_state'], d['mu_state'])[0,1]:+.4f}")

    print("\n  S1 — does the lagged state predict REALISED game dispersion?")
    s = d.dropna(subset=["realised_disp"])
    for lab, x in (("all", s), ("develop", s[s.yr <= 2023]),
                   ("2024-25", s[s.yr == 2024])):
        r = np.corrcoef(x["disp_state"], x["realised_disp"])[0, 1]
        t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
        print(f"    {lab:10} n={len(x):5,}  corr {r:+.4f}  t={t:+.2f}")

    print("\n  S2 — PRICING: is dispersion in the book's number at all?")
    print("      total  ~ a + b*mu_state + c*disp_state   for the BOOK's close")
    print("      actual ~ a + b*mu_state + c*disp_state   for what HAPPENED")
    for lab, x in (("develop", dev), ("2024-25", hold), ("all", d)):
        X = np.column_stack([x["mu_state"], x["disp_state"]])
        bm, sem, tm = ols(x["total"].values, X)
        bt, set_, tt = ols(x["actual"].values, X)
        diff = bt[2] - bm[2]
        sed = np.sqrt(set_[2] ** 2 + sem[2] ** 2)
        print(f"    {lab:8} n={len(x):5,}   c_market {bm[2]:+7.3f} "
              f"(t={tm[2]:+5.2f})   c_true {bt[2]:+7.3f} (t={tt[2]:+5.2f})"
              f"   gap {diff:+7.3f} (t={diff/sed:+5.2f})")
    print("      b on mu_state, develop: "
          f"{ols(dev['total'].values, np.column_stack([dev['mu_state'], dev['disp_state']]))[0][1]:+.4f}"
          "  [1.0 would be full pass-through of the mean]")

    print("\n  S3/S4 — does dispersion predict error magnitude or direction?")
    qtable(dev, "disp_state", "DEVELOP, within-season dispersion quintiles")
    qtable(hold, "disp_state", "VALIDATION 2024-25, same quintiles")

    print("\n  regression form, dispersion orthogonalised against mu_state")
    for lab, x in (("develop", dev), ("2024-25", hold)):
        b, se, t = ols(x["disp_state"].values,
                       np.column_stack([x["mu_state"]]))
        resid = x["disp_state"].values - (b[0] + b[1] * x["mu_state"].values)
        for tgt in ("abs_e", "e"):
            r = np.corrcoef(resid, x[tgt])[0, 1]
            tt = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
            sl = np.polyfit(resid, x[tgt], 1)[0]
            print(f"    {lab:8} {tgt:6} ~ disp|mu   slope {sl:+.4f}  "
                  f"corr {r:+.4f}  t={tt:+.2f}")


if __name__ == "__main__":
    main()
