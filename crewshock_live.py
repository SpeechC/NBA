"""CREWSHOCK LIVE — daily log-only pipeline for 2026-27.

=============================================================================
 THIS PROGRAM PLACES NO BETS. There is no order-placement code anywhere in
 this file, and none is to be added. It writes a log. That is structural, not
 a configuration flag.
=============================================================================

The estimator is FROZEN (`CLOSING_REFEREE.md`). This module is a faithful
READ-ONLY port of `ref_features.matched_ref_effect`, extended only so it can
score games that have not been played yet. Nothing is re-estimated:

    k     = 78.247119   FROZEN, method-of-moments on development only.
                        NEVER re-estimated as new data arrives -- doing so
                        would let the shrinkage drift with the holdout.
    N     = 60          official's horizon
    MINN  = 25          minimum prior games before an official contributes
    THR   = 0.8682      frozen development Q85 action threshold

Daily inputs
    1  BigDataBall season-to-date CSV  -> pf_rate for COMPLETED games, which
       extends each official's rolling history. Verified to reproduce the
       advanced-stats sidecar exactly (max|diff| = 0.0).
    2  official.nba.com assignments API -> tonight's three officials.
       Published mid-morning; the close is at tip. That gap IS the edge.

Modes
    validate   reproduce ref_features.csv through the live code path
    daily      score tonight's slate, append to the log  (NO ORDERS)
    grade      settle logged rows once finals are in, append to the ledger
"""
import argparse
import datetime as dt
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---- FROZEN CONSTANTS. Do not modify. ---------------------------------------
K_FROZEN = 78.247119
N, MINN = 60, 25
SHORT, LONG = 200, 1230
THR = 0.8682
# -----------------------------------------------------------------------------

HIST = "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"
CURRENT = "/mnt/c/NBA2/dfMaster_2027.csv"          # BigDataBall season-to-date
LOG = "crewshock_live_log.csv"
LEDGER = "crewshock_live_ledger.csv"
ASSIGN_URL = "https://official.nba.com/wp-json/api/v1/get-game-officials?date={d}"

RU_H, RU_R = "REFEREE\n&\nUMPIRE_H", "REFEREE\n&\nUMPIRE_R"


def _norm_ref(s):
    return (s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
            .replace({"nan": np.nan, "": np.nan}))


def _canon(s):
    """Match key across sources. official.nba.com writes 'JT Orr' where
    BigDataBall writes 'J.T. Orr'; an unmatched name silently zeroes that
    official's entire 60-game history and understates CrewShock. Strip
    punctuation and case so the two resolve to one key."""
    return (pd.Series(s, dtype="object").astype(str)
            .str.replace(r"[.\-']", "", regex=True)
            .str.replace(r"\s+", " ", regex=True).str.strip().str.lower()
            .replace({"nan": np.nan, "": np.nan}))


def resolve_officials(slate, history):
    """Map assignment names onto the history's spelling. Returns (slate, gaps).

    An official who cannot be resolved contributes 0 to the crew sum, which
    biases CrewShock toward zero and can flip the action either way. Such
    games are flagged and are NEVER actioned.
    """
    key2name = {}
    for c in ("ref1", "ref2", "ref3"):
        for k, v in zip(_canon(history[c]), history[c]):
            if isinstance(k, str):
                key2name.setdefault(k, v)
    s = slate.copy()
    gaps = []
    for c in ("ref1", "ref2", "ref3"):
        ck = _canon(s[c])
        mapped = ck.map(key2name)
        unresolved = mapped.isna() & s[c].notna()
        for gid, nm in zip(s.loc[unresolved, "gid"], s.loc[unresolved, c]):
            gaps.append({"gid": gid, "slot": c, "name": nm})
        s[c] = mapped.where(~unresolved, s[c])
    s["data_gap"] = s.gid.isin({g["gid"] for g in gaps})
    return s, pd.DataFrame(gaps)


