"""Is within-game scoring rate mean reverting?

Caveat on what is measurable: the file has points by quarter, not possessions by
quarter. PACE and POSS exist only at game level. So this measures quarter
*scoring*, which is pace x efficiency -- and on this data quarter-1 points
correlate 0.51 with combined offensive efficiency but only 0.23 with game pace,
so it is closer to an efficiency measure than a pace measure. Read the results as
"does scoring rate mean revert", and treat pace specifically as unresolved.

Method. Each quarter's deviation is measured against the *pre-game* closing total
pro-rated by that quarter's league-average share:

    d_i = q_i - closing_total * share_i

Using the pre-game line rather than the game's own realised average matters: if
deviations are taken from the realised mean, quarter i is inside its own
benchmark, which manufactures negative correlation out of nothing. That artefact
is exactly what a naive test of "mean reversion" would pick up.

Interpretation of the slope of d_{later} on d_1:
    > 0   a shared game-level component -- fast games stay fast (persistence)
    = 0   quarter 1 is noise around the pre-game expectation, telling you nothing
    < 0   genuine mean reversion -- the game compensates
"""

import numpy as np
import pandas as pd
from scipy import stats

from prepare_data import CSV, season_label

QS = ["q1", "q2", "q3", "q4"]


def load():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    r = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    for i in [1, 2, 3, 4]:
        r[f"q{i}"] = (pd.to_numeric(r[f"{i}Q_H"], errors="coerce")
                      + pd.to_numeric(r[f"{i}Q_R"], errors="coerce"))
    ot_cols = [f"OT{i}_{s}" for i in range(1, 6) for s in ("H", "R")]
    r["ot_pts"] = sum(pd.to_numeric(r[c], errors="coerce").fillna(0) for c in ot_cols)
    r["reg"] = r[QS].sum(axis=1)
    r["full"] = r["reg"] + r["ot_pts"]
    r["isOT"] = r["OT1_H"].notna()
    r["close_total"] = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    return r.dropna(subset=["close_total"] + QS)


def ols(y, X, names):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    dof = len(y) - X.shape[1]
    s2 = float(res @ res) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t = coef / se
    return pd.DataFrame({"coef": coef, "se": se, "t": t,
                         "p": 2 * (1 - stats.t.cdf(np.abs(t), dof))}, index=names)


def main():
    r = load()
    reg = r[~r["isOT"]].copy()          # clean statistical sample
    L = ["# Is within-game scoring rate mean reverting?\n",
         "**What is measurable.** The file has points by quarter, not possessions by "
         "quarter — `PACE`/`POSS` are game-level only. Quarter-1 points correlate "
         "**0.51** with combined offensive efficiency but only **0.23** with game pace, "
         "so this is closer to a scoring-efficiency test than a pace test. Pace "
         "specifically cannot be resolved with this data.\n",
         f"\nRegulation-only games: {len(reg)} (excludes {r['isOT'].sum()} overtime games, "
         "whose 4th quarter is conditioned on the score being tied).\n"]

    shares = (reg[QS].mean() / reg["close_total"].mean())
    L.append("\n## Quarter shares of the closing total\n")
    tab = pd.DataFrame({"mean pts": reg[QS].mean(), "SD": reg[QS].std(),
                        "share of closing total": shares})
    L.append(tab.round(4).to_markdown() + "\n")
    L.append("\nScoring drifts *down* through the game — Q4 averages 53.8 vs Q1's 56.2 "
             "— so each quarter is benchmarked against its own share, not a flat quarter "
             "of the total.\n")

    for q in QS:
        reg[f"d_{q}"] = reg[q] - reg["close_total"] * shares[q]

    L.append("\n## Correlations between quarter deviations\n")
    C = reg[[f"d_{q}" for q in QS]].corr()
    L.append(C.round(4).to_markdown() + "\n")

    L.append("\n## Does Q1 predict later quarters?\n")
    rows = {}
    for tgt in ["d_q2", "d_q3", "d_q4"]:
        X = np.column_stack([np.ones(len(reg)), reg["d_q1"]])
        rows[f"{tgt} on d_q1"] = ols(reg[tgt].values, X, ["const", "slope"]).loc["slope"]
    rest = reg["d_q2"] + reg["d_q3"] + reg["d_q4"]
    X = np.column_stack([np.ones(len(reg)), reg["d_q1"]])
    rows["rest of game (Q2+Q3+Q4) on d_q1"] = ols(rest.values, X, ["const", "slope"]).loc["slope"]
    h1 = reg["d_q1"] + reg["d_q2"]
    h2 = reg["d_q3"] + reg["d_q4"]
    X2 = np.column_stack([np.ones(len(reg)), h1])
    rows["2nd half on 1st half"] = ols(h2.values, X2, ["const", "slope"]).loc["slope"]
    L.append(pd.DataFrame(rows).T.round(4).to_markdown() + "\n")

    # pooled AR(1) across consecutive quarters
    a = np.concatenate([reg["d_q1"], reg["d_q2"], reg["d_q3"]])
    b = np.concatenate([reg["d_q2"], reg["d_q3"], reg["d_q4"]])
    ar = ols(b, np.column_stack([np.ones(len(a)), a]), ["const", "slope"])
    L.append(f"\nPooled quarter-to-quarter AR(1) slope: **{ar.loc['slope', 'coef']:+.4f}** "
             f"(t = {ar.loc['slope', 't']:.2f}).\n")

    # variance decomposition: shared game component vs quarter noise
    v_between = float(np.mean([np.cov(reg[f"d_{x}"], reg[f"d_{y}"])[0, 1]
                               for x in QS for y in QS if x != y]))
    v_total = float(np.mean(reg[[f"d_{q}" for q in QS]].var()))
    L.append(f"\n## Variance decomposition\n")
    L.append(f"Mean covariance between different quarters (the shared, persistent "
             f"game-level component): **{v_between:.2f}**\n\n"
             f"Mean variance of a single quarter's deviation: **{v_total:.2f}**\n\n"
             f"Share of a quarter's variance that is persistent game-level signal: "
             f"**{100 * v_between / v_total:.1f}%**; the remaining "
             f"**{100 * (1 - v_between / v_total):.1f}%** is quarter-specific noise.\n")

    # the live-betting question, graded the way a book grades: full game incl. OT
    L.append("\n## The live-betting version (all games, overtime included)\n")
    allg = r.copy()
    for q in QS:
        allg[f"d_{q}"] = allg[q] - allg["close_total"] * shares[q]
    remain = allg["full"] - allg["q1"]
    exp_remain = allg["close_total"] * (1 - shares["q1"])
    y = (remain - exp_remain).values
    X = np.column_stack([np.ones(len(allg)), allg["d_q1"]])
    live = ols(y, X, ["const", "slope"])
    L.append("Regressing (actual points after Q1 − pre-game expectation for that "
             "stretch) on the Q1 deviation:\n")
    L.append(live.round(4).to_markdown() + "\n")
    s = live.loc["slope", "coef"]
    L.append(f"\nA game running **+10** over its pro-rated pace after one quarter is "
             f"expected to finish the remaining three quarters "
             f"**{10 * s:+.2f}** points relative to expectation "
             f"(t = {live.loc['slope', 't']:.2f}).\n")

    open("QUARTERS.md", "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
