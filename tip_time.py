"""TIP TIME AND HOURS OF REST — executes PREREG_tip_time.md.

Does the closing line price rest in DAYS and miss the HOURS inside each
day-stratum? CrewShock template applied to the schedule.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side
from rest_travel import ARENAS, add_rest_travel

NPERM = 5000
RNG = np.random.default_rng(42)
DEV_SEASONS = ("2017-2018", "2018-2019", "2020-2021", "2021-2022",
               "2022-2023", "2023 In-Season", "2023-2024")
STRATA = (0, 1, 2)                     # prereg §2: 3+ excluded


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    n, k = X.shape
    se = np.sqrt(np.diag((r @ r / (n - k)) * np.linalg.pinv(X.T @ X)))
    return b, b / se, int(n)


def oos_r2(tr, te, cols, tgt):
    X = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in cols])
    y = tr[tgt].values
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
    Xt = np.column_stack([np.ones(len(te))] + [te[c].values for c in cols])
    yt = te[tgt].values
    okt = np.isfinite(yt) & np.all(np.isfinite(Xt), axis=1)
    pr = Xt[okt] @ b
    yt = yt[okt]
    return 1 - ((yt - pr) @ (yt - pr)) / ((yt - yt.mean()) @ (yt - yt.mean())), okt.sum()


def build():
    panel = pd.read_csv("tip_time_panel.csv", parse_dates=["date", "utc_ts"])
    # gid round-trips through CSV as int64 while the master keeps it as a
    # zero-padded string; without this cast the index alignment below silently
    # yields all-NaN and every row drops.
    panel["gid"] = panel["gid"].astype(str).str.strip()
    h = panel[panel.side == "H"].set_index("gid")
    a = panel[panel.side == "R"].set_index("gid")

    raw = read_master(verbose=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].astype(str).str.contains(
        "Regular Season|In-Season", na=False)].copy()
    gid = raw["GAME-ID"].astype(str).str.strip()
    hp = _side(raw, "H")["Y"].values.astype(float)
    ap = _side(raw, "R")["Y"].values.astype(float)

    d = pd.DataFrame({
        "gid": gid.values, "season": raw["season"].astype(str).values,
        "date": pd.to_datetime(raw["DATE"]).values,
        "home": raw["TEAM_H"].astype(str).str.strip().values,
        "away": raw["TEAM_R"].astype(str).str.strip().values,
        "to_close": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce").values,
        "sp_close": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce").values,
        "actual_total": hp + ap, "actual_margin": hp - ap}).set_index("gid")

    d["hours_H"] = h["hours_gap"]
    d["hours_R"] = a["hours_gap"]
    d["rest_H"] = h["rest_days"]
    d["rest_R"] = a["rest_days"]
    d["tip_hour"] = h["tip_hour"]

    d["H_sum"] = d.hours_H + d.hours_R
    d["H_diff"] = d.hours_H - d.hours_R
    off = {k: v[2] for k, v in ARENAS.items()}
    d["body_a"] = d.tip_hour + (d.away.map(off) - d.home.map(off))
    d["early"] = (d.tip_hour < 17).astype(float)

    d["dev"] = d.actual_total - d.to_close
    d["dev_s"] = d.actual_margin + d.sp_close

    d = attach_travel(d, raw, gid)

    for k in ("H", "R"):
        for s in STRATA:
            d[f"st{k}{s}"] = (d[f"rest_{k}"] == s).astype(float)
    d["is_dev"] = d.season.str.contains("|".join(DEV_SEASONS))
    d = d[d.rest_H.isin(STRATA) & d.rest_R.isin(STRATA)].copy()
    # a join failure must abort, not present itself as a null result
    for col, floor in (("hours_H", 6000), ("dev", 6000), ("tz_H", 4000)):
        n = int(d[col].notna().sum())
        if n < floor:
            raise RuntimeError(f"JOIN FAILURE: {col} populated on {n} rows "
                               f"(expected >= {floor}); aborting rather than "
                               f"reporting a null")
    return d.reset_index()


def attach_travel(d, raw, gid):
    """tz_shift / travel_km for both sides, via rest_travel on a side panel."""
    parts = {}
    for suf, tag in (("H", "H"), ("R", "R")):
        # _side already carries game_id in the master's NATIVE int64 dtype, and
        # add_rest_travel maps it against raw["GAME-ID"] (also int64). Casting
        # it to str here breaks that lookup and yields all-NaN travel.
        p = _side(raw, suf).copy()
        try:
            p = add_rest_travel(p, raw)
        except Exception as ex:                                   # noqa: BLE001
            print(f"  [warn] add_rest_travel({suf}) failed: {ex}; travel=NaN")
            p["tz_shift"] = np.nan
            p["travel_km"] = np.nan
        p["game_id"] = p["game_id"].astype(str).str.strip()   # match d's index
        parts[tag] = p.set_index("game_id")[["tz_shift", "travel_km"]]
    for tag in ("H", "R"):
        d[f"tz_{tag}"] = parts[tag]["tz_shift"]
        d[f"km_{tag}"] = parts[tag]["travel_km"]
    return d


CTRL = [f"st{k}{s}" for k in ("H", "R") for s in STRATA[:-1]] + \
       ["tz_H", "tz_R", "km_H", "km_R"]


def perm_one_sided(x, y, key, ctl, label):
    cols = [x[key].values] + [x[c].values for c in ctl]
    b, t, n = ols_t(y, cols)
    obs = b[1]
    yrs = x["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    v = x[key].values
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for bl in blocks:
            p[bl] = v[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols_t(y, [p] + [x[c].values for c in ctl])
        null[i] = bb[1]
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"    {label:28} n={n:>6,}  beta {obs:+.5f} (t={t[1]:+.2f})   "
          f"null {null.mean():+.5f} sd {null.std():.5f}   p1={p1:.4f} p2={p2:.4f}")
    return obs, t[1], p1, null.std()


def main():
    d = build()
    print(f"built {len(d):,} games (rest strata {STRATA});  "
          f"development {int(d.is_dev.sum()):,}  holdout {int((~d.is_dev).sum()):,}")
    for c in ("tz_H", "km_H"):
        print(f"  control coverage {c}: {d[c].notna().mean():.3f}")

    dv = d[d.is_dev]
    print(f"\n  H_sum: mean {dv.H_sum.mean():.1f}h  sd {dv.H_sum.std():.1f}h  "
          f"IQR {dv.H_sum.quantile(.25):.1f}-{dv.H_sum.quantile(.75):.1f}")

    print("\n=== P1 PRIMARY — dev ~ H_sum + strata + travel  (predicted > 0) ===")
    x = dv.dropna(subset=["dev", "H_sum"] + CTRL)
    obs, tt, p1, nsd = perm_one_sided(x, x.dev.values, "H_sum", CTRL, "P1 H_sum -> dev")

    print("\n=== SECONDARIES ===")
    xs = dv.dropna(subset=["dev_s", "H_diff"] + CTRL)
    perm_one_sided(xs, xs.dev_s.values, "H_diff", CTRL, "P2 H_diff -> dev_s (>0)")
    xb = dv.dropna(subset=["dev_s", "body_a"] + CTRL)
    perm_one_sided(xb, xb.dev_s.values, "body_a", CTRL, "P3 body_a -> dev_s (>0)")
    xe = dv.dropna(subset=["dev", "early"] + CTRL)
    b, t, n = ols_t(xe.dev.values, [xe.early.values] + [xe[c].values for c in CTRL])
    print(f"    {'P4 early -> dev (<0)':28} n={n:>6,}  beta {b[1]:+.5f} "
          f"(t={t[1]:+.2f})   early on {100*xe.early.mean():.1f}% of games")

    print("\n=== SECTION 5 INCREMENTAL (holdout, scored once) ===")
    tr = d[d.is_dev].dropna(subset=["dev", "H_sum"] + CTRL)
    te = d[~d.is_dev].dropna(subset=["dev", "H_sum"] + CTRL)
    A, nA = oos_r2(tr, te, CTRL, "dev")
    B, nB = oos_r2(tr, te, CTRL + ["H_sum"], "dev")
    print(f"    n_ho={nB:,}   A(rest+travel) OOS R2 {A:+.6f}   "
          f"B(+H_sum) OOS R2 {B:+.6f}   B-A {B-A:+.6f}   "
          f"{'B WINS' if B > A else 'A WINS -> P1 does not advance'}")

    print("\n=== SECTION 7 MINIMUM DETECTABLE EFFECT ===")
    sd_h = x.H_sum.std()
    mde = 1.96 * nsd
    print(f"    permutation sd of beta   {nsd:.5f} pts per hour")
    print(f"    MDE at 95% (1.96 sd)     {mde:.5f} pts/hour "
          f"= {mde*sd_h:.4f} pts per 1 SD of H_sum ({sd_h:.1f}h)")
    print(f"    observed beta            {obs:+.5f} pts/hour "
          f"= {obs*sd_h:+.4f} pts per 1 SD")
    p50 = x.H_sum.quantile(.95) - x.H_sum.quantile(.05)
    print(f"    p5-p95 span of H_sum     {p50:.1f}h -> observed effect across "
          f"that span {obs*p50:+.4f} total points")
    edge = abs(obs * p50) / 13.0        # ~13 pts sd of dev -> prob shift proxy
    print(f"    implied hit-rate edge over 52.38% break-even: ~{100*edge:.2f}pp "
          f"-> n needed = {7.84*0.25/max(edge,1e-9)**2:,.0f} games"
          if edge > 0 else "    effect is signed against the prediction")


if __name__ == "__main__":
    main()