def load_history(paths=(HIST, CURRENT)):
    """Completed games: date, gid, pf_rate, ref1..3. Prior-only by nature."""
    frames = []
    for p in paths:
        if not os.path.exists(p):
            print(f"  [warn] {p} not found - skipping")
            continue
        raw = pd.read_csv(p, low_memory=False)
        # FROZEN universe filter, copied from refs.build(): "Regular Season"
        # ONLY (In-Season Tournament excluded), a closing total present and
        # inside [150,300], and finals present. Including playoffs or IST here
        # changes both the league cumulative and every official's history.
        from prepare_data import season_label
        raw = raw[season_label(raw).astype(str).str.contains(
            "Regular Season", na=False)].copy()
        _tot = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
        _act = (pd.to_numeric(raw["PTS_H"], errors="coerce")
                + pd.to_numeric(raw["PTS_R"], errors="coerce"))
        raw = raw[_tot.between(150, 300) & _act.notna()].copy()
        d = pd.DataFrame({
            "gid": raw["GAME-ID"].astype(str).str.strip(),
            "date": pd.to_datetime(raw["DATE"], errors="coerce"),
            "PF_H": pd.to_numeric(raw.get("PF_H"), errors="coerce"),
            "PF_R": pd.to_numeric(raw.get("PF_R"), errors="coerce"),
            "POSS_H": pd.to_numeric(raw.get("POSS_H"), errors="coerce"),
            "POSS_R": pd.to_numeric(raw.get("POSS_R"), errors="coerce")})
        # frozen refs.build() column logic, both layout eras
        d["ref1"] = _norm_ref(raw["MAIN REF_R"] if "MAIN REF_R" in raw
                              else raw["CREW CHIEF_R"])
        if "MAIN REF_R" in raw and "CREW CHIEF_R" in raw:
            d["ref1"] = _norm_ref(raw["MAIN REF_R"].fillna(raw["CREW CHIEF_R"]))
        d["ref2"] = _norm_ref(raw["CREW_R"].fillna(raw[RU_R])
                              if "CREW_R" in raw else raw[RU_R])
        d["ref3"] = _norm_ref(raw["CREW_H"].fillna(raw[RU_H])
                              if "CREW_H" in raw else raw[RU_H])
        frames.append(d)
    h = pd.concat(frames, ignore_index=True).drop_duplicates("gid", keep="last")
    h["pf_rate"] = 100 * h.PF_H / h.POSS_R + 100 * h.PF_R / h.POSS_H
    h = h.dropna(subset=["pf_rate", "date", "ref1", "ref2", "ref3"])
    return h.sort_values(["date", "gid"]).reset_index(drop=True)


