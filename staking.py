"""Quadratic capped stake sizing, $100 unit.

    stake_units = min(pred**2, 3)          bet every game carrying a prediction
    stake_$     = 100 * stake_units

RECONSTRUCTED, not carried over from the original run. The rule was computed
in-session and only its summary statistics were recorded (FINDINGS_LATE.md 3-4);
no committed file held the formula. It was recovered by solving back from those
statistics, which pin it down tightly:

    recorded            implied                                  check
    ---------------------------------------------------------------------
    max stake $300      cap = 3 units, binds at |pred| >= 1.732  cap value
    mean stake $31      E[pred^2] = 0.31                         mean units
    median stake $17    median|pred| = sqrt(0.17) = 0.41         consistent with
                                                                 the observed
                                                                 prediction
                                                                 distribution
    ~967 bets/season    every scored game is staked, not a
                        thresholded subset
    1,377 units risked  4,572 bets x 0.301 mean units            total

`verify_reconstruction()` re-checks those four statistics against whatever panel
is loaded and prints the comparison, so the assumption stays falsifiable.

Note this rule REPLACES the 1.25 threshold rather than composing with it: the
stake function is itself the selector, sizing near zero where the old rule
abstained. Reported alongside the thresholded version, never silently swapped.
"""

import numpy as np
import pandas as pd

UNIT = 100.0          # dollars per unit
CAP_UNITS = 3.0       # maximum 3 units = $300
PRICES = {"-110": 100 / 110, "-105": 100 / 105, "exchange (-102)": 100 / 102}


def stake_units(pred):
    """Quadratic in the predicted move, capped. Zero-safe."""
    return np.minimum(np.square(np.asarray(pred, dtype=float)), CAP_UNITS)


def stake_dollars(pred, unit=UNIT):
    return unit * stake_units(pred)


def settle(df, price="-110", unit=UNIT):
    """Add stake_units, stake_$, won (bool), and $won to a frame of bets.

    Requires: pm (signed prediction), actual_total, open_total.
    Bets are struck and graded at the OPENING total; exact pushes pay nothing.
    """
    d = df.copy()
    d["stake_units"] = stake_units(d["pm"])
    d["stake_$"] = unit * d["stake_units"]

    over = d["actual_total"] > d["open_total"]
    push = d["actual_total"] == d["open_total"]
    d["won"] = np.where(d["pm"] > 0, over, ~over) & ~push
    d["push"] = push

    payout = PRICES[price]
    d["$won"] = np.where(push, 0.0,
                         np.where(d["won"], d["stake_$"] * payout, -d["stake_$"]))
    return d


def summarise(d, label=""):
    live = d[~d["push"]]
    risked = live["stake_$"].sum()
    won = d["$won"].sum()
    return {"set": label, "bets": len(d), "graded": len(live),
            "risked $": round(risked, 2), "$won": round(won, 2),
            "ROI %": round(100 * won / risked, 2) if risked else np.nan,
            "win %": round(100 * live["won"].mean(), 2) if len(live) else np.nan,
            "mean stake $": round(d["stake_$"].mean(), 2),
            "median stake $": round(d["stake_$"].median(), 2),
            "max stake $": round(d["stake_$"].max(), 2)}


def verify_reconstruction(d):
    """Check the four recorded statistics the formula was solved back from."""
    s = d["stake_$"]
    rows = [("cap / max stake $", 300.00, round(s.max(), 2)),
            ("mean stake $", 31.00, round(s.mean(), 2)),
            ("median stake $", 17.00, round(s.median(), 2)),
            ("mean units", 0.301, round(d["stake_units"].mean(), 3))]
    print(f"{'statistic':22} {'recorded':>10} {'observed':>10}   note")
    for name, rec, obs in rows:
        note = "" if abs(obs - rec) <= max(0.15 * abs(rec), 0.02) else "<-- differs"
        print(f"{name:22} {rec:10.2f} {obs:10.2f}   {note}")
    print("\nRecorded values came from the OLD panel (7,335 games, dev 2019-2024);"
          "\nthis panel is larger and starts in 2017, so exact agreement is not"
          "\nexpected. The check is for shape, not equality.")
