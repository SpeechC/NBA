"""Does visitor temporal possession allocation RELOCATE the CrewShock effect
between halves, rather than adding full-game points?

VISITOR STATE — recovered, not redefined. Exactly poss_vs_eff.py:

    prior  = that team's ROAD games in seasons STRICTLY BEFORE the current one
    B      = mean of q31 (Q3 minus Q1 points) over those games
    require n >= MIN_PRIOR = 60 road games; merge onto the season by TEAM_R

ORIENTATION, frozen before any outcome is examined. poss_vs_eff.py established
that higher B shifts possessions toward Q3, i.e. LATER. The hypothesis is stated
in terms of H1 exposure, so

    VisAlloc = -B      higher VisAlloc  =>  possessions shifted EARLIER (H1)

standardised on development only. This orientation is verified against
h1_poss_share -- a property of the state, checked before any outcome.

CrewShock and LeagueFoulState are LOADED from ref_features.csv, never rebuilt.

PREDICTED RELOCATION SIGNATURE, on the interaction d = CrewShock x VisAlloc:

    d_H1 > 0        d_H2 < 0        d_FG ~ 0

Development 2017-18..2023-24; SEALED mechanism holdout 2024-25. The DK H1 price
read is EXPLORATORY_IN_SAMPLE and runs only after the mechanism is locked.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import pbp_halves
import ref_shock as rsk
import refs
from dispersion_priced import ols

MIN_PRIOR = 60
DEV_MAX, SEALED = 2023, 2024
CTRL = rsk.CTRL
DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"


def visitor_state():
    """Exactly the poss_vs_eff.py construction. No tuning."""
    from bench_oos import build as bench_build
    gg, L = bench_build()
    road = L[L["road"]]
    out = []
    for yr in sorted(gg["yr"].unique()):
        prior = road[road["yr"] < yr]
        if prior["yr"].nunique() < 1:
            continue
        sig = prior.groupby("team").agg(B=("q31", "mean"),
                                        n=("q31", "size")).reset_index()
        sig = sig[sig["n"] >= MIN_PRIOR]
        cur = gg[gg["yr"] == yr].merge(sig.rename(columns={"team": "TEAM_R"}),
                                       on="TEAM_R", how="inner")
        out.append(cur)
    return pd.concat(out)[["gid", "yr", "B"]]


def build():
    V = visitor_state()
    H = pbp_halves.build()
    H["gid"] = H["gid"].astype(str).str.strip()
    V["gid"] = V["gid"].astype(str).str.strip().str.lstrip("0")
    H["gidj"] = H["gid"].str.lstrip("0")

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidj"] = m["gid"].str.lstrip("0")
    n0 = len(m)
    m = m.merge(V[["gid", "B"]].rename(columns={"gid": "gidj"}), on="gidj",
                how="left")
    print(f"  visitor state merged: {m['B'].notna().sum():,} of {n0:,}")
    m = m.merge(H.drop(columns=["gid"]), on="gidj", how="left")
    print(f"  half aggregates merged: {m['poss_h1'].notna().sum():,}")

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")
    return m


OUTS = [("poss_h1", "H1 possessions"), ("poss_h2", "H2 possessions"),
        ("poss_fg", "FG possessions"),
        ("fouls_h1", "H1 fouls"), ("fouls_h2", "H2 fouls"),
        ("fouls_fg", "FG fouls"),
        ("fta_h1", "H1 FTA"), ("fta_h2", "H2 FTA"), ("fta_fg", "FG FTA"),
        ("pts_h1", "H1 points"), ("pts_h2", "H2 points"),
        ("pts_fg", "FG points")]


def main():
    d = build()
    need = (["B", "CrewShock", "LeagueFoulState", "poss_h1", "h1_poss_share"]
            + [c for c, _ in OUTS] + CTRL)
    s = d.dropna(subset=need).copy()
    s = s[s["yr"] <= SEALED]
    dev = s[s["yr"] <= DEV_MAX]
    mu, sd = dev["B"].mean(), dev["B"].std()
    s["VisAlloc"] = -(s["B"] - mu) / sd
    dev = s[s["yr"] <= DEV_MAX]
    seal = s[s["yr"] == SEALED]

    print("\n" + "=" * 100)
    print("VISITOR x CREW ALLOCATION")
    print("=" * 100)
    print(f"  {len(s):,} games   development {len(dev):,}   "
          f"SEALED 2024-25 {len(seal):,}")
    print(f"  FROZEN develop standardisation of B: mu {mu:+.4f}  sd {sd:.4f}")
    print(f"  corr(VisAlloc, CrewShock) = "
          f"{np.corrcoef(s['VisAlloc'], s['CrewShock'])[0,1]:+.4f}")

    print("\n  ORIENTATION CHECK (property of the state, not an outcome)")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        r = np.corrcoef(x["VisAlloc"], x["h1_poss_share"])[0, 1]
        t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
        rb = np.corrcoef(x["B"], x["h1_poss_share"])[0, 1]
        print(f"    {lab:16} corr(VisAlloc, H1 poss share) {r:+.4f} "
              f"(t={t:+.2f})   [corr(B, .) = {rb:+.4f}]")
    print("    higher VisAlloc must mean MORE H1 possessions for the")
    print("    predicted signature to be stated in the right direction")

    print("\n" + "=" * 100)
    print("RELOCATION SIGNATURE — d = coefficient on CrewShock x VisAlloc")
    print("  Y ~ CrewShock + VisAlloc + CrewShock*VisAlloc + League + controls")
    print("  predicted:  d_H1 > 0    d_H2 < 0    d_FG ~ 0")
    print("=" * 100)
    print(f"  {'outcome':18} {'development':>24} {'SEALED 2024-25':>24}")
    rows = []
    for col, name in OUTS:
        cells = []
        for x in (dev, seal):
            X = np.column_stack([x["CrewShock"], x["VisAlloc"],
                                 x["CrewShock"] * x["VisAlloc"],
                                 x["LeagueFoulState"]] + [x[c] for c in CTRL])
            b, se, t = ols(x[col].values, X)
            cells.append(f"{b[3]:+9.4f} (t={t[3]:+5.2f})")
            rows.append({"outcome": col, "window": "dev" if x is dev else "seal",
                         "delta": round(b[3], 4), "t": round(t[3], 2),
                         "bR": round(b[1], 4), "bV": round(b[2], 4)})
        pre = ("  <- predicted >0" if col.endswith("_h1") else
               "  <- predicted <0" if col.endswith("_h2") else
               "  <- predicted ~0")
        print(f"  {name:18} {cells[0]:>24} {cells[1]:>24}{pre}")
    pd.DataFrame(rows).to_csv("visitor_crew_alloc_results.csv", index=False)

    print("\n" + "=" * 100)
    print("EXPLORATORY_IN_SAMPLE_MARKET_READ — DK H1 closing prices")
    print("  927 games, all 2023-24, INSIDE development. Not a validation.")
    print("  Purpose: decide whether buying more H1 price history is justified.")
    print("=" * 100)
    dk = pd.read_csv(DK, low_memory=False)
    dk = dk.dropna(subset=["h1_total_close"])
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["key"] = (pd.to_datetime(adv["DATE"]).dt.strftime("%Y-%m-%d") + "_"
                  + adv["ADV_TEAM_ABBR_R"].astype(str) + "_"
                  + adv["ADV_TEAM_ABBR_H"].astype(str))
    dk["key"] = dk["game_join_key"].astype(str)
    j = dk.merge(adv[["gid", "key"]], on="key", how="inner")
    print(f"  DK rows with an H1 close: {len(dk):,}   joined to games: {len(j):,}")
    k = s.merge(j[["gid", "h1_total_close", "full_game_total_close"]],
                on="gid", how="inner")
    print(f"  with the frozen state and half data: {len(k):,}")
    if len(k) < 100:
        print("  too few to read; stopping.")
        return
    k["h1_resid"] = k["pts_h1"] - k["h1_total_close"]
    k["alloc"] = k["CrewShock"] * k["h1_poss_share"]
    print(f"  H1 residual: mean {k['h1_resid'].mean():+.3f}  "
          f"sd {k['h1_resid'].std():.2f}   "
          f"over rate {100*(k['h1_resid']>0).mean():.2f}%")
    for lab, X, nm in (
            ("CrewShock alone", np.column_stack([k["CrewShock"]]), "CrewShock"),
            ("allocated CrewShock x H1 share",
             np.column_stack([k["alloc"]]), "alloc"),
            ("CrewShock x VisAlloc interaction",
             np.column_stack([k["CrewShock"], k["VisAlloc"],
                              k["CrewShock"] * k["VisAlloc"]]), "interaction")):
        b, se, t = ols(k["h1_resid"].values, X)
        i = len(b) - 1
        print(f"    {lab:34} coef {b[i]:+.4f}  t={t[i]:+.2f}")
    print("\n  c_market vs c_true on the H1 line, allocated CrewShock")
    X = np.column_stack([k["alloc"]])
    bm, _, tm = ols(k["h1_total_close"].values, X)
    bt, _, tt = ols(k["pts_h1"].values, X)
    print(f"    c_market {bm[1]:+.4f} (t={tm[1]:+5.2f})   "
          f"c_true {bt[1]:+.4f} (t={tt[1]:+5.2f})   gap {bt[1]-bm[1]:+.4f}")


if __name__ == "__main__":
    main()
