"""PREREG_injury.md market tests. Stage-0 gates PASSED (Q1 99.2%, Q2 99.95%,
Q3 100%) on the scoped window 2020-21..2024-25.

HYPOTHESIS A (primary) - the totals channel of role-specific absence
  A1  DEF_ANCHOR absences: gap = c_true - c_market > 0 on the CLOSING total
  A2  OFF_STAR absences:   gap ~ 0 (priced)
  A3  falsification: OUT_baseline (known before the open) shows gap ~ 0
      against the OPEN
  Inference: within-season permutation of the absence state, 5,000 reps.

HYPOTHESIS B (secondary) - intraday status change as a THIRD movement source
  B1  OUT_late / UPGRADE_late predict open->close TOTAL movement
  B2  survives JOINTLY with MOVE_RIDGE_OOS and MOVE_LATENT_OOS

Everything frozen in the prereg: MIN_SHARE top-3 salience, BLK36 development
top quintile for DEF_ANCHOR, min-prior floors, MIN_SHARE weighting. No
injury-type/severity/player-name conditioning anywhere.

Development 2020-21..2023-24; holdout 2024-25 ONLY (one season, reduced power
stated in every holdout line).
"""
import re
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import opening_line_error_decomposition as OLE
import ref_shock as rsk

PANEL = "injury_status_panel.csv"
PBP = "/home/dpope/data/pbp_lineups_all.parquet"
SIDECAR = "/mnt/c/NBA2/move_signal_states.csv"
DEV_MAX, HOLD = 2023, 2024
MIN_PRIOR_G, MIN_PRIOR_MIN = 10, 300
NPERM = 5000
RNG = np.random.default_rng(20260828)

# per-player per-game seconds and blocks, from the lineup PBP
SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
         PLAYER1_ID AS pid, PLAYER1_NAME AS pname,
         PLAYER1_TEAM_ABBREVIATION AS abbr,
         EVENTMSGTYPE AS msg
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE='RegularSeason' AND PLAYER1_ID>0 AND PLAYER1_NAME IS NOT NULL
),
blk AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
         PLAYER3_ID AS pid, count(*) AS blocks
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE='RegularSeason' AND EVENTMSGTYPE=2 AND PLAYER3_ID>0
  GROUP BY 1,2
)
SELECT e.gid, e.pid, any_value(e.pname) AS pname, any_value(e.abbr) AS abbr,
       count(*) AS events, any_value(b.blocks) AS blocks
