"""Does CrewShock's value depend on WHEN teams commit their fouls?

Distinct from the retired CrewShock x FoulCommitPropensity test, which asked
whether a generally foul-prone defence receives a larger crew increment (it
does not, delta = +0.027, t = +0.51). This asks the narrower question the NBA
penalty rule makes consequential: four fouls spread evenly through a quarter
leave the opponent unexposed; four in the first six minutes expose the rest.

ONE state, no alternatives:

    BonusMinutes_ig = a + b*FoulRate_ig + eps        fitted on development
    BonusTimingState_it = prior-only rolling mean of eps over 20 games,
                          shift(1), within season
    BonusTimingAvg_t   = (BonusTiming_H + BonusTiming_A) / 2

Higher = this defence puts opponents into the bonus earlier than its overall
foul volume alone would predict.

Continuous interaction only; no thresholds. Development 2017-18..2023-24,
SEALED 2024-25 (the play-by-play ends there).
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import bonus_analysis
import ref_shock as rsk
from dispersion_priced import ols

CTRL = rsk.CTRL
W, MINP = 20, 10        # the frozen team-state horizon used throughout
DEV_MAX, SEALED = 2023, 2024


def build():
    L, m, _ = bonus_analysis.build()
    L = L.dropna(subset=["opp_bonus_min", "foul_rate"]).sort_values("date")

    # residual timing, coefficient fitted on DEVELOPMENT only
    dev = L[L["yr"] <= DEV_MAX]
    b, se, t = ols(dev["opp_bonus_min"].values,
                   np.column_stack([dev["foul_rate"]]))
    print(f"  BonusMinutes ~ FoulRate on development: a {b[0]:+.4f}  "
          f"b {b[1]:+.4f} (t={t[1]:+.1f})   [frozen]")
    L["timing_resid"] = L["opp_bonus_min"].values - (
        b[0] + b[1] * L["foul_rate"].values)

    L["BonusTiming"] = L.groupby(["yr", "team"])["timing_resid"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())

    # game level
    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        BonusTimingAvg=("BonusTiming", "mean"),
        n_side=("BonusTiming", "size"),
        bonus_min=("opp_bonus_min", "sum"),
        bonus_fouls=("nonshoot_in_bonus", "sum"),
        bonus_fta=("bonus_fta", "sum"),
        bonus_ftm=("bonus_ftm", "sum"),
        fouls=("fouls", "sum"),
        CrewShock=("CrewShock", "first"),
        LeagueFoulState=("LeagueFoulState", "first"),
        **{c: (c, "first") for c in CTRL})
    G = G[G["n_side"] == 2]
    mm = m[["gidz", "total", "actual", "e"]].drop_duplicates("gidz")
    G = G.merge(mm, on="gidz", how="inner")
    return G.dropna(subset=["BonusTimingAvg", "CrewShock", "LeagueFoulState",
                            "total", "actual"] + CTRL).reset_index(drop=True)


def main():
    G = build()
    dev = G[G["yr"] <= DEV_MAX]
    mu_c, sd_c = dev["CrewShock"].mean(), dev["CrewShock"].std()
    mu_b, sd_b = dev["BonusTimingAvg"].mean(), dev["BonusTimingAvg"].std()
    G["zC"] = (G["CrewShock"] - mu_c) / sd_c
    G["zB"] = (G["BonusTimingAvg"] - mu_b) / sd_b
    G["zCB"] = G["zC"] * G["zB"]
    dev, seal = G[G["yr"] <= DEV_MAX], G[G["yr"] == SEALED]
    print(f"  games {len(G):,}   development {len(dev):,}   "
          f"SEALED 2024-25 {len(seal):,}")
    print(f"  BonusTimingAvg: mean {G['BonusTimingAvg'].mean():+.4f} "
          f"sd {G['BonusTimingAvg'].std():.4f} minutes")
    print(f"  corr(CrewShock, BonusTimingAvg) = "
          f"{np.corrcoef(G['CrewShock'], G['BonusTimingAvg'])[0,1]:+.4f}")

    def reg(x, y):
        X = np.column_stack([x["zC"], x["zB"], x["zCB"],
                             x["LeagueFoulState"]] + [x[c] for c in CTRL])
        b, se, t = ols(x[y].values, X)
        return b[1], t[1], b[2], t[2], b[3], t[3]

    print("\n" + "=" * 100)
    print("THE MECHANISM TEST — is beta3 > 0 on bonus exposure?")
    print("  Y ~ CrewShock + BonusTiming + CrewShock x BonusTiming + controls")
    print("=" * 100)
    print(f"  {'window':16}{'b1 Crew':>16}{'b2 Timing':>16}"
          f"{'b3 INTERACTION':>20}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        b1, t1, b2, t2, b3, t3 = reg(x, "bonus_min")
        print(f"  {lab:16}{b1:+9.4f}({t1:+5.2f}){b2:+9.4f}({t2:+5.2f})"
              f"{b3:+13.4f}({t3:+5.2f})")

    print("\n" + "=" * 100)
    print("THE SAME INTERACTION THROUGH THE CHAIN (b3 only)")
    print("=" * 100)
    print(f"  {'outcome':26}{'development':>22}{'SEALED 2024-25':>22}")
    for y, nm in (("bonus_min", "bonus MINUTES"),
                  ("bonus_fouls", "bonus fouls"),
                  ("bonus_fta", "bonus FTA"),
                  ("bonus_ftm", "bonus FTM"),
                  ("actual", "ACTUAL total"),
                  ("total", "CLOSING total"),
                  ("e", "closing residual")):
        cells = []
        for x in (dev, seal):
            _, _, _, _, b3, t3 = reg(x, y)
            cells.append(f"{b3:+11.4f} (t={t3:+5.2f})")
        print(f"  {nm:26}{cells[0]:>22}{cells[1]:>22}")

    print("\n" + "=" * 100)
    print("MAIN EFFECTS FOR REFERENCE (b1 CrewShock, b2 Timing)")
    print("=" * 100)
    print(f"  {'outcome':26}{'b1 dev':>15}{'b2 dev':>15}{'b1 seal':>15}"
          f"{'b2 seal':>15}")
    for y, nm in (("bonus_min", "bonus MINUTES"),
                  ("bonus_fta", "bonus FTA"),
                  ("actual", "ACTUAL total"),
                  ("e", "closing residual")):
        b1d, t1d, b2d, t2d, _, _ = reg(dev, y)
        b1s, t1s, b2s, t2s, _, _ = reg(seal, y)
        print(f"  {nm:26}{b1d:+8.3f}({t1d:+5.2f}){b2d:+8.3f}({t2d:+5.2f})"
              f"{b1s:+8.3f}({t1s:+5.2f}){b2s:+8.3f}({t2s:+5.2f})")


if __name__ == "__main__":
    main()
