"""Does the totals market price offensive-rebound possession extensions?

An OREB retains the offensive possession and creates another scoring
opportunity inside it. Frequency and value are estimated separately, then
combined only as an accounting identity:

    SecondChancePressure = ExpectedExtensions x ExpectedValuePerExtension

Development 2017-18..2023-24; SEALED holdout 2024-25 (play-by-play ends there).
Every team state is strictly prior-only: shift(1), rolling 20, min 10, within
season. CrewShock is deliberately NOT used.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import oreb_extract
import ref_shock as rsk
import refs
from dispersion_priced import ols

W, MINP = 20, 10
DEV_MAX, SEALED = 2023, 2024
CTRL = ["pace_s", "oeff_s", "deff_s", "mu_state"]


def build():
    P = oreb_extract.build()
    g = oreb_extract.game_team(P)
    g["gid"] = g["gid"].astype(str).str.zfill(10)

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]], on="gid",
                how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")

    # long panel: one row per game-team, with opponent linkage
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "gid": m["gid"], "yr": m["yr"],
            "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"]}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(g, left_on=["gidz", "team"], right_on=["gid", "team"],
                how="inner", suffixes=("", "_g")).drop(columns=["gid_g"])
    L = L.sort_values("date").reset_index(drop=True)

    # prior-only own OREB rate and own second-chance value
    grp = L.groupby(["yr", "team"])
    L["prior_oreb_rate"] = grp["oreb_rate"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    # expected possessions must ALSO be prior-only. Using the game's realised
    # possession count here makes the state a pace proxy and leaks same-game
    # information -- the first-chance placebo catches it immediately.
    L["prior_poss"] = grp["poss"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["v2c"] = L["pts_2c"] / L["oreb_ext"].replace(0, np.nan)
    L["prior_v2c"] = grp["v2c"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())

    # prior-only OREB rate ALLOWED by each team on defence
    opp = L[["gidz", "team", "oreb_rate", "v2c"]].rename(
        columns={"team": "opp", "oreb_rate": "opp_oreb_rate",
                 "v2c": "opp_v2c"})
    L = L.merge(opp, on=["gidz", "opp"], how="left")
    gd = L.groupby(["yr", "team"])
    L["prior_oreb_allowed"] = gd["opp_oreb_rate"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prior_v2c_allowed"] = gd["opp_v2c"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    return L, m


def main():
    L, m = build()
    L = L[L["yr"] <= SEALED]
    print(f"  game-team rows {len(L):,}   games {L['gidz'].nunique():,}")

    print("\n" + "=" * 96)
    print("STEP 1 — SECOND-CHANCE VALUE: is it forecastable at team level?")
    print("=" * 96)
    d = L[L["yr"] <= DEV_MAX].dropna(subset=["prior_v2c", "v2c"])
    r = np.corrcoef(d["prior_v2c"], d["v2c"])[0, 1]
    t = r * np.sqrt(len(d) - 2) / np.sqrt(1 - r * r)
    print(f"  game level: corr(prior-20 own 2C value, realised) {r:+.4f} "
          f"(t={t:+.2f}, n={len(d):,})")
    ts = L[L["yr"] <= DEV_MAX].groupby(["yr", "team"]).agg(
        v=("pts_2c", "sum"), e=("oreb_ext", "sum"), n=("v2c", "size"))
    ts = ts[ts["n"] >= 40]
    ts["val"] = ts["v"] / ts["e"]
    ts = ts.reset_index()
    ts["nxt"] = ts["yr"] + 1
    j = ts.merge(ts, left_on=["team", "nxt"], right_on=["team", "yr"],
                 suffixes=("_t", "_n"))
    rs = np.corrcoef(j["val_t"], j["val_n"])[0, 1]
    print(f"  season to season: corr {rs:+.4f} (n={len(j)} pairs)")
    lg = d["pts_2c"].sum() / d["oreb_ext"].sum()
    print(f"  league second-chance value on development: {lg:.4f} pts/extension")
    use_team = abs(r) > 0.10 and abs(rs) > 0.20
    print(f"  -> team-specific 2C value {'IS' if use_team else 'is NOT'} "
          f"forecastable; using "
          f"{'team states' if use_team else 'the frozen league prior'}")

    print("\n" + "=" * 96)
    print("STEP 2 — EXPECTED EXTENSIONS, additive model frozen on development")
    print("  realised OREB rate ~ a + b1*prior own rate + b2*prior opp allowed")
    print("=" * 96)
    dd = L[L["yr"] <= DEV_MAX].dropna(
        subset=["prior_oreb_rate", "prior_oreb_allowed", "oreb_rate"])
    X = np.column_stack([dd["prior_oreb_rate"], dd["prior_oreb_allowed"]])
    b, se, tt = ols(dd["oreb_rate"].values, X)
    print(f"  intercept {b[0]:+.5f}   own rate {b[1]:+.4f} (t={tt[1]:+.2f})"
          f"   opp allowed {b[2]:+.4f} (t={tt[2]:+.2f})   n={len(dd):,}")
    L["exp_rate"] = b[0] + b[1] * L["prior_oreb_rate"] \
        + b[2] * L["prior_oreb_allowed"]
    L["exp_ext"] = L["exp_rate"] * L["prior_poss"]
    for lab, x in (("development", L[L["yr"] <= DEV_MAX]),
                   ("SEALED 2024-25", L[L["yr"] == SEALED])):
        s = x.dropna(subset=["exp_ext", "oreb_ext"])
        rr = np.corrcoef(s["exp_ext"], s["oreb_ext"])[0, 1]
        print(f"    {lab:16} corr(expected, realised extensions) {rr:+.4f} "
              f"n={len(s):,}")

    print("\n" + "=" * 96)
    print("STEP 3 — GAME-LEVEL STATE AND THE ACCOUNTING CHAIN")
    print("=" * 96)
    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        exp_ext=("exp_ext", "sum"), oreb_ext=("oreb_ext", "sum"),
        pts_2c=("pts_2c", "sum"), pts_1c=("pts_1c", "sum"),
        fga_2c=("fga_2c", "sum"), fta_2c=("fta_2c", "sum"),
        poss=("poss", "sum"), pts=("pts", "sum"))
    val = lg if not use_team else np.nan
    G["scp"] = G["exp_ext"] * val
    mm = m[["gidz", "total", "actual", "e"] + CTRL].copy()
    G = G.merge(mm, on="gidz", how="inner").dropna(
        subset=["exp_ext", "total", "actual"] + CTRL)
    print(f"  corr(expected extensions, expected pace state) = "
          f"{np.corrcoef(G['exp_ext'], G['pace_s'])[0,1]:+.4f}"
          "   [high values mean the state is mostly a pace proxy]")
    dev, seal = G[G["yr"] <= DEV_MAX], G[G["yr"] == SEALED]
    print(f"  games {len(G):,}   development {len(dev):,}   "
          f"SEALED {len(seal):,}")

    def reg(x, y, sig="exp_ext"):
        Xf = np.column_stack([x[sig]] + [x[c] for c in CTRL])
        bb, ss, t_ = ols(x[y].values, Xf)
        return bb[1], t_[1]

    print(f"\n  {'link':34}{'development':>22}{'SEALED 2024-25':>22}")
    for y, nm in (("oreb_ext", "expected -> realised extensions"),
                  ("pts_2c", "expected -> second-chance points"),
                  ("pts_1c", "expected -> FIRST-chance points [placebo]"),
                  ("poss", "expected -> total possessions"),
                  ("actual", "expected -> ACTUAL total"),
                  ("total", "expected -> CLOSING total"),
                  ("e", "expected -> closing residual")):
        cells = []
        for x in (dev, seal):
            bb, t_ = reg(x, y)
            cells.append(f"{bb:+11.4f} (t={t_:+5.2f})")
        print(f"  {nm:34}{cells[0]:>22}{cells[1]:>22}")

    print("\n" + "=" * 96)
    print("STEP 4 — GROSS VERSUS NET, per +1 expected extension (development)")
    print("=" * 96)
    per = {}
    for y in ("oreb_ext", "fga_2c", "fta_2c", "pts_2c", "pts_1c", "poss",
              "actual"):
        per[y], _ = reg(dev, y)
    r_ext = per["oreb_ext"]
    print(f"  +1 expected extension delivers {r_ext:+.4f} realised extensions")
    print(f"  per REALISED extension:")
    for y, nm in (("fga_2c", "second-chance FGA"),
                  ("fta_2c", "second-chance FTA"),
                  ("pts_2c", "GROSS second-chance points"),
                  ("pts_1c", "first-chance points elsewhere"),
                  ("poss", "total possessions"),
                  ("actual", "NET game points")):
        print(f"    {nm:32}{per[y]/r_ext:+8.4f}")
    print(f"\n  gross second-chance {per['pts_2c']/r_ext:+.4f}  "
          f"offset elsewhere {per['pts_1c']/r_ext:+.4f}  "
          f"= net {per['actual']/r_ext:+.4f} points")

    print("\n" + "=" * 96)
    print("STEP 5 — MARKET PRICING")
    print("=" * 96)
    print(f"  {'window':16}{'c_market':>12}{'t':>8}{'c_true':>10}{'t':>8}"
          f"{'gap':>10}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal),
                   ("pooled", G)):
        bm, tm = reg(x, "total")
        bt, tt_ = reg(x, "actual")
        print(f"  {lab:16}{bm:+12.4f}{tm:8.2f}{bt:+10.4f}{tt_:8.2f}"
              f"{bt-bm:+10.4f}")

    print("\n  frozen development quintiles of expected extensions")
    q = dev["exp_ext"].quantile([0, .2, .4, .6, .8, 1.0]).values.copy()
    q[0], q[-1] = -np.inf, np.inf
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        x = x.copy()
        x["b"] = pd.cut(x["exp_ext"], q, labels=[1, 2, 3, 4, 5])
        print(f"    {lab}")
        print(f"      {'Q':>3}{'n':>7}{'exp ext':>9}{'real ext':>10}"
              f"{'2C pts':>9}{'close':>9}{'actual':>9}{'resid':>9}{'over %':>9}")
        for bq, gg in x.groupby("b", observed=True):
            ov = 100 * (gg["e"] > 0).mean()
            print(f"      {bq:>3}{len(gg):7,}{gg['exp_ext'].mean():9.2f}"
                  f"{gg['oreb_ext'].mean():10.2f}{gg['pts_2c'].mean():9.2f}"
                  f"{gg['total'].mean():9.2f}{gg['actual'].mean():9.2f}"
                  f"{gg['e'].mean():9.3f}{ov:9.2f}")


if __name__ == "__main__":
    main()
