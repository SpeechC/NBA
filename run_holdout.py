"""Execute the pre-registered holdout on 2024-25 and 2025-26.

Follows PREREGISTRATION.md exactly:
  * frozen spec A, threshold 1.25, no re-tuning of anything
  * bets struck and graded at the OPENING total, pushes void
  * CLV is the PRIMARY metric; ROI is reported but is not the test
  * both seasons reported separately AND pooled
  * if the two seasons disagree in sign, the verdict is AMBIGUOUS regardless
    of the pooled figure

  PASS       pooled CLV >= +1.2 with 95% CI excluding zero
  AMBIGUOUS  pooled CLV +0.4 to +1.2 with CI excluding zero
  FAIL       pooled CLV <= +0.4, or CI including zero

Backtest anchor at this threshold: CLV +1.844, beat-close 66.6%, win 54.05%,
ROI +3.18%.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25
PASS_CLV, AMBIG_CLV = 1.2, 0.4
ANCHOR = {"CLV": 1.844, "beat_close": 66.6, "win": 54.05, "ROI": 3.18}
HOLDOUT = ("2024-2025", "2025-2026")


def metrics(s, label):
    """s: bets already filtered to |pred| > THRESH and non-push."""
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
    n, w = len(win), win.mean()
    clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
    se = clv.std() / np.sqrt(n)
    wl, wh = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
    bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(8000)])
    roi_bs = bs * (100 / 110) - (1 - bs)
    return {"sample": label, "n": n,
            "CLV": clv.mean(), "CLV lo": clv.mean() - 1.96 * se,
            "CLV hi": clv.mean() + 1.96 * se,
            "beat close %": 100 * (clv > 0).mean(),
            "win %": 100 * w, "win lo": 100 * wl, "win hi": 100 * wh,
            "ROI %": 100 * (w * (100 / 110) - (1 - w)),
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean()}


def main():
    from models_frozen import SPECS, add_pace_terms, walk_forward
    from symmetric_features import build

    G = add_pace_terms(build())
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    G = G.sort_values("date").reset_index(drop=True)
    print(f"panel: {len(G):,} games   {G['date'].min().date()} .. {G['date'].max().date()}")

    G["pm"] = walk_forward(G[feats].values, G["move_total"].values.astype(float),
                           G["date"].values)
    d = G.dropna(subset=["pm"]).copy()
    d["is_holdout"] = d["season"].astype(str).str.contains("|".join(HOLDOUT))
    dev, ho = d[~d["is_holdout"]], d[d["is_holdout"]]
    print(f"development {len(dev):,}   holdout {len(ho):,}\n")
    if len(ho) == 0:
        raise SystemExit("no holdout games found — check season labels")

    def bets(x):
        s = x[(x["pm"].abs() > THRESH) & (x["actual_total"] != x["open_total"])]
        return s

    rows = [metrics(bets(dev), "development 2018-2024 (in sample)")]
    per_season = {}
    for s in HOLDOUT:
        sub = bets(ho[ho["season"].astype(str).str.contains(s)])
        if len(sub) >= 25:
            m = metrics(sub, f"HOLDOUT {s}")
            per_season[s] = m
            rows.append(m)
    pooled = metrics(bets(ho), "HOLDOUT pooled")
    rows.append(pooled)

    res = pd.DataFrame(rows)
    print("=" * 110)
    print("PRE-REGISTERED HOLDOUT — frozen spec A, threshold 1.25, CLV primary")
    print("=" * 110)
    print(res[["sample", "n", "CLV", "CLV lo", "CLV hi", "beat close %",
               "win %", "win lo", "win hi"]].round(3).to_string(index=False))
    print()
    print(res[["sample", "n", "ROI %", "ROI lo", "ROI hi", "P(ROI>0) %"]]
          .round(2).to_string(index=False))

    print("\n" + "=" * 110)
    print("VERDICT")
    print("=" * 110)
    clv, lo = pooled["CLV"], pooled["CLV lo"]
    signs = {k: np.sign(v["CLV"]) for k, v in per_season.items()}
    disagree = len(set(signs.values())) > 1
    if disagree:
        verdict = "AMBIGUOUS (seasons disagree in sign — pre-committed rule)"
    elif clv >= PASS_CLV and lo > 0:
        verdict = "PASS"
    elif clv >= AMBIG_CLV and lo > 0:
        verdict = "AMBIGUOUS"
    else:
        verdict = "FAIL"
    print(f"  pooled CLV      {clv:+.3f}   95% CI [{pooled['CLV lo']:+.3f}, "
          f"{pooled['CLV hi']:+.3f}]   (anchor {ANCHOR['CLV']:+.3f})")
    for k, v in per_season.items():
        print(f"  {k}       {v['CLV']:+.3f}   95% CI [{v['CLV lo']:+.3f}, "
              f"{v['CLV hi']:+.3f}]   n={v['n']}")
    print(f"\n  seasons agree in sign: {'no' if disagree else 'yes'}")
    print(f"\n  >>> {verdict} <<<")
    print(f"\n  thresholds: PASS >= {PASS_CLV}, AMBIGUOUS >= {AMBIG_CLV}, "
          f"both requiring CI above zero")
    print(f"  ROI is reported above but is NOT the test: at n~{pooled['n']} the")
    print(f"  win-rate interval spans break-even by construction.")
    res.to_csv("holdout_results.csv", index=False)
    ho[(ho['pm'].abs() > THRESH)].to_csv("holdout_bets.csv", index=False)


if __name__ == "__main__":
    main()
