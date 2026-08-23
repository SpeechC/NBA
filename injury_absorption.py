"""PREREG_injury_absorption.md -- the SINGLE absorption estimate.

Reconstructs an implied total line L(t) each minute from the Kalshi rung
ladder, then measures around each late-OUT report:

    JUMP     = L_0 - L_pre     response already gone before you can act
    RESIDUAL = L_k - L_0       the only economically available quantity
                               k in {1,2,4,8} hours

against a same-date no-event control arm. Horizons whose target falls at or
after tipoff are DROPPED, not clipped.

kalshi_nba_totals.sqlite is opened READ-ONLY (it holds tipoff_ts, which the
fetcher would null out; see PREREG_move_injury_combined.md section 9).
"""
import sqlite3
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from injury_market import norm_name

CAND = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_candles.sqlite"
CURATED = "file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro"
PANEL = "injury_status_panel.csv"
PBP = "/home/dpope/data/pbp_lineups_all.parquet"
W0, W1 = "2025-10-21", "2025-12-22"
HORIZONS = [1, 2, 4, 8]
TOL = pd.Timedelta(minutes=15)

PRIOR_SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid, GAMEDATE AS d,
         PLAYER1_ID AS pid, PLAYER1_NAME AS pname,
         PLAYER1_TEAM_ABBREVIATION AS abbr
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE='RegularSeason' AND PLAYER1_ID>0 AND PLAYER1_NAME IS NOT NULL
    AND CAST(GAMEDATE AS VARCHAR) BETWEEN '2024-10-01' AND '2025-07-01'
)
SELECT gid, any_value(d) AS d, pid, any_value(pname) AS pname,
       any_value(abbr) AS abbr, count(*) AS events
