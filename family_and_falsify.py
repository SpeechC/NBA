"""Two final NBA tests, then stop testing this sample.

PART 1 — FAMILY-LEVEL MAX PERMUTATION.
  The pre-ASB window survived its own matched-window null at p=0.0006, but it was
  selected as the best of seven pre-specified regimes. The family-wise question
  is: how often does the LARGEST over-rate among seven matched pseudo-regimes
  reach 60.47%? Each regime gets its own structure-preserving draw:

      calendar regimes  a contiguous window of the same width, drawn from the
                        same part of the calendar (4 weeks either side)
      playoff regimes   a same-size random subset of playoff games
      Cup regimes       a same-size random subset of contemporaneous Nov-Dec
                        regular-season games

  The max across the seven is recorded per draw. That distribution is the correct
  reference for a result found by scanning seven states.

PART 2 — THE FALSIFICATION.
  Everything so far is confounded with the calendar: February and April could
  simply be unusual. This separates the two by finding ORDINARY games that
  precede an unusually long rest for one or both teams, excluding the All-Star
  break and the end of the season entirely.

      Gap_it = date of team i's NEXT game - date of this game

  The threshold is pre-specified from the empirical gap distribution, which is
  printed BEFORE any outcome is examined. If a January game before five days off
  shows the same directional effect, the mechanism is behavioural rather than
  calendrical. If it shows nothing, the calendar windows are just calendar.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

BE = 110 / 210
GAP_THRESHOLD = 4      # pre-specified below, from the gap distribution


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw.copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "date", "actual"])
    d = d[d["close"].between(150, 300)].copy()
    d["r"] = d["actual"] - d["close"]
    d["kind"] = np.select(
        [d["lbl"].str.contains("Regular"), d["lbl"].str.contains("Playoffs"),
         d["lbl"].str.contains("In-Season")], ["REG", "PLAYOFF", "CUP"], "other")
    reg = d[d["kind"] == "REG"]
    breaks = {}
    for lbl, g in reg.groupby("lbl"):
        dts = np.sort(g["date"].dropna().unique())
        gaps = np.diff(dts).astype("timedelta64[D]").astype(int)
        breaks[lbl] = pd.Timestamp(dts[int(np.argmax(gaps))])
    d["break_day"] = d["lbl"].map(breaks)
    d["days_to_break"] = (d["break_day"] - d["date"]).dt.days
    d["days_left"] = (d.groupby("lbl")["date"].transform("max")
                      - d["date"]).dt.days
    return d[d["r"] != 0].reset_index(drop=True), breaks


def over(s):
    return (s["r"] > 0).mean() if len(s) else np.nan


def part1(d, breaks):
    reg = d[d["kind"] == "REG"]
    po = d[d["kind"] == "PLAYOFF"]
    novdec = reg[reg["date"].dt.month.isin([11, 12])]

    obs = {"pre_asb": (reg[reg["days_to_break"].between(0, 2)], 3, "pre"),
           "post_asb": (reg[reg["days_to_break"].between(-3, -1)], 3, "post"),
           "first7": (reg[reg["date"] <= reg.groupby("lbl")["date"]
                          .transform("min") + pd.Timedelta(days=6)], 7, "first"),
           "playoff_g1": (None, None, "po"), "playoff_elim": (None, None, "po"),
           "cup_all": (d[d["kind"] == "CUP"], None, "cup"),
           "cup_final": (None, None, "cup")}
    sizes = {"pre_asb": 172, "post_asb": 188, "first7": 396,
             "playoff_g1": 120, "playoff_elim": 182,
             "cup_all": 187, "cup_final": 61}
    observed = {"pre_asb": 0.6047, "post_asb": 0.4780, "first7": 0.5203,
                "playoff_g1": 0.4359, "playoff_elim": 0.5110,
                "cup_all": 0.4813, "cup_final": 0.4262}

    donors = {}
    for lbl, bd in breaks.items():
        r = reg[reg["lbl"] == lbl]
        donors[("pre", lbl)] = np.sort(
            r[(r["date"] < bd - pd.Timedelta(days=2))
              & (r["date"] >= bd - pd.Timedelta(days=28))]["date"].unique())
        donors[("post", lbl)] = np.sort(
            r[(r["date"] > bd + pd.Timedelta(days=8))
              & (r["date"] <= bd + pd.Timedelta(days=35))]["date"].unique())
        first = r["date"].min()
        donors[("first", lbl)] = np.sort(
            r[(r["date"] > first + pd.Timedelta(days=6))
              & (r["date"] <= first + pd.Timedelta(days=34))]["date"].unique())

    print("=" * 96)
    print("PART 1 — family-level max permutation across 7 pre-specified regimes")
    print("=" * 96)
    print("  observed over rates: " + "  ".join(
        f"{k}={100*v:.1f}" for k, v in observed.items()))
    obs_max = max(observed.values())
    print(f"  observed MAX = {100*obs_max:.2f}%  ({max(observed, key=observed.get)})")

    maxes = []
    for _ in range(4000):
        draws = []
        for key, width in (("pre", 3), ("post", 3), ("first", 7)):
            picks = []
            for lbl in breaks:
                dts = donors.get((key, lbl), np.array([]))
                if len(dts) < width + 1:
                    continue
                i = RNG.integers(0, len(dts) - width + 1)
                picks.append(reg[(reg["lbl"] == lbl)
                                 & (reg["date"].isin(dts[i:i + width]))])
            if picks:
                draws.append(over(pd.concat(picks)))
        for n in (sizes["playoff_g1"], sizes["playoff_elim"]):
            if len(po) >= n:
                draws.append(over(po.sample(n, random_state=int(RNG.integers(1e9)))))
        for n in (sizes["cup_all"], sizes["cup_final"]):
            if len(novdec) >= n:
                draws.append(over(novdec.sample(n, random_state=int(RNG.integers(1e9)))))
        if draws:
            maxes.append(np.nanmax(draws))
    maxes = np.array(maxes)
    print(f"\n  family max under the null: {100*maxes.mean():.2f}% "
          f"± {100*maxes.std():.2f}   95th pct {100*np.percentile(maxes,95):.2f}%")
    print(f"  p(family max >= {100*obs_max:.2f}%) = "
          f"{np.mean(maxes >= obs_max):.4f}")


def part2(d):
    reg = d[d["kind"] == "REG"].copy()
    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({
            "idx": reg.index, "lbl": reg["lbl"], "date": reg["date"],
            "team": reg[f"TEAM_{side}"]}))
    L = pd.concat(rows).sort_values(["lbl", "team", "date"])
    L["next_date"] = L.groupby(["lbl", "team"])["date"].shift(-1)
    L["gap"] = (L["next_date"] - L["date"]).dt.days

    print("\n" + "=" * 96)
    print("PART 2 — falsification: ordinary games before an unusually long rest")
    print("=" * 96)
    print("  empirical distribution of a team's NEXT-GAME gap (days), all "
          "regular-season games:")
    vc = L["gap"].value_counts().sort_index()
    tot = vc.sum()
    for g in range(1, 9):
        if g in vc.index:
            print(f"    {g} day{'s' if g>1 else ' '}: {vc[g]:6,}  "
                  f"({100*vc[g]/tot:5.2f}%)   cum {100*vc[vc.index<=g].sum()/tot:5.1f}%")
    print(f"    9+      : {int(vc[vc.index>=9].sum()):6,}")
    print(f"\n  PRE-SPECIFIED THRESHOLD: gap >= {GAP_THRESHOLD} days "
          f"({100*vc[vc.index>=GAP_THRESHOLD].sum()/tot:.1f}% of team-games)")

    L["long"] = L["gap"] >= GAP_THRESHOLD
    cnt = L.groupby("idx")["long"].sum().rename("n_long")
    reg = reg.join(cnt)
    # exclude the confounded windows entirely
    ok = reg[(reg["days_to_break"].abs() > 5) & (reg["days_left"] > 10)
             & reg["n_long"].notna()]
    print(f"\n  after excluding the All-Star window (+/-5d) and the final 10 "
          f"days: {len(ok):,} games")

    out = []
    for n, s in ok.groupby("n_long"):
        if len(s) < 40:
            continue
        ov = over(s)
        se = np.sqrt(ov * (1 - ov) / len(s))
        t, p = stats.ttest_1samp(s["r"], 0)
        out.append({"teams facing a long rest": int(n), "n": len(s),
                    "resid": round(s["r"].mean(), 3),
                    "median": round(s["r"].median(), 2),
                    "over %": round(100 * ov, 2),
                    "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
                    "ROI110": round(100 * (ov * (100/110) - (1-ov)), 2),
                    "p": round(p, 4)})
    print()
    print(pd.DataFrame(out).to_string(index=False))

    a = ok[ok["n_long"] >= 1]["r"]
    b = ok[ok["n_long"] == 0]["r"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    print(f"\n  any long rest vs none: {a.mean():+.3f} vs {b.mean():+.3f}  "
          f"diff {a.mean()-b.mean():+.3f}  t={t:+.2f}  p={p:.4f}")
    print(f"  reference: pre-ASB +2.820, final week +2.973 over a ~+0.31 base")


def main():
    d, breaks = load()
    part1(d, breaks)
    part2(d)


if __name__ == "__main__":
    main()
