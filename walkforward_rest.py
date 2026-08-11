"""Add rest and travel to the matchup model; grade against the closing spread.

Builds on walkforward_pace.py. Each team-game gets its own rest/travel context
plus the opponent's, so the model can see a rested home team hosting a team on
the second night of a back-to-back at the end of a road trip.
"""

import numpy as np
import pandas as pd

from prepare_data import CSV, VARS, season_label, _side
from rest_travel import FEATURES as RT, add_rest_travel
from walkforward import calibrate, to_games
from walkforward_pace import ALLV, EXT, build_panel_ext, evaluate, walk_forward


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()

    panel, market = build_panel_ext()
    rt = add_rest_travel(panel[["game_id", "season", "team", "date", "home"]], raw)
    rt = rt[["game_id", "team"] + RT + ["itinerary_gap"]]
    panel = panel.merge(rt, on=["game_id", "team"], how="left")

    # opponent's rest/travel, joined through the other row of the same game
    opp = panel[["game_id", "home"] + RT].copy()
    opp["home"] = 1 - opp["home"]
    opp = opp.rename(columns={c: c + "_opp" for c in RT})
    panel = panel.merge(opp, on=["game_id", "home"], how="inner")
    return panel, market


def main():
    panel, market = build()
    print(f"team-games: {len(panel)}", flush=True)
    print(f"itinerary holes (travel unknown): {panel['itinerary_gap'].mean():.1%}", flush=True)
    print(panel[RT].describe().round(2).to_string(), flush=True)

    base = [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
    variants = {
        "matchup": base,
        "matchup+rest": base + ["rest_days", "is_b2b", "is_3in4", "is_4in5",
                                "rest_days_opp", "is_b2b_opp", "is_3in4_opp", "is_4in5_opp"],
        "matchup+travel": base + ["travel_km", "tz_shift", "road_trip_game",
                                  "travel_km_opp", "tz_shift_opp", "road_trip_game_opp"],
        "matchup+rest+travel": base + RT + [c + "_opp" for c in RT],
    }

    rows = {}
    for name, cols in variants.items():
        scores = walk_forward(panel, cols)
        g = calibrate(to_games(scores, market))
        rows[name] = evaluate(g)
        print(f"{name:22} RMSE {rows[name]['margin RMSE']:.3f}  "
              f"t {rows[name]['incr t']:+.2f}  ROI {rows[name]['ROI %']:+.2f}%", flush=True)
        if name == "matchup+rest+travel":
            g.to_csv("rest_travel_games.csv", index=False)

    comp = pd.DataFrame(rows).T
    out = ["# Rest and travel added to the matchup model\n",
           "Rest is parsed from the file's `TEAM REST DAYS` label (accurate: computed "
           "before overtime games were stripped). Travel is computed from the sequence of "
           "hosts, with arena coordinates as external reference data. Where the itinerary "
           "has a hole from a removed overtime game, travel is set to NaN and XGBoost "
           "learns a default direction.\n",
           "## Variant comparison\n", comp.round(3).to_markdown() + "\n",
           "\nClosing-line margin RMSE on these games is 13.68; break-even at -110 is "
           "52.38%. `incr t` is the t-statistic on the model's coefficient when actual "
           "margin is regressed on the closing line plus the model.\n"]
    open("BETTING_REST.md", "w").write("\n".join(out))
    print("\n" + comp.round(3).to_string())


if __name__ == "__main__":
    main()