FROM ev e LEFT JOIN blk b ON e.gid=b.gid AND e.pid=b.pid
GROUP BY e.gid, e.pid
"""


def norm_name(s):
    s = re.sub(r"[^a-z,]", "", str(s).lower())
    if "," in s:
        last, _, first = s.partition(",")
        s = first + last
    return s


def build():
    g = OLE.load()
    g = g[(g["season"] >= 2020) & (g["season"] <= HOLD)].copy()
    g["gidz"] = g["gid"].str.zfill(10)
    g["date_s"] = g["date"].dt.strftime("%Y-%m-%d")

    # ---- player-game facts from the PBP (players who PLAYED) --------------
    M = duckdb.connect().execute(SQL).fetchdf()
    M["gid"] = M["gid"].astype(str)
    M["blocks"] = M["blocks"].fillna(0.0)
    M["key"] = M["pname"].map(norm_name)
    M = M.merge(g[["gidz", "season", "date"]].rename(columns={"gidz": "gid"}),
                on="gid", how="inner")
    M["tot"] = M.groupby(["gid", "abbr"])["events"].transform("sum")
    M["share"] = M["events"] / M["tot"]
    M = M.sort_values("date")
    gp = M.groupby(["season", "key"])
    M["min_share"] = gp["share"].transform(
        lambda s: s.shift(1).rolling(20, min_periods=MIN_PRIOR_G).mean())
    M["ev_cum"] = gp["events"].transform(lambda s: s.shift(1).cumsum())
    M["blk_cum"] = gp["blocks"].transform(lambda s: s.shift(1).cumsum())
    M["blk36"] = np.where(M["ev_cum"] >= MIN_PRIOR_MIN,
                          M["blk_cum"] / M["ev_cum"] * 36.0, np.nan)

    # ---- player STATE as of a date: their latest prior appearance ---------
    # (an OUT player is absent from tonight's PBP, so the state must be
    #  carried forward from earlier games -- this is the join the first
    #  version got wrong)
    state = M.loc[M["min_share"].notna(),
                  ["date", "season", "key", "abbr", "min_share", "blk36"]] \
        .sort_values("date")

    # ---- team roster ranking at each team game-date (for SALIENT top-3) ---
    tdates = pd.concat([
        g[["season", "date", "home"]].rename(columns={"home": "team"}),
        g[["season", "date", "away"]].rename(columns={"away": "team"})])
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    tdates["abbr"] = tdates["team"].map(mp)
    tdates = tdates.dropna(subset=["abbr"])[["season", "abbr", "date"]] \
        .drop_duplicates()
    roster = M[["season", "abbr", "key"]].drop_duplicates()
    cross = roster.merge(tdates, on=["season", "abbr"]).sort_values("date")
    cross = pd.merge_asof(
        cross, state[["date", "key", "min_share", "blk36"]].sort_values("date"),
        on="date", by="key", direction="backward",
        allow_exact_matches=False).dropna(subset=["min_share"])
    cross["rk"] = cross.groupby(["abbr", "date"])["min_share"].rank(
        ascending=False, method="first")
    cross["salient"] = cross["rk"] <= 3
    q_blk = cross.loc[(cross["season"] <= DEV_MAX) & cross["salient"],
                      "blk36"].quantile(0.80)
    cross["def_anchor"] = cross["salient"] & (cross["blk36"] >= q_blk)
    cross["off_star"] = cross["salient"] & ~cross["def_anchor"]
    print(f"  role thresholds FROZEN on development: BLK36 q80 = {q_blk:.4f}")
    print(f"  player-date role rows {len(cross):,}   salient "
          f"{int(cross['salient'].sum()):,}   DEF_ANCHOR "
          f"{int(cross['def_anchor'].sum()):,}")

    # ---- injury status transitions per (game date, player) ----------------
    P = pd.read_csv(PANEL, parse_dates=["report_ts", "game_date"])
    P["key"] = P["player"].map(norm_name)
    P["date_s"] = P["game_date"].dt.strftime("%Y-%m-%d")
    grp = P.groupby(["date_s", "matchup"])["report_ts"]
    P["first_ts"], P["last_ts"] = grp.transform("min"), grp.transform("max")
    first = P[P["report_ts"] == P["first_ts"]][["date_s", "key", "status"]] \
        .rename(columns={"status": "st_first"}).drop_duplicates(
            ["date_s", "key"])
    last = P[P["report_ts"] == P["last_ts"]][["date_s", "key", "status"]] \
        .rename(columns={"status": "st_last"}).drop_duplicates(
            ["date_s", "key"])
    S = last.merge(first, on=["date_s", "key"], how="left")
    S["OUT_baseline"] = (S["st_first"] == "Out").astype(float)
    S["OUT_late"] = ((S["st_first"] != "Out")
                     & (S["st_last"] == "Out")).astype(float)
    S["UPGRADE_late"] = (S["st_first"].isin(["Out", "Doubtful"])
                         & ~S["st_last"].isin(["Out", "Doubtful"])
                         ).astype(float)
    S["date"] = pd.to_datetime(S["date_s"])

    R = cross.merge(S, on=["date", "key"], how="inner")
    print(f"  injury rows matched to a role state: {len(R):,}   "
          f"of which salient {int(R['salient'].sum()):,}")
    for st in ("OUT_baseline", "OUT_late", "UPGRADE_late"):
        for role_col, tag in (("def_anchor", "DEF"), ("off_star", "OFF")):
            R[f"{st}_{tag}"] = R[st] * R[role_col] * R["min_share"]
    cols = [f"{s}_{t}" for s in ("OUT_baseline", "OUT_late", "UPGRADE_late")
            for t in ("DEF", "OFF")]
    agg = R.groupby(["date", "abbr"], as_index=False)[cols].sum()

    # game level: sum both teams
    long = pd.concat([
        g[["gid", "season", "date", "home"]].rename(columns={"home": "team"}),
        g[["gid", "season", "date", "away"]].rename(columns={"away": "team"})])
    long["abbr"] = long["team"].map(mp)
    long = long.merge(agg, on=["date", "abbr"], how="left").fillna(
        {c: 0.0 for c in cols})
    gl = long.groupby("gid", as_index=False)[cols].sum()

    d = g.merge(gl, on="gid", how="left").fillna({c: 0.0 for c in cols})
    ctl = rsk.build()[["gid"] + rsk.CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    d = d.merge(ctl, on="gid", how="left")
    sc = pd.read_csv(SIDECAR)
    sc["gid"] = sc["GAME-ID"].astype(str).str.strip()
    d = d.merge(sc[["gid", "MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"]], on="gid",
                how="left")
    return d.dropna(subset=rsk.CTRL)


def ols_t(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se


def gap_test(d, state, target_true, target_mkt, lab):
    """c_true, c_market and gap on `state`, with frozen controls."""
    out = []
    for wl, x in (("development", d[d["season"] <= DEV_MAX]),
                  ("holdout 2024-25", d[d["season"] == HOLD])):
        X = [x[state].values] + [x[c].values for c in rsk.CTRL]
        bt, tt = ols_t(x[target_true].values, X)
        bm, tm = ols_t(x[target_mkt].values, X)
        bg, tg = ols_t((x[target_true] - x[target_mkt]).values, X)
        out.append((wl, len(x), bt[1], tt[1], bm[1], tm[1], bg[1], tg[1]))
    print(f"\n  {lab}")
    print(f"    {'window':18}{'n':>7}{'c_true':>10}{'t':>7}{'c_market':>11}"
          f"{'t':>7}{'gap':>9}{'t':>7}")
    for wl, n, bt, tt, bm, tm, bg, tg in out:
        print(f"    {wl:18}{n:>7,}{bt:>+10.3f}{tt:>7.2f}{bm:>+11.3f}"
              f"{tm:>7.2f}{bg:>+9.3f}{tg:>7.2f}")
    return out


def perm_p(d, state, lab):
    x = d[d["season"] <= DEV_MAX]
    y = (x["total"] - x["ot_close"]).values
    ctl = [x[c].values for c in rsk.CTRL]
    b, _ = ols_t(y, [x[state].values] + ctl)
    obs = b[1]
    yrs = x["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    v = x[state].values
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for bl in blocks:
            p[bl] = v[bl][RNG.permutation(len(bl))]
        bb, _ = ols_t(y, [p] + ctl)
        null[i] = bb[1]
    pv = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"    permutation ({lab}): observed {obs:+.4f}  null "
          f"{null.mean():+.4f} sd {null.std():.4f}  p={pv:.4f}")
    return pv


def main():
    d = build()
    print(f"  {len(d):,} games  seasons {sorted(d['season'].unique())}")
    for c in ("OUT_baseline_DEF", "OUT_late_DEF", "OUT_late_OFF"):
        print(f"    {c:20} nonzero on {int((d[c] > 0).sum()):,} games   "
              f"mean {d[c].mean():.4f}")

    print("\n" + "=" * 96)
    print("HYPOTHESIS A — role-specific absence and the CLOSING total")
    print("  gap = c_true - c_market;  A1 predicts gap > 0 for DEF_ANCHOR")
    print("=" * 96)
    gap_test(d, "OUT_baseline_DEF", "total", "ot_close",
             "A1  DEF_ANCHOR absences (closing total)")
    perm_p(d, "OUT_baseline_DEF", "A1 DEF")
    gap_test(d, "OUT_baseline_OFF", "total", "ot_close",
             "A2  OFF_STAR absences (closing total)  [expect gap ~ 0]")
    perm_p(d, "OUT_baseline_OFF", "A2 OFF")
    gap_test(d, "OUT_baseline_DEF", "total", "ot_open",
             "A3  FALSIFICATION: DEF_ANCHOR baseline vs the OPEN  [expect ~0]")

    print("\n" + "=" * 96)
    print("HYPOTHESIS B — intraday status change as a movement source")
    print("=" * 96)
    d["late_signed"] = (d["OUT_late_DEF"] + d["OUT_late_OFF"]
                        - d["UPGRADE_late_DEF"] - d["UPGRADE_late_OFF"])
    for wl, x in (("development", d[d["season"] <= DEV_MAX]),
                  ("holdout 2024-25", d[d["season"] == HOLD])):
        b1, t1 = ols_t(x["tmove"].values, [x["late_signed"].values])
        h = x.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"])
        if len(h) > 100:
            b2, t2 = ols_t(h["tmove"].values,
                           [h["MOVE_RIDGE_OOS"].values,
                            h["MOVE_LATENT_OOS"].values,
                            h["late_signed"].values])
            print(f"  {wl:18} B1 alone {b1[1]:+.4f} (t={t1[1]:+.2f})  n={len(x):,}"
                  f"   |  B2 JOINT: ridge {b2[1]:+.3f} (t={t2[1]:+.2f}) "
                  f"latent {b2[2]:+.3f} (t={t2[2]:+.2f}) "
                  f"LATE {b2[3]:+.4f} (t={t2[3]:+.2f})  n={len(h):,}")
        else:
            print(f"  {wl:18} B1 alone {b1[1]:+.4f} (t={t1[1]:+.2f})  "
                  f"n={len(x):,}   | joint: insufficient overlap")


if __name__ == "__main__":
    main()