FROM ev GROUP BY gid, pid
"""


def implied_lines():
    """L(t) per (event_ticker, minute): the 0.5 crossing of the survival curve."""
    cc = sqlite3.connect(CAND)
    k = pd.read_sql(
        "SELECT ticker,event_ticker,end_period_ts,yes_bid_close,yes_ask_close "
        "FROM candles", cc)
    ct = sqlite3.connect(CURATED, uri=True)
    mk = pd.read_sql("SELECT ticker,floor_strike,tipoff_ts FROM markets", ct)
    k = k.merge(mk, on="ticker", how="left")
    for c in ("end_period_ts", "yes_bid_close", "yes_ask_close",
              "floor_strike", "tipoff_ts"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k = k[(k.yes_bid_close > 0) & (k.yes_ask_close > 0)
          & k.floor_strike.notna()]
    k["p"] = (k.yes_bid_close + k.yes_ask_close) / 200.0   # cents -> prob
    # average duplicate strikes, then sort
    g = k.groupby(["event_ticker", "end_period_ts", "floor_strike"],
                  as_index=False).agg(p=("p", "mean"))
    g = g.sort_values(["event_ticker", "end_period_ts", "floor_strike"])

    out = []
    for (ev, ts), s in g.groupby(["event_ticker", "end_period_ts"], sort=False):
        if len(s) < 4:
            continue
        x = s.floor_strike.values
        y = s.p.values                     # P(total > strike), decreasing
        above = np.where(y >= 0.5)[0]
        below = np.where(y < 0.5)[0]
        if not len(above) or not len(below):
            continue                        # crossing not bracketed
        i = above[-1]
        j = below[below > i]
        if not len(j):
            continue
        j = j[0]
        y0, y1 = y[i], y[j]
        L = x[i] if y0 == y1 else x[i] + (x[j] - x[i]) * (y0 - 0.5) / (y0 - y1)
        out.append((ev, ts, L))
    L = pd.DataFrame(out, columns=["event_ticker", "ts", "L"])
    L["t"] = pd.to_datetime(L.ts, unit="s")
    tip = k.groupby("event_ticker")["tipoff_ts"].median()
    L["tip"] = pd.to_datetime(L.event_ticker.map(tip), unit="s")
    return L.sort_values("t")


def events():
    """Per-game first OUT_late time and carryover treatment weight."""
    P = pd.read_csv(PANEL, parse_dates=["report_ts", "game_date"])
    P = P[(P.game_date >= W0) & (P.game_date <= W1)].copy()
    P["key"] = P.player.map(norm_name)
    P["d"] = P.game_date.dt.strftime("%Y-%m-%d")
    P["gk"] = P.d + "|" + P.matchup
    gg = P.groupby("gk")["report_ts"]
    P["f"] = gg.transform("min")
    P["l"] = gg.transform("max")
    first = P[P.report_ts == P.f][["gk", "key", "status"]].rename(
        columns={"status": "s0"}).drop_duplicates(["gk", "key"])
    last = P[P.report_ts == P.l][["gk", "key", "status"]].rename(
        columns={"status": "s1"}).drop_duplicates(["gk", "key"])
    S = last.merge(first, on=["gk", "key"], how="left")
    S["out_late"] = S.s0.ne("Out") & S.s1.eq("Out")
    lateset = set(map(tuple, S.loc[S.out_late, ["gk", "key"]].values))

    # prior-season (2024-25) carryover MIN_SHARE  -- see prereg s4 amendment
    M = duckdb.connect().execute(PRIOR_SQL).fetchdf()
    M["key"] = M.pname.map(norm_name)
    M["tot"] = M.groupby(["gid", "abbr"])["events"].transform("sum")
    M["share"] = M.events / M.tot
    M = M.sort_values("d")
    w = M.groupby("key")["share"].apply(lambda s: s.tail(20).mean())

    # first minute at which any OUT_late player is listed Out
    O = P[P.status == "Out"].copy()
    O["is_late"] = [(a, b) in lateset for a, b in zip(O.gk, O.key)]
    O = O[O.is_late]
    t0 = O.groupby("gk")["report_ts"].min().rename("t0")
    wt = O.assign(w=O.key.map(w).fillna(0.0)).groupby("gk")["w"].sum()
    E = pd.concat([t0, wt.rename("weight")], axis=1).reset_index()
    E["d"] = E.gk.str.split("|").str[0]
    E["matchup"] = E.gk.str.split("|").str[1]
    allg = P[["d", "matchup"]].drop_duplicates()
    allg["gk"] = allg.d + "|" + allg.matchup
    allg["treated"] = allg.gk.isin(set(E.gk))
    return E, allg


def measure(L, ev_ticker, t0, tip):
    s = L[L.event_ticker == ev_ticker]
    if s.empty:
        return None
    pre = s[s.t < t0]
    post = s[s.t >= t0]
    if pre.empty or post.empty:
        return None
    L_pre, L_0 = pre.L.iloc[-1], post.L.iloc[0]
    t_entry = post.t.iloc[0]
    row = {"L_pre": L_pre, "L_0": L_0, "jump": L_0 - L_pre}
    for h in HORIZONS:
        tgt = t0 + pd.Timedelta(hours=h)
        if pd.notna(tip) and tgt >= tip:
            row[f"r{h}"] = np.nan            # censored at tipoff, dropped
            continue
        c = s[(s.t - tgt).abs() <= TOL]
        row[f"r{h}"] = (c.iloc[(c.t - tgt).abs().argsort()].L.iloc[0] - L_0
                        if len(c) and t_entry < tgt else np.nan)
    return row


def main():
    L = implied_lines()
    print(f"  implied lines: {len(L):,} minute-observations over "
          f"{L.event_ticker.nunique():,} games")
    E, allg = events()
    print(f"  games in window: {len(allg):,}   treated (>=1 OUT_late): "
          f"{int(allg.treated.sum()):,}   controls: {int((~allg.treated).sum()):,}")
    print(f"  treatment weight: mean {E.weight.mean():.4f}  "
          f"median {E.weight.median():.4f}  zero on {int((E.weight==0).sum())}")

    ct = sqlite3.connect(CURATED, uri=True)
    ev = pd.read_sql("SELECT event_ticker,game_date,home_team,away_team "
                     "FROM events", ct)
    ev["gk"] = ev.game_date + "|" + ev.away_team + "@" + ev.home_team
    tipmap = L.groupby("event_ticker")["tip"].first()

    rows = []
    # treated
    for _, r in E.iterrows():
        m = ev[ev.gk == r.gk]
        if m.empty:
            continue
        et = m.event_ticker.iloc[0]
        res = measure(L, et, r.t0, tipmap.get(et, pd.NaT))
        if res:
            rows.append({**res, "arm": "treated", "gk": r.gk, "d": r.d,
                         "t0": r.t0, "weight": r.weight})
    # controls: same date, no event, same pseudo-t0 clock time
    treated_t0 = E.set_index("gk")["t0"].to_dict()
    for _, r in allg[~allg.treated].iterrows():
        same = E[E.d == r.d]
        if same.empty:
            continue
        t0 = same.t0.iloc[0]
        t0 = pd.Timestamp(r.d) + (t0 - t0.normalize())
        m = ev[ev.gk == r.gk]
        if m.empty:
            continue
        et = m.event_ticker.iloc[0]
        res = measure(L, et, t0, tipmap.get(et, pd.NaT))
        if res:
            rows.append({**res, "arm": "control", "gk": r.gk, "d": r.d,
                         "t0": t0, "weight": 0.0})
    D = pd.DataFrame(rows)
    print(f"  measured: {len(D):,} games  "
          f"({int((D.arm=='treated').sum())} treated, "
          f"{int((D.arm=='control').sum())} control)")

    print("\n" + "=" * 88)
    print("ABSORPTION OF LATE-OUT INFORMATION  (points of total; negative = down)")
    print("=" * 88)
    T, C = D[D.arm == "treated"], D[D.arm == "control"]
    print(f"\n  JUMP  (L_0 - L_pre, the part gone before you can act)")
    print(f"    treated {T.jump.mean():+.3f}  (n={T.jump.notna().sum():,})   "
          f"control {C.jump.mean():+.3f}  (n={C.jump.notna().sum():,})")
    dj = T.jump.mean() - C.jump.mean()
    sj = np.sqrt(T.jump.var()/T.jump.notna().sum()
                 + C.jump.var()/max(C.jump.notna().sum(), 1))
    print(f"    difference {dj:+.3f}  (t={dj/sj if sj else np.nan:+.2f})")

    print(f"\n  RESIDUAL (L_k - L_0, the only capturable part)")
    print(f"    {'k':>4}{'treated':>10}{'n_t':>7}{'control':>10}{'n_c':>7}"
          f"{'diff':>9}{'t':>7}{'>=1.0pt?':>10}")
    for h in HORIZONS:
        a, b = T[f"r{h}"].dropna(), C[f"r{h}"].dropna()
        if len(a) < 5 or len(b) < 5:
            print(f"    {h:>4}{'--':>10}{len(a):>7}{'--':>10}{len(b):>7}"
                  f"{'insufficient':>19}")
            continue
        d = a.mean() - b.mean()
        se = np.sqrt(a.var()/len(a) + b.var()/len(b))
        print(f"    {h:>4}{a.mean():>+10.3f}{len(a):>7}{b.mean():>+10.3f}"
              f"{len(b):>7}{d:>+9.3f}{d/se if se else np.nan:>7.2f}"
              f"{'YES' if abs(d) >= 1.0 else 'no':>10}")

    print(f"\n  MONOTONICITY in the carryover weight (treated only; "
          f"prereg s4 amendment applies)")
    for h in HORIZONS:
        a = T[[f"r{h}", "weight"]].dropna()
        if len(a) < 10:
            print(f"    k={h}: n={len(a)} too few"); continue
        x = np.column_stack([np.ones(len(a)), a.weight.values])
        b, *_ = np.linalg.lstsq(x, a[f"r{h}"].values, rcond=None)
        r = a[f"r{h}"].values - x @ b
        se = np.sqrt(np.diag(np.linalg.pinv(x.T @ x)) * (r @ r) / (len(a)-2))
        print(f"    k={h}: slope {b[1]:+.3f} (t={b[1]/se[1]:+.2f})  n={len(a)}")
    D.to_csv("injury_absorption_rows.csv", index=False)


if __name__ == "__main__":
    main()