def crewshock(history, pending=None, k=K_FROZEN):
    """FROZEN matched-horizon estimator. `pending` rows carry no pf_rate.

    Faithful to ref_features.matched_ref_effect. The one extension: the league
    cumulative is built from COMPLETED games only, so appending unplayed rows
    cannot alter any historical value. Every window is shift(1)-based, so a
    pending game's own (missing) foul count never enters its own estimate.
    """
    hist = history.copy()
    hist["_pending"] = False
    if pending is not None and len(pending):
        p = pending.copy()
        p["_pending"] = True
        p["pf_rate"] = np.nan
        d = pd.concat([hist, p], ignore_index=True)
    else:
        d = hist
    d = d.sort_values(["date", "gid"], kind="stable").reset_index(drop=True)

    comp = d[~d._pending]
    sd = comp["date"].values.astype("datetime64[ns]").astype(np.int64)
    o = np.argsort(sd, kind="stable")
    sd = sd[o]
    cum = np.concatenate([[0.0], np.cumsum(comp["pf_rate"].values[o])])

    dates = d["date"].values.astype("datetime64[ns]").astype(np.int64)
    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "slot": i, "date": dates,
                      "ref": d[f"ref{i}"].values, "pf": d["pf_rate"].values})
        for i in (1, 2, 3)])
    long = long.sort_values(["ref", "date"], kind="stable").reset_index(drop=True)
    g = long.groupby("ref", sort=False)
    p_ = g["pf"].shift(1)
    long["rm"] = p_.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).mean())
    long["rn"] = p_.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).count())
    dprev = g["date"].shift(1)
    long["d_end"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).max())
    long["d_start"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).min())

    ok = long["rn"].notna() & long["d_start"].notna()
    j1 = np.searchsorted(sd, long.loc[ok, "d_start"].values, side="left")
    j2 = np.searchsorted(sd, long.loc[ok, "d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["lg_matched"] = np.nan
    long.loc[ok, "lg_matched"] = (cum[j2] - cum[j1]) / cnt
    long["eff"] = ((long["rm"] - long["lg_matched"])
                   * long["rn"] / (long["rn"] + k)).fillna(0.0)
    agg = long.groupby("row").agg(CrewShock=("eff", "sum"), min_prior=("rn", "min"))
    d["CrewShock"] = agg["CrewShock"].reindex(np.arange(len(d))).values
    d["min_prior"] = agg["min_prior"].reindex(np.arange(len(d))).values
    return d


def fetch_assignments(day):
    """official.nba.com. NOTE the working format is YYYY-MM-DD; MM-DD-YYYY
    silently returns zero rows, which would look like 'no games' rather than
    an error. The row-count gate below turns that into a loud failure."""
    from curl_cffi import requests as rq
    r = rq.get(ASSIGN_URL.format(d=day), impersonate="chrome", timeout=30)
    rows = r.json().get("nba", {}).get("Table", {}).get("rows", [])
    if not rows:
        return pd.DataFrame()
    a = pd.DataFrame(rows)
    out = pd.DataFrame({
        "gid": a.game_id.astype(str).str.lstrip("0"),
        "date": pd.to_datetime(a.game_date, format="%m/%d/%Y"),
        "home": a.home_team_abbr, "away": a.away_team_abbr,
        "ref1": _norm_ref(a.official1), "ref2": _norm_ref(a.official2),
        "ref3": _norm_ref(a.official3)})
    return out.dropna(subset=["ref1", "ref2", "ref3"])


def cmd_validate():
    """Does the live code path reproduce the frozen artifact exactly?"""
    h = load_history((HIST,))
    print(f"  history {len(h):,} completed games "
          f"{h.date.min().date()} -> {h.date.max().date()}")
    out = crewshock(h)
    frozen = pd.read_csv("ref_features.csv")
    frozen["gid"] = frozen.gid.astype(str).str.strip()
    j = out[["gid", "CrewShock"]].merge(
        frozen[["gid", "CrewShock"]].rename(columns={"CrewShock": "frozen"}),
        on="gid")
    diff = (j.CrewShock - j.frozen).abs()
    print(f"\n  VALIDATION 1 - full reproduction of ref_features.csv")
    print(f"    overlap {len(j):,}   max|diff| {diff.max():.3e}   "
          f"mean|diff| {diff.mean():.3e}   corr {j.CrewShock.corr(j.frozen):.10f}")
    ok1 = diff.max() < 1e-6
    print(f"    {'PASS' if ok1 else 'FAIL'}")

    # pending path: hide the last slate's fouls, score it as if unplayed
    last = h.date.max()
    played = h[h.date < last]
    slate = h[h.date == last][["gid", "date", "ref1", "ref2", "ref3"]]
    pend = crewshock(played, pending=slate)
    pend = pend[pend._pending][["gid", "CrewShock"]]
    j2 = pend.merge(frozen[["gid", "CrewShock"]].rename(
        columns={"CrewShock": "frozen"}), on="gid")
    d2 = (j2.CrewShock - j2.frozen).abs()
    print(f"\n  VALIDATION 2 - PENDING path on {last.date()} "
          f"({len(j2)} games scored with fouls withheld)")
    print(f"    max|diff| {d2.max():.3e}   mean|diff| {d2.mean():.3e}")
    ok2 = d2.max() < 1e-6
    print(f"    {'PASS' if ok2 else 'FAIL'}")
    print(f"\n  OVERALL: {'PASS - live path is faithful' if ok1 and ok2 else 'FAIL'}")
    return ok1 and ok2


def cmd_daily(day, lines_csv=""):
    h = load_history()
    slate = fetch_assignments(day)
    if slate.empty:
        print(f"  no assignments published for {day} (yet)")
        return
    slate, gaps = resolve_officials(slate, h)
    if len(gaps):
        print(f"  *** {len(gaps)} UNRESOLVED OFFICIAL(S) - those games are "
              f"flagged DATA_GAP and will NOT be actioned ***")
        for _, g in gaps.iterrows():
            print(f"      {g.gid}  {g.slot}  {g['name']!r}")
    print(f"  slate {len(slate)} games; history {len(h):,} completed")
    out = crewshock(h, pending=slate)
    rec = out[out._pending].copy()
    # a data gap biases CrewShock toward zero and can flip the call either way
    rec["fires"] = (rec.CrewShock >= THR) & (~rec.data_gap.astype(bool))
    rec["action"] = np.where(rec.data_gap.astype(bool), "DATA_GAP",
                             np.where(rec.fires, "LOG_OVER", "no_action"))
    rec["asof"] = dt.datetime.now().isoformat(timespec="seconds")
    if lines_csv and os.path.exists(lines_csv):
        ln = pd.read_csv(lines_csv)
        ln["gid"] = ln.gid.astype(str).str.strip()
        rec = rec.merge(ln[["gid", "total"]].rename(
            columns={"total": "total_at_log"}), on="gid", how="left")
    cols = ["asof", "gid", "date", "home", "away", "ref1", "ref2", "ref3",
            "CrewShock", "min_prior", "data_gap", "fires", "action"]
    cols += [c for c in ("total_at_log",) if c in rec.columns]
    rec = rec[cols].sort_values("CrewShock", ascending=False)
    print(f"\n  {'gid':>10} {'matchup':<10} {'CrewShock':>10} {'minN':>5}  action")
    for _, r in rec.iterrows():
        print(f"  {r.gid:>10} {r.away}@{r.home:<6} {r.CrewShock:>10.4f} "
              f"{r.min_prior:>5.0f}  {r.action}")
    print(f"\n  {int(rec.fires.sum())} of {len(rec)} fire at CrewShock >= {THR}")
    hdr = not os.path.exists(LOG)
    rec.to_csv(LOG, mode="a", header=hdr, index=False)
    print(f"  appended to {LOG}   *** LOG ONLY - NO ORDER WAS PLACED ***")


def cmd_grade(results_csv):
    """Settle logged rows. results_csv: gid,closing_total,actual_total."""
    if not os.path.exists(LOG):
        print("  no log yet"); return
    log = pd.read_csv(LOG)
    log["gid"] = log.gid.astype(str).str.strip()
    res = pd.read_csv(results_csv)
    res["gid"] = res.gid.astype(str).str.strip()
    j = log[log.fires].merge(res, on="gid", how="inner").dropna(
        subset=["closing_total", "actual_total"])
    if j.empty:
        print("  nothing to grade yet"); return
    j["result"] = np.sign(j.actual_total - j.closing_total)
    live = j[j.result != 0]
    w, l = int((live.result > 0).sum()), int((live.result < 0).sum())
    prof = w * (100 / 1.1) - l * 100
    n = w + l
    print(f"  graded {n} bets (pushes {len(j)-n}):  {w}-{l}  "
          f"hit {100*w/n:.2f}%   P&L {prof:+,.0f}   ROI {100*prof/(n*100):+.2f}%")
    hdr = not os.path.exists(LEDGER)
    j.to_csv(LEDGER, mode="a", header=hdr, index=False)
    print(f"  appended to {LEDGER}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["validate", "daily", "grade"])
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--lines", default="")
    ap.add_argument("--results", default="")
    a = ap.parse_args()
    if a.mode == "validate":
        cmd_validate()
    elif a.mode == "daily":
        cmd_daily(a.date, a.lines)
    else:
        cmd_grade(a.results)
