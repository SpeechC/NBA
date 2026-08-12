"""Can we isolate the BEST overs inside the end-of-season window?

The instinct is right -- 67 bets a season at +3.5pp is thin, and if a subset ran
at +8pp the economics would change. The question is whether we can identify that
subset, or only appear to.

The binding constraint is resolution. With ~537 games in the last-7-day window,
splitting into subgroups leaves 100-300 each. The standard error on a subgroup
rate is then 3-5pp, and the standard error on the DIFFERENCE between two
subgroups is ~1.4x that. So a filter that genuinely adds 4pp is invisible, while
noise routinely produces apparent gaps of 8-10pp. Every filter will look like it
works on the subgroup that happened to win.

Filters here are derived from the stated MECHANISM (teams stop competing), not
searched for. That is the only defensible way to pick them, and it still does not
solve the resolution problem -- it only avoids making it worse.

Reported for each: n, rate, CI width, and season-by-season consistency, which is
the only thing that separates a real filter from a lucky split.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

from end_of_season import load

BE = 110 / 210


def stat(s, lab):
    if len(s) < 40:
        return None
    ov = (s["resid"] > 0).mean()
    se = np.sqrt(ov * (1 - ov) / len(s))
    seasons = s.groupby("season")["resid"].apply(lambda x: (x > 0).mean())
    return {"filter": lab, "n": len(s), "over %": round(100 * ov, 2),
            "±1.96se": round(100 * 1.96 * se, 2),
            "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
            "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2),
            "szns > BE": f"{int((seasons > BE).sum())}/{len(seasons)}",
            "$/season": round(100 * (ov * (100 / 110) - (1 - ov)) * len(s) / 8)}


def main():
    d = load()
    for W in (7, 10):
        w = d[d["days_left"] <= W].dropna(subset=["wpct_h", "wpct_a"]).copy()
        w["worst"] = w[["wpct_h", "wpct_a"]].min(axis=1)
        w["best"] = w[["wpct_h", "wpct_a"]].max(axis=1)
        w["fighting"] = ((w["wpct_h"].between(0.40, 0.60)) |
                         (w["wpct_a"].between(0.40, 0.60)))

        rows = [stat(w, "ALL games in window")]
        for lab, m in (
            ("contains a tanker (<.333)", w["worst"] < 0.333),
            ("both below .450", w["best"] < 0.450),
            ("neither team fighting", ~w["fighting"]),
            ("contains a lock (>.650)", w["best"] > 0.650),
            ("high total (close > median)", w["close_total"] > w["close_total"].median()),
            ("low total (close <= median)", w["close_total"] <= w["close_total"].median()),
            ("line moved UP", w["move"] > 0),
            ("line moved DOWN", w["move"] < 0),
        ):
            r = stat(w[m], lab)
            if r:
                rows.append(r)
        t = pd.DataFrame([r for r in rows if r])
        print("=" * 116)
        print(f"LAST {W} DAYS — mechanism-derived filters (n={len(w):,})")
        print("=" * 116)
        print(t.to_string(index=False))

        # what does a RANDOM split of the same size produce?
        base = w["resid"].values > 0
        print(f"\n  Null check — random subsets of the same sizes:")
        for frac in (0.5, 0.3):
            k = int(len(w) * frac)
            sims = np.array([RNG.choice(base, k, replace=False).mean()
                             for _ in range(4000)])
            print(f"    random {int(100*frac)}% subset (n={k}): "
                  f"5th-95th pct = [{100*np.percentile(sims,5):.1f}, "
                  f"{100*np.percentile(sims,95):.1f}]  "
                  f"-> best of 8 such filters averages "
                  f"{100*np.mean([np.max(RNG.choice(sims,8)) for _ in range(2000)]):.1f}%")
        print()


if __name__ == "__main__":
    main()
