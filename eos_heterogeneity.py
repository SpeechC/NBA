"""How much TRUE heterogeneity is there in the late-season uplift?

    Residual_it = a + d*Late_it + b_team*Late_it + b_season*Late_it + e_it

The object of interest is Var(b_team) and Var(b_season). Small after shrinkage
means this is a common regime shift; large but noisy means heterogeneity exists
and our features cannot find it. These are different conclusions and only the
variance component distinguishes them.

Not a feature search and not used to generate filters.

METHOD. statsmodels is unavailable, so the variance component is estimated by
method of moments, which is what a random-slope fit reports:

    delta_g   = mean(resid | late, g) - mean(resid | rest, g)     per group g
    Var_obs   = variance of delta across groups
    Var_samp  = mean over groups of [s2_late/n_late + s2_rest/n_rest]
    Var_true  = Var_obs - Var_samp          (floored at 0)
    lambda    = Var_true / (Var_true + Var_samp)   the shrinkage weight

with a permutation null: shuffle the late flag at GAME level within season
(preserving the pairing of the two teams in a game) and recompute Var_obs. That
gives the distribution of apparent heterogeneity when there is none.

⚠ Each game contributes to BOTH teams, so team-level estimates are correlated.
That is handled in the permutation by shuffling games, not team-games.

⚠ POWER. With ~35 late team-games per team, a single team's uplift has a
standard error near 3 points. Team heterogeneity below roughly that scale is
undetectable here regardless of method, and the script reports the floor.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

WINDOW = 7


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close_total", "date", "actual"])
    d = d[d["close_total"].between(150, 300)]
    d["resid"] = d["actual"] - d["close_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d["late"] = d["days_left"] <= WINDOW
    d = d[d["resid"] != 0].reset_index(drop=True)
    d["g"] = np.arange(len(d))
    return d


def to_long(d):
    a = d[["g", "season", "resid", "late", "TEAM_H"]].rename(
        columns={"TEAM_H": "team"})
    b = d[["g", "season", "resid", "late", "TEAM_R"]].rename(
        columns={"TEAM_R": "team"})
    return pd.concat([a, b], ignore_index=True)


def components(df, key):
    """MoM variance decomposition of the late uplift across groups `key`."""
    rows = []
    for gname, s in df.groupby(key):
        lt, rs = s[s["late"]], s[~s["late"]]
        if len(lt) < 8 or len(rs) < 30:
            continue
        rows.append({"group": gname, "n_late": len(lt), "n_rest": len(rs),
                     "delta": lt["resid"].mean() - rs["resid"].mean(),
                     "samp_var": (lt["resid"].var(ddof=1) / len(lt)
                                  + rs["resid"].var(ddof=1) / len(rs))})
    t = pd.DataFrame(rows)
    var_obs = t["delta"].var(ddof=1)
    var_samp = t["samp_var"].mean()
    var_true = max(0.0, var_obs - var_samp)
    lam = var_true / (var_true + var_samp) if (var_true + var_samp) > 0 else 0.0
    t["shrunk"] = t["delta"].mean() + lam * (t["delta"] - t["delta"].mean())
    return t, var_obs, var_samp, var_true, lam


def perm_null(d, key, n=1500):
    """Shuffle the late flag at GAME level within season."""
    out = []
    for _ in range(n):
        p = d.copy()
        p["late"] = (p.groupby("season")["late"]
                     .transform(lambda s: RNG.permutation(s.values)))
        L = to_long(p) if key == "team" else p
        try:
            _, vo, _, _, _ = components(L, key)
            out.append(vo)
        except Exception:
            continue
    return np.array(out)


def report(name, t, vo, vs, vt, lam, null):
    print(f"\n--- {name} ---")
    print(f"  groups: {len(t)}   mean n_late per group: {t['n_late'].mean():.0f}")
    print(f"  common uplift (mean delta)      {t['delta'].mean():+.3f} pts")
    print(f"  Var_obs  (spread of deltas)     {vo:8.3f}   sd {np.sqrt(vo):.3f}")
    print(f"  Var_samp (sampling noise)       {vs:8.3f}   sd {np.sqrt(vs):.3f}")
    print(f"  Var_true (heterogeneity)        {vt:8.3f}   sd {np.sqrt(vt):.3f}")
    print(f"  shrinkage weight lambda         {lam:8.3f}   "
          f"({'trust group estimates' if lam > 0.5 else 'shrink to the common effect'})")
    if len(null):
        pct = 100 * np.mean(null < vo)
        print(f"  permutation null Var_obs        {null.mean():8.3f} "
              f"± {null.std():.3f}   observed at percentile {pct:.1f}")
    print(f"  detectable floor: heterogeneity sd below ~{np.sqrt(vs):.2f} pts "
          f"is invisible at this sample size")


def main():
    d = load()
    print(f"{len(d):,} games   late {int(d['late'].sum()):,}   "
          f"{d['season'].nunique()} seasons")
    print(f"pooled late uplift: "
          f"{d.loc[d['late'],'resid'].mean() - d.loc[~d['late'],'resid'].mean():+.3f} pts")

    print("\n" + "=" * 96)
    print("TEAM-level random slope on Late")
    print("=" * 96)
    L = to_long(d)
    t, vo, vs, vt, lam = components(L, "team")
    report("teams", t, vo, vs, vt, lam, perm_null(d, "team", 800))
    print("\n  raw vs shrunk team uplifts (extremes):")
    x = t.sort_values("delta")
    print(x.head(4)[["group", "n_late", "delta", "shrunk"]].round(2).to_string(index=False))
    print(x.tail(4)[["group", "n_late", "delta", "shrunk"]].round(2).to_string(index=False))

    print("\n" + "=" * 96)
    print("SEASON-level random slope on Late")
    print("=" * 96)
    ts, vo2, vs2, vt2, lam2 = components(d, "season")
    report("seasons", ts, vo2, vs2, vt2, lam2, perm_null(d, "season", 800))
    print()
    print(ts[["group", "n_late", "delta", "shrunk"]].assign(
        group=lambda z: z["group"].str[4:13]).round(2).to_string(index=False))

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    print(f"  team    Var_true {vt:.3f} (sd {np.sqrt(vt):.2f}), lambda {lam:.3f}")
    print(f"  season  Var_true {vt2:.3f} (sd {np.sqrt(vt2):.2f}), lambda {lam2:.3f}")


if __name__ == "__main__":
    main()
