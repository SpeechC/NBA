"""Per-bet dollar P&L under quadratic capped staking, $100 unit.

Writes one row per game with stake_$ and $won, for specs A and D, and prints
season-by-season summaries for development and holdout.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
import staking
from models_frozen import OPERATING_THRESHOLD, SPECS, add_pace_terms, walk_forward
from symmetric_features import build


def season_of(d):
    """Label a game by the season it belongs to, from its date."""
    y = d["date"].dt.year
    return np.where(d["date"].dt.month >= 7, y.astype(str) + "-" + (y + 1).astype(str),
                    (y - 1).astype(str) + "-" + y.astype(str))


def main():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)

    for spec in ("A", "D"):
        feats = SPECS[spec]
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
        d = d.sort_values("date").reset_index(drop=True)
        d["pm"] = walk_forward(d[feats].values,
                               d["move_total"].values.astype(float),
                               d["date"].values)
        d = d.dropna(subset=["pm"]).copy()
        d["season_lbl"] = season_of(d)

        b = staking.settle(d, price="-110")
        b = ds.tag(b)

        print("=" * 108)
        print(f"SPEC {spec} — quadratic capped staking, $100 unit, priced at -110")
        print("=" * 108)
        if spec == "A":
            staking.verify_reconstruction(b)
            print()

        rows = [staking.summarise(b[~b["is_holdout"]], "DEVELOPMENT (in sample)")]
        for s, sub in b[b["is_holdout"]].groupby("season_lbl"):
            rows.append(staking.summarise(sub, f"HOLDOUT {s}"))
        rows.append(staking.summarise(b[b["is_holdout"]], "HOLDOUT pooled"))
        print(pd.DataFrame(rows).to_string(index=False))

        print("\n-- development, season by season --")
        srows = [staking.summarise(sub, s)
                 for s, sub in b[~b["is_holdout"]].groupby("season_lbl")]
        print(pd.DataFrame(srows).to_string(index=False))

        print("\n-- same bets at other prices ($won only) --")
        prow = {}
        for price in staking.PRICES:
            pb = staking.settle(d, price=price)
            pb = ds.tag(pb)
            prow[price] = {"DEV $won": round(pb.loc[~pb["is_holdout"], "$won"].sum(), 2),
                           "HOLDOUT $won": round(pb.loc[pb["is_holdout"], "$won"].sum(), 2)}
        print(pd.DataFrame(prow).T.to_string())

        cols = ["game_id", "date", "season_lbl", "is_holdout", "open_total",
                "close_total", "actual_total", "move_total", "pm",
                "stake_units", "stake_$", "won", "push", "$won"]
        out = b[[c for c in cols if c in b.columns]]
        out.to_csv(f"staking_bets_{spec}.csv", index=False)
        print(f"\nwrote staking_bets_{spec}.csv ({len(out):,} rows)\n")


if __name__ == "__main__":
    main()
