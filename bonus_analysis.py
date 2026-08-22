"""Two questions about bonus (penalty) entry.

1. TEAM PERSISTENCE. Are there teams that put opponents into the bonus early
   or late with consistency? Tested raw and residualised on the team's own
   foul rate, since more fouls mechanically means earlier entry -- the
   interesting claim is timing beyond volume.

2. CREWSHOCK -> BONUS ACCELERATION. Does a whistle-heavy crew move bonus entry
   earlier, and does that convert later non-shooting fouls into free throws?
   The rules-based mechanism: before the bonus a non-shooting foul yields 0
   FTA; after it yields 2. So early whistles raise the marginal value of later
   whistles.

Diagnostic only. Nothing frozen is modified.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import bonus_extract
import ref_shock as rsk
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

CTRL = rsk.CTRL
DEV_MAX = 2023


def build():
    a = bonus_extract.build()
    a["gid"] = a["gid"].astype(str).str.zfill(10)
    # game x team: this team's fouling put the OPPONENT in the bonus
    g = a.groupby(["gid", "team"], as_index=False).agg(
        fouls=("fouls", "sum"),
        q_reached=("reached_bonus", "sum"),
        opp_bonus_min=("opp_bonus_min", "sum"),
        nonshoot_in_bonus=("nonshoot_in_bonus", "sum"),
        bonus_fta=("bonus_fta", "sum"),
        bonus_ftm=("bonus_ftm", "sum"),
        fta=("fta", "sum"),
        pres_fta=("pres_fta", "sum"), pres_ftm=("pres_ftm", "sum"))
    # per-quarter entry timing, conditional on reaching
    for q in (1, 2, 3, 4):
        s = a[(a["q"] == q) & a["reached_bonus"]][
            ["gid", "team", "entry_sec_left"]].rename(
            columns={"entry_sec_left": f"entry_q{q}"})
        g = g.merge(s, on=["gid", "team"], how="left")

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["poss_g"] = (pd.to_numeric(adv["PBP_POSS_H"], errors="coerce")
                     + pd.to_numeric(adv["PBP_POSS_R"], errors="coerce"))
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R", "poss_g"]],
                on="gid", how="left")
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")

    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "gid": m["gid"], "yr": m["yr"],
            "date": m["date"], "team": m[f"ADV_TEAM_ABBR_{s}"],
            "CrewShock": m["CrewShock"], "LeagueFoulState": m["LeagueFoulState"],
            "poss_g": m["poss_g"], **{c: m[c] for c in CTRL}}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(g, left_on=["gidz", "team"], right_on=["gid", "team"],
                how="inner", suffixes=("", "_g")).drop(columns=["gid_g"])
    L["foul_rate"] = 200.0 * L["fouls"] / L["poss_g"]
    return L, m, g


def main():
    L, m, g = build()
    print(f"  game-team rows {len(L):,}   games {L['gidz'].nunique():,}")
    print(f"  per game-team: fouls {L['fouls'].mean():.2f}   "
          f"quarters reaching bonus {L['q_reached'].mean():.2f}   "
          f"opponent bonus minutes {L['opp_bonus_min'].mean():.2f}")
    print(f"  bonus non-shooting fouls {L['nonshoot_in_bonus'].mean():.2f}   "
          f"bonus FTA {L['bonus_fta'].mean():.2f}   "
          f"bonus FTM {L['bonus_ftm'].mean():.2f}")

    print("\n" + "=" * 96)
    print("1 — DO TEAMS PUT OPPONENTS IN THE BONUS EARLY/LATE CONSISTENTLY?")
    print("=" * 96)
    d = L[L["yr"] <= DEV_MAX].dropna(
        subset=["opp_bonus_min", "foul_rate"]).copy()
    # residualise on the team's own foul rate: timing beyond volume
    X = np.column_stack([d["foul_rate"]])
    b, se, t = ols(d["opp_bonus_min"].values, X)
    d["bonus_resid"] = d["opp_bonus_min"].values - (
        b[0] + b[1] * d["foul_rate"].values)
    print(f"  opponent bonus minutes ~ own foul rate: b {b[1]:+.4f} "
          f"(t={t[1]:+.1f}), R^2 "
          f"{np.corrcoef(d['foul_rate'], d['opp_bonus_min'])[0,1]**2:.4f}")
    print("  -> most of bonus exposure is simply foul VOLUME; the residual is"
          " timing")

    d = d.sort_values("date").copy()
    d["gnum"] = d.groupby(["yr", "team"]).cumcount()
    for col, lab in (("opp_bonus_min", "raw opponent bonus minutes"),
                     ("bonus_resid", "residual (timing beyond volume)"),
                     ("foul_rate", "own foul rate [reference]")):
        A = d[d["gnum"] % 2 == 0].groupby(["yr", "team"])[col].agg(
            ["mean", "size", "std"])
        B = d[d["gnum"] % 2 == 1].groupby(["yr", "team"])[col].agg(
            ["mean", "size"])
        j = A.join(B, lsuffix="_a", rsuffix="_b").dropna()
        j = j[(j["size_a"] >= 20) & (j["size_b"] >= 20)]
        r = np.corrcoef(j["mean_a"], j["mean_b"])[0, 1]
        tt = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
        # noise floor: expected split-half r given sampling error
        v_obs = np.var(j["mean_a"], ddof=1)
        v_noise = np.mean(j["std"] ** 2) / j["size_a"].mean()
        rel = max(v_obs - v_noise, 0) / v_obs if v_obs > 0 else 0
        print(f"\n  {lab}")
        print(f"    within-season split-half corr {r:+.4f} (t={tt:+.2f}, "
              f"n={len(j)} team-seasons)")
        print(f"    observed var {v_obs:.4f}  sampling-noise var {v_noise:.4f}"
              f"  -> signal share {rel:.3f}")
        ts = d.groupby(["yr", "team"])[col].agg(["mean", "size"]).reset_index()
        ts = ts[ts["size"] >= 40]
        ts["nxt"] = ts["yr"] + 1
        jj = ts.merge(ts, left_on=["team", "nxt"], right_on=["team", "yr"],
                      suffixes=("_t", "_n"))
        rs = np.corrcoef(jj["mean_t"], jj["mean_n"])[0, 1]
        print(f"    season-to-season corr {rs:+.4f} (n={len(jj)} pairs)")

    print("\n  most and least extreme teams on the timing residual "
          "(development, shrunk toward zero)")
    per = d.groupby("team")["bonus_resid"].agg(["mean", "size", "std"])
    per = per[per["size"] >= 300]
    se_i = per["std"] / np.sqrt(per["size"])
    tau2 = max(np.var(per["mean"], ddof=1) - np.mean(se_i ** 2), 0.0)
    per["shrunk"] = per["mean"] * tau2 / (tau2 + se_i ** 2)
    per = per.sort_values("shrunk")
    print(f"    implied true between-team SD {np.sqrt(tau2):.4f} minutes")
    print(per[["size", "mean", "shrunk"]].head(4).round(3).to_string())
    print("    ...")
    print(per[["size", "mean", "shrunk"]].tail(4).round(3).to_string())

    print("\n" + "=" * 96)
    print("2 — CREWSHOCK -> BONUS ACCELERATION")
    print("=" * 96)
    s = L.dropna(subset=["CrewShock", "LeagueFoulState"] + CTRL).copy()
    dev, hold = s[s["yr"] <= DEV_MAX], s[s["yr"] > DEV_MAX]

    def reg(x, y):
        Xf = np.column_stack([x["CrewShock"], x["LeagueFoulState"]]
                             + [x[c] for c in CTRL])
        bb, ss, t_ = ols(x[y].values, Xf)
        return bb[1], t_[1]

    print(f"  {'outcome':32}{'development':>22}{'holdout':>22}")
    for y, nm in (("fouls", "team fouls"),
                  ("q_reached", "quarters reaching bonus"),
                  ("opp_bonus_min", "opponent bonus MINUTES"),
                  ("nonshoot_in_bonus", "non-shooting fouls in bonus"),
                  ("bonus_fta", "FTA from bonus fouls"),
                  ("bonus_ftm", "FTM from bonus fouls"),
                  ("fta", "all FTA [reference]"),
                  ("pres_fta", "possession-preserving FTA")):
        cells = []
        for x in (dev, hold):
            xx = x.dropna(subset=[y])
            bb, t_ = reg(xx, y)
            cells.append(f"{bb:+11.4f} (t={t_:+5.2f})")
        print(f"  {nm:32}{cells[0]:>22}{cells[1]:>22}")

    print(f"\n  bonus ENTRY TIMING by quarter (seconds remaining; "
          f"positive = earlier entry)")
    print(f"  {'quarter':32}{'development':>22}{'holdout':>22}")
    for q in (1, 2, 3, 4):
        cells = []
        for x in (dev, hold):
            xx = x.dropna(subset=[f"entry_q{q}"])
            bb, t_ = reg(xx, f"entry_q{q}")
            cells.append(f"{bb:+11.3f} (t={t_:+5.2f})")
        print(f"  {'Q' + str(q) + ' entry (sec left)':32}"
              f"{cells[0]:>22}{cells[1]:>22}")

    print("\n" + "=" * 96)
    print("3 — HOW MUCH OF THE CREWSHOCK FT EFFECT IS THE BONUS CHANNEL?")
    print("=" * 96)
    b_all, t_all = reg(dev, "fta")
    b_bon, t_bon = reg(dev, "bonus_fta")
    b_pre, t_pre = reg(dev, "pres_fta")
    print(f"  development, per unit CrewShock, per team:")
    print(f"    all FTA                        {b_all:+.4f} (t={t_all:+.2f})")
    print(f"    of which bonus non-shooting    {b_bon:+.4f} (t={t_bon:+.2f})"
          f"   = {100*b_bon/b_all:.1f}% of the FTA effect")
    print(f"    of which possession-preserving {b_pre:+.4f} (t={t_pre:+.2f})"
          f"   = {100*b_pre/b_all:.1f}% of the FTA effect")
    print(f"\n  baseline shares of FTA in the data:")
    print(f"    bonus non-shooting {100*L['bonus_fta'].sum()/L['fta'].sum():.2f}%"
          f"   possession-preserving "
          f"{100*L['pres_fta'].sum()/L['fta'].sum():.2f}%")


if __name__ == "__main__":
    main()
