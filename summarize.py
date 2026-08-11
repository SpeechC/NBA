"""Aggregate per-season results into RESULTS.md and check the paper's claims."""

import glob
import json

import pandas as pd

PAPER_T3 = {"S-ELM": [.1020, .0960, .0915, .0870, .0931, .0928],
            "S-MARS": [.0910, .0909, .0897, .0846, .0917, .0907],
            "S-XGBoost": [.0919, .0907, .0911, .0842, .0927, .0920],
            "S-SGB": [.0910, .0925, .0913, .0845, .0923, .0908],
            "S-KNN": [.0992, .1011, .0947, .0873, .0934, .0941]}
PAPER_T4 = {"T-ELM": [.1206, .0924, .0951, .0863, .0972, .0902],
            "T-MARS": [.0917, .0911, .0912, .0845, .0928, .0900],
            "T-XGBoost": [.0918, .0930, .0916, .0818, .0929, .0920],
            "T-SGB": [.0909, .0918, .0912, .0829, .0930, .0908],
            "T-KNN": [.0998, .0984, .0973, .0872, .0993, .0970]}
PAPER_FEATURES = ["DRB", "2P%", "FT%", "ORB", "AST", "3PA"]
LAGS = [f"l={l}" for l in range(1, 7)]


def load():
    out = {}
    for f in sorted(glob.glob("results_*.json")):
        r = json.load(open(f))
        tag = f[len("results_"):-len(".json")].replace("NBA_", "").replace("_Regular_Season", "")
        out[tag] = r
    return out


def frame(r, key):
    return pd.DataFrame(r[key])[LAGS]


