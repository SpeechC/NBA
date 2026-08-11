"""How fast does the totals-movement edge decay after the opener posts?

The frozen models produce +0.746 points of CLV measured from the OPENING number
to the close. That figure is only bankable if the opening number is actually
obtainable. If most of the move has happened by the first repost, the edge is
real but unmonetizable.

We have three intermediate quotes per game (LINE MOVEMENT #1/2/3, recovered by
magnitude since spread and total swap columns row by row). They give an entry
ladder: open -> q1 -> q2 -> q3 -> close.

Two questions, and they are different:

  A. WHERE DOES THE VALUE ACCRUE?  Signal computed at the open, held fixed.
     Measure the signed move captured by each stage. This is the decay curve.

  B. CAN THE STRATEGY BE RUN FROM A LATER ENTRY?  Re-anchor the model on the
     later quote (refit with q_k in place of open_total) and grade bets struck
     at q_k against q_k. This answers "if I am always late, do I still have a
     business?" -- which is the practical question, and is NOT the same as A.

A stale signal decaying is expected. B is what decides executability.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats

from models_frozen import SPECS, add_pace_terms, walk_forward
from movement_features import market_features
from prepare_data import CSV, season_label
from symmetric_features import build

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25          # frozen operating threshold


def attach_quotes(G):
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)]
    mf = market_features(raw)
    q = mf[["game_id", "q1_total", "q2_total", "q3_total"]].copy()
    q["gid"] = q["game_id"].astype(str)
    return G.merge(q.drop(columns=["game_id"]), on="gid", how="left")


def bet_stats(side, entry_line, actual, close, label, n_boot=6000):
    """Grade bets struck at `entry_line`."""
    keep = np.isfinite(entry_line) & np.isfinite(actual) & (side != 0)
    side, entry_line, actual, close = (side[keep], entry_line[keep],
                                       actual[keep], close[keep])
    push = actual == entry_line
    side, entry_line, actual, close = (side[~push], entry_line[~push],
                                       actual[~push], close[~push])
    n = len(side)
    if n < 50:
        return None
    over = actual > entry_line
    win = np.where(side > 0, over, ~over).astype(float)
    w = win.mean()
    clv = side * (close - entry_line)          # value still on the table at entry
    bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(n_boot)])
    roi_bs = bs * (100 / 110) - (1 - bs)
    return {"entry": label, "n": n,
            "CLV to close": clv.mean(),
            "beat close %": 100 * (clv > 0).mean(),
            "win %": 100 * w,
            "ROI -110 %": 100 * (w * (100 / 110) - (1 - w)),
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean()}


def main():
    G = add_pace_terms(build())
    G = attach_quotes(G)
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total", "open_total",
                                 "close_total"]).reset_index(drop=True)

    # frozen model, anchored at the open
    G["pred"] = walk_forward(G[feats].values,
                             G["move_total"].values.astype(float),
                             G["date"].values)
    d = G.dropna(subset=["pred"]).copy()
    side = np.where(np.abs(d["pred"]) <= THRESH, 0, np.sign(d["pred"])).astype(int)
    d["side"] = side

    full = d[d["side"] != 0]
    has_q = full.dropna(subset=["q1_total", "q2_total", "q3_total"])
    print(f"bets at |pred| > {THRESH}: {len(full):,}   "
          f"with all three quotes: {len(has_q):,} "
          f"({100 * len(has_q) / max(len(full), 1):.1f}%)\n")

    # ---------- A. where does the value accrue? ----------
    s = has_q["side"].to_numpy()
    op = has_q["open_total"].to_numpy()
    stages = [("quote 1", has_q["q1_total"].to_numpy()),
              ("quote 2", has_q["q2_total"].to_numpy()),
              ("quote 3", has_q["q3_total"].to_numpy()),
              ("close", has_q["close_total"].to_numpy())]
    total_move = (s * (has_q["close_total"].to_numpy() - op)).mean()
    print("=== A. value accrual (signal fixed at the open) ===")
    rows = []
    for lab, line in stages:
        captured = (s * (line - op)).mean()
        rows.append({"by": lab, "CLV captured from open": captured,
                     "% of final CLV": 100 * captured / total_move,
                     "still available": total_move - captured})
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # ---------- B. can it be run from a later entry? ----------
    print("\n=== B. strategy re-anchored at each entry point ===")
    print("(model refit with the entry quote replacing open_total; "
          "bets struck AND graded at that quote)\n")
    out = []
    base = bet_stats(has_q["side"].to_numpy(), has_q["open_total"].to_numpy(),
                     has_q["actual_total"].to_numpy(),
                     has_q["close_total"].to_numpy(), "open (frozen model)")
    if base:
        out.append(base)

    for qcol, lab in (("q1_total", "quote 1"), ("q2_total", "quote 2"),
                      ("q3_total", "quote 3")):
        g = G.dropna(subset=[qcol]).copy()
        g["anchor"] = g[qcol]
        g["move_from_anchor"] = g["close_total"] - g["anchor"]
        f2 = [c if c != "open_total" else "anchor" for c in feats]
        # dis_open is relative to the opener; re-anchor it too
        g["dis_anchor"] = g["dis_open"] + (g["open_total"] - g["anchor"])
        f2 = [c if c != "dis_open" else "dis_anchor" for c in f2]
        g = g.dropna(subset=f2 + ["move_from_anchor"]).reset_index(drop=True)
        g["p2"] = walk_forward(g[f2].values,
                               g["move_from_anchor"].values.astype(float),
                               g["date"].values)
        g = g.dropna(subset=["p2"])
        s2 = np.where(np.abs(g["p2"]) <= THRESH, 0, np.sign(g["p2"])).astype(int)
        r = bet_stats(s2, g["anchor"].to_numpy(), g["actual_total"].to_numpy(),
                      g["close_total"].to_numpy(), lab)
        if r:
            out.append(r)
    print(pd.DataFrame(out).round(3).to_string(index=False))
    pd.DataFrame(out).to_csv("alpha_decay.csv", index=False)


if __name__ == "__main__":
    main()
