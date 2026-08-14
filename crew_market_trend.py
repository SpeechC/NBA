"""Is the market learning to price CrewShock?

For each season s, on identical rows:

    b_fouls,s    raw fouls   ~ CrewShock + LeagueFoulState + controls
    b_open,s     OPENING total ~ same
    b_close,s    CLOSING total ~ same          = c_market
    b_actual,s   ACTUAL total  ~ same          = c_true
    gap_s        = b_actual - b_close
    move_s       = b_close - b_open

NBA crew assignments are published mid-morning, usually AFTER the opening
number is posted. So `move_s` is how much the market adjusts its total on
referee news specifically, and its trend is the direct test of learning.

Learning would look like: b_fouls flat (mechanism unchanged), move rising,
gap falling. Everything frozen -- CrewShock, LeagueFoulState, controls,
split. Nothing is rebuilt.

Inference: naive per-season SEs are reported but the TREND statistics are
tested against the time-local (7-day block) crew permutation, because the
regressor is referee-derived.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as rf
import ref_shock as rsk
import refs
from dispersion_priced import ols

CTRL = rsk.CTRL
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
THR = 0.8682
NPERM = 400
BLOCK_DAYS = 7
BE = 110 / 210
STAKE, WIN = 100.0, 100.0 * 100.0 / 110.0
RNG = np.random.default_rng(4711)

TGT = [("fouls", "raw fouls"), ("open", "OPENING total"),
       ("total", "CLOSING total"), ("actual", "ACTUAL total")]


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["open"] = n("OPENING TOTAL_H")
    m["fouls"] = n("PF_H") + n("PF_R")
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")
    return m


def season_coefs(x, targets=TGT):
    """Return {target: (coef, se, t)} for one season."""
    out = {}
    for col, _ in targets:
        X = np.column_stack([x["CrewShock"], x["LeagueFoulState"]]
                            + [x[c] for c in CTRL])
        b, se, t = ols(x[col].values, X)
        out[col] = (b[1], se[1], t[1])
    return out


def wls_trend(years, vals, ses):
    """Inverse-variance weighted slope of `vals` on season index."""
    x = np.asarray(years, float)
    x = x - x.mean()
    y = np.asarray(vals, float)
    w = 1.0 / np.asarray(ses, float) ** 2
    sw = w.sum()
    sx = (w * x).sum() / sw
    sy = (w * y).sum() / sw
    sxx = (w * (x - sx) ** 2).sum()
    sxy = (w * (x - sx) * (y - sy)).sum()
    slope = sxy / sxx
    se = np.sqrt(1.0 / sxx)
    return slope, se, slope / se


def series(s):
    """Per-season coefficient table."""
    rows = []
    for y, g in s.groupby("yr"):
        c = season_coefs(g)
        rows.append({
            "yr": int(y), "n": len(g),
            "b_fouls": c["fouls"][0], "se_fouls": c["fouls"][1],
            "b_open": c["open"][0], "se_open": c["open"][1],
            "b_close": c["total"][0], "se_close": c["total"][1],
            "b_actual": c["actual"][0], "se_actual": c["actual"][1]})
    T = pd.DataFrame(rows)
    T["gap"] = T["b_actual"] - T["b_close"]
    T["se_gap"] = np.sqrt(T["se_actual"] ** 2 + T["se_close"] ** 2)
    T["move"] = T["b_close"] - T["b_open"]
    T["se_move"] = np.sqrt(T["se_close"] ** 2 + T["se_open"] ** 2)
    return T


def main():
    d = build()
    need = ["CrewShock", "LeagueFoulState", "open", "total", "actual",
            "fouls"] + CTRL
    s = d.dropna(subset=need).copy()
    print(f"  {len(s):,} games with the full control set, "
          f"seasons {sorted(s['yr'].unique())}")
    print(f"  opening total present on {100*d['open'].notna().mean():.1f}% "
          f"of the panel")

    T = series(s)
    print("\n" + "=" * 104)
    print("PER-SEASON COEFFICIENTS ON FROZEN CrewShock")
    print("  gap = c_true - c_market      move = c_close - c_open")
    print("=" * 104)
    print(f"  {'season':8} {'n':>5} {'b_fouls':>15} {'b_open':>15} "
          f"{'b_close':>15} {'b_actual':>15} {'gap':>9} {'move':>9}")
    for _, r in T.iterrows():
        print(f"  {int(r['yr']):<8} {int(r['n']):5,} "
              f"{r['b_fouls']:+7.3f}({r['b_fouls']/r['se_fouls']:+5.2f}) "
              f"{r['b_open']:+7.3f}({r['b_open']/r['se_open']:+5.2f}) "
              f"{r['b_close']:+7.3f}({r['b_close']/r['se_close']:+5.2f}) "
              f"{r['b_actual']:+7.3f}({r['b_actual']/r['se_actual']:+5.2f}) "
              f"{r['gap']:+9.3f} {r['move']:+9.3f}")

    print("\n" + "=" * 104)
    print("TRENDS — inverse-variance weighted slope per season")
    print("=" * 104)
    tr = {}
    for col, se_col, lab in (("b_fouls", "se_fouls", "mechanism (raw fouls)"),
                             ("b_close", "se_close", "c_market (closing)"),
                             ("b_actual", "se_actual", "c_true (actual)"),
                             ("gap", "se_gap", "GAP = c_true - c_market"),
                             ("move", "se_move", "MOVE = close - open")):
        sl, se, t = wls_trend(T["yr"], T[col], T[se_col])
        tr[col] = sl
        print(f"  {lab:26} slope per season {sl:+.4f}  se {se:.4f}  "
              f"t={t:+.2f}")
    print("\n  learning would be: mechanism flat, MOVE rising, GAP falling")

    print("\n  first half vs second half of the sample")
    early, late = T[T["yr"] <= 2021], T[T["yr"] >= 2022]
    print(f"    {'quantity':26} {'2017-2021':>12} {'2022-2025':>12} "
          f"{'change':>10}")
    for col, lab in (("b_fouls", "mechanism"), ("b_close", "c_market"),
                     ("b_actual", "c_true"), ("gap", "gap"),
                     ("move", "move")):
        a, b_ = early[col].mean(), late[col].mean()
        print(f"    {lab:26} {a:12.4f} {b_:12.4f} {b_-a:+10.4f}")

    print("\n" + "=" * 104)
    print(f"TIME-LOCAL PERMUTATION on the trend slopes, {NPERM} reshuffles")
    print("=" * 104)
    uni = rf.universe()
    k = rf.estimate_k(uni)[0]
    ublk = (uni["yr"].astype(str) + "_"
            + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
               .dt.days // BLOCK_DAYS).astype(str)).values
    ucrew = uni[["ref1", "ref2", "ref3"]].values
    ublocks = [np.where(ublk == b_)[0] for b_ in pd.unique(ublk)]
    keep = pd.Series(np.arange(len(uni)),
                     index=uni["gid"].astype(str)).reindex(s["gid"]).values
    sub, ss = uni.copy(), s.copy()
    obs = {c: tr[c] for c in ("b_close", "gap", "move")}
    null = {c: np.empty(NPERM) for c in obs}
    for j in range(NPERM):
        perm = ucrew.copy()
        for b_ in ublocks:
            if len(b_) > 1:
                perm[b_] = ucrew[b_][RNG.permutation(len(b_))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        cs = rf.matched_ref_effect(sub, k)["CrewShock"].values
        ss["CrewShock"] = cs[keep]
        Tn = series(ss)
        for c, sec in (("b_close", "se_close"), ("gap", "se_gap"),
                       ("move", "se_move")):
            null[c][j] = wls_trend(Tn["yr"], Tn[c], Tn[sec])[0]
    for c, lab in (("b_close", "c_market trend"), ("gap", "gap trend"),
                   ("move", "move trend")):
        o, n_ = obs[c], null[c]
        p_hi = (1 + np.sum(n_ >= o)) / (NPERM + 1)
        p_lo = (1 + np.sum(n_ <= o)) / (NPERM + 1)
        print(f"  {lab:18} observed {o:+.4f}   null mean {n_.mean():+.4f} "
              f"sd {n_.std():.4f}   z={(o-n_.mean())/n_.std():+.2f}   "
              f"p(rise)={p_hi:.4f}  p(fall)={p_lo:.4f}")

    print("\n" + "=" * 104)
    print("ECONOMIC — frozen Q85 strategy by season, for reference")
    print("=" * 104)
    full = refs.build()
    full["gid"] = full["GAME-ID"].astype(str).str.strip()
    f2 = pd.read_csv("ref_features.csv")
    f2["gid"] = f2["gid"].astype(str).str.strip()
    full = full.merge(f2[["gid", "CrewShock"]], on="gid", how="inner").dropna(
        subset=["CrewShock", "e"])
    b = full[full["CrewShock"] >= THR]
    print(f"  {'season':8} {'bets':>6} {'win %':>7} {'$ won':>9} {'mean e':>8}")
    for y, g in b.groupby("yr"):
        w = int((g["e"] > 0).sum())
        l = int((g["e"] < 0).sum())
        wp = 100 * w / (w + l) if w + l else np.nan
        print(f"  {int(y):<8} {len(g):6,} {wp:7.2f} {w*WIN-l*STAKE:9,.0f} "
              f"{g['e'].mean():8.3f}")
    yrs = sorted(b["yr"].unique())
    wr = [100 * (b[b.yr == y]["e"] > 0).mean() for y in yrs]
    x = np.array(yrs, float) - np.mean(yrs)
    sl = np.polyfit(x, wr, 1)[0]
    print(f"\n  win-rate trend {sl:+.3f} pp per season "
          f"(corr {np.corrcoef(x, wr)[0,1]:+.3f}, n={len(yrs)} seasons)")


if __name__ == "__main__":
    main()