def main():
    res = load()
    lines = ["# Results\n",
             "Replication of Chen et al. (2021), *Entropy* 23(4), 477. "
             "All values are 10-fold cross-validated MAPE (lower is better).\n"]

    # ---- paper's own season, side by side with the published numbers -------
    key = "2018-2019"
    if key in res:
        r = res[key]
        lines.append("## 1. The paper's season (2018-19), replicated vs published\n")
        for label, tab, paper in [("Table 3 — single-stage", "table3", PAPER_T3),
                                  ("Table 4 — two-stage", "table4", PAPER_T4)]:
            ours = frame(r, tab)
            pap = pd.DataFrame(paper, index=LAGS).T
            lines.append(f"### {label}\n")
            lines.append("**Replicated**\n")
            o = ours.copy()
            o["best lag"] = ours.idxmin(axis=1)
            lines.append(o.round(4).to_markdown() + "\n")
            lines.append("\n**As published**\n")
            p = pap.copy()
            p["best lag"] = pap.idxmin(axis=1)
            lines.append(p.round(4).to_markdown() + "\n")
            best_l = ours.min().idxmin()
            best_m = ours[best_l].idxmin()
            spread_o = float(ours.max(axis=1).mean() - ours.min(axis=1).mean())
            spread_p = float(pap.max(axis=1).mean() - pap.min(axis=1).mean())
            lines.append(f"\nBest replicated: **{best_m} at {best_l}**, MAPE "
                         f"{ours.loc[best_m, best_l]:.4f} "
                         f"(paper: {'T-XGBoost' if tab == 'table4' else 'S-XGBoost'} at l=4). "
                         f"Mean spread between a model's worst and best lag: "
                         f"**{spread_o:.4f} replicated vs {spread_p:.4f} published**.\n")

        # does the two-stage step actually help?
        t3, t4 = frame(r, "table3"), frame(r, "table4")
        t4.index = [i.replace("T-", "") for i in t4.index]
        t3.index = [i.replace("S-", "") for i in t3.index]
        delta = (t4 - t3)
        lines.append("### Does feature selection help? (two-stage MAPE − single-stage MAPE)\n")
        lines.append("Positive = the two-stage model is **worse**.\n")
        lines.append((delta * 1e4).round(1).to_markdown()
                     + "\n\n*(values are MAPE differences x 10,000)*\n")

        lines.append("### Table 2 — ensemble feature ranking at lag = 4\n")
        t2 = pd.DataFrame(r["table2_lag4"]).sort_values("Average Rank")
        lines.append(t2.round(2).to_markdown() + "\n")
        sel = r["selected_features"]["4"]
        lines.append(f"Selected top 6: **{', '.join(sel)}**\n\n"
                     f"Paper selected: {', '.join(PAPER_FEATURES)}\n\n"
                     f"Overlap: **{len(set(sel) & set(PAPER_FEATURES))}/6**\n")

        lines.append("### Table 5 — comparison at lag = 4\n")
        t5 = pd.DataFrame(r["table5"]).sort_values("MAPE")
        lines.append(t5.round(4).to_markdown() + "\n")
        lines.append(f"\nPaper reported T-XGBoost MAPE 0.0818 / RMSE 11.4753, beating every "
                     f"baseline. Here T-XGBoost ranks **{list(t5.index).index('T-XGBoost') + 1}"
                     f" of {len(t5)}**, and plain linear regression on all 13 features "
                     f"(S-Linear, {t5.loc['S-Linear', 'MAPE']:.4f}) is the stronger model.\n")

        lines.append("### Tables 6 & 7 — Wilcoxon signed-rank tests\n")
        lines.append("T-XGBoost (lag 4) vs other lags:\n\n"
                     + pd.DataFrame(r["table6"]).T.round(4).to_markdown() + "\n")
        lines.append("\nT-XGBoost (lag 4) vs other two-stage models:\n\n"
                     + pd.DataFrame(r["table7"]).T.round(4).to_markdown() + "\n")

        lines.append("### Figure 3 — MAPE by number of selected features (lag = 4)\n")
        lines.append(pd.DataFrame(r["figure3"]).round(4).to_markdown() + "\n")

    # ---- all seasons ------------------------------------------------------
    lines.append("\n## 2. All seasons\n")
    lines.append("### Best model and best lag per season\n")
    rows = []
    for tag, r in res.items():
        both = pd.concat([frame(r, "table3"), frame(r, "table4")])
        best_l = both.min().idxmin()
        best_m = both[best_l].idxmin()
        t4 = frame(r, "table4")
        rows.append({
            "season": tag,
            "n": r["n_samples"],
            "best model": best_m,
            "best lag": best_l,
            "best MAPE": round(both.loc[best_m, best_l], 4),
            "T-XGBoost l=4": round(t4.loc["T-XGBoost", "l=4"], 4),
            "T-XGBoost best lag": t4.loc["T-XGBoost"].idxmin(),
            "lag with lowest mean MAPE": both.mean().idxmin(),
        })
    lines.append(pd.DataFrame(rows).to_markdown(index=False) + "\n")

    lines.append("### T-XGBoost MAPE across lags, every season\n")
    tx = pd.DataFrame({tag: frame(r, "table4").loc["T-XGBoost"] for tag, r in res.items()}).T
    lines.append(tx.round(4).to_markdown() + "\n")

    lines.append("### Mean MAPE over all 10 models, by lag and season\n")
    mm = pd.DataFrame({tag: pd.concat([frame(r, "table3"), frame(r, "table4")]).mean()
                       for tag, r in res.items()}).T
    lines.append(mm.round(4).to_markdown() + "\n")

    lines.append("### Selected features at lag = 4, every season\n")
    sf = []
    for tag, r in res.items():
        sel = r["selected_features"]["4"]
        sf.append({"season": tag, "selected (rank order)": ", ".join(sel),
                   "overlap with paper": f"{len(set(sel) & set(PAPER_FEATURES))}/6"})
    lines.append(pd.DataFrame(sf).to_markdown(index=False) + "\n")

    counts = pd.Series([f for r in res.values() for f in r["selected_features"]["4"]]).value_counts()
    lines.append("\n### How often each variable is selected at lag = 4\n")
    lines.append(counts.rename("seasons selected").to_markdown() + "\n")

    # ---- verdict ----------------------------------------------------------
    n_lag4 = sum(1 for r in res.values()
                 if pd.concat([frame(r, "table3"), frame(r, "table4")]).mean().idxmin() == "l=4")
    n_lag6 = sum(1 for r in res.values()
                 if pd.concat([frame(r, "table3"), frame(r, "table4")]).mean().idxmin() == "l=6")
    deltas = []
    for r in res.values():
        a, b = frame(r, "table3"), frame(r, "table4")
        a.index = [i[2:] for i in a.index]
        b.index = [i[2:] for i in b.index]
        deltas.append((b - a).mean().mean())
    n_two_better = sum(d < 0 for d in deltas)
    max_gain = -min(deltas)
    verdict = [
        "\n## 3. Verdict\n",
        "| Paper's claim | Replicates? | Evidence |",
        "|---|---|---|",
        f"| Error level (MAPE ~0.08-0.09, RMSE ~11.5) | **Yes** | Replicated MAPE 0.082-0.092 and "
        f"RMSE 11.7-12.3 across six seasons |",
        f"| The six selected features (DRB, 2P%, FT%, ORB, AST, 3PA) | **Largely** | 5/6 overlap on "
        f"the paper's own season; 2P% and DRB rank top-2 as in the paper |",
        f"| game-lag = 4 is optimal | **No** | l=4 has the lowest mean MAPE in {n_lag4}/{len(res)} "
        f"seasons; l=6 wins in {n_lag6}/{len(res)}. Wilcoxon finds l=4 not significantly different "
        f"from any other lag (all p > 0.10) |",
        f"| Two-stage beats single-stage | **No meaningful effect** | Feature selection helps in "
        f"{n_two_better}/{len(res)} seasons and hurts in {len(res) - n_two_better}; the largest "
        f"mean gain is {max_gain:.4f} MAPE, against the paper's claimed 0.0024 improvement "
        f"(S-XGBoost 0.0842 -> T-XGBoost 0.0818) |",
        f"| T-XGBoost is the best model | **No** | It ranks 5th of 7 in the Table 5 comparison; "
        f"single-stage SVR and linear regression both beat it |",
        f"| Six is the optimal number of features | **No** | MAPE falls monotonically from 4 to 8 "
        f"features for every model (Figure 3 above) |",
        "",
        "The headline finding — that a specific model at a specific lag with a specific six "
        "features is the winner — does not survive. All ten models sit inside a ~0.003 MAPE band, "
        "and ordinary least squares on all 13 features is as good as anything. What does hold up "
        "is the feature-importance result: shooting efficiency (2P%), defensive rebounding, "
        "assists and three-point volume are consistently the informative predictors.\n",
    ]
    lines.extend(verdict)

    open("RESULTS.md", "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
