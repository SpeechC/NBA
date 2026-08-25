"""
===============================================================================
 HALFTIME STRATEGY — ECONOMIC AUDIT (what is the money, after the timing fix)
===============================================================================
 Companion to wnba_anchor_audit.py and nba_anchor_audit.py, which established
 the TIMING. This establishes the MONEY.

Re-runs the economic tail for BOTH leagues at BOTH the published (biased) and
corrected decision times, through one identical pipeline:

  * walk-forward: the efficient rule (a + b*pre + c*H1) and its residual CDF
    are fit ONLY on games strictly earlier than the one being traded
  * real ladder quotes at the decision bar; buy YES at the ask, NO at 1-bid
  * Kalshi taker fee 0.07*p*(1-p) on entry, held to settlement
  * YES pays iff realized total > strike (verified rule)
  * OT games INCLUDED (excluding them conditions on an outcome you cannot
    know at bet time)

Reports per-contract P&L in dollars and ROI on capital actually deployed.
"""
import os, pickle, sqlite3, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/dpope/projects/nba_entropy_replication")
import wnba_anchor_audit as A, wnba_reconcile as R
from prepare_data import CSV, season_label

THRESH = (0.03, 0.05, 0.08)
MIN_TRAIN = 80


def fee(p):
    return 0.07 * p * (1 - p)


def ladders(db, evts):
    """-> {event: {ts: DataFrame[k,bid,ask]}} in probability units."""
    con = sqlite3.connect(db)
    q = ("select event_ticker e, end_period_ts t, strike_label k, "
         "yes_bid_close b, yes_ask_close a from candles where "
         "period_interval=1 and strike_label is not null")
    df = pd.read_sql(q, con); con.close()
    df = df[df.e.isin(evts)].dropna(subset=["b", "a"])
    df["bid"] = df.b / 100.0; df["ask"] = df.a / 100.0
    return {e: {t: g[["k", "bid", "ask"]] for t, g in ge.groupby("t")}
            for e, ge in df.groupby("e")}


def nearest(book, ts, tol=240):
    if not book: return None
    ks = np.array(sorted(book))
    i = np.abs(ks - ts).argmin()
    return book[ks[i]] if abs(ks[i] - ts) <= tol else None


def simulate(games, lad, label):
    """games: DataFrame[event, date, pre, h1, total, dts] sorted by date."""
    out = []
    g = games.sort_values("date").reset_index(drop=True)
    for i in range(len(g)):
        if i < MIN_TRAIN: continue
        tr = g.iloc[:i]
        X = np.column_stack([np.ones(len(tr)), tr.pre.values, tr.h1.values])
        beta, *_ = np.linalg.lstsq(X, tr.total.values, rcond=None)
        resid = np.sort(tr.total.values - X @ beta)
        row = g.iloc[i]
        book = nearest(lad.get(row.event, {}), row.dts)
        if book is None or not len(book): continue
        E = beta[0] + beta[1] * row.pre + beta[2] * row.h1
        for _, r in book.iterrows():
            K, bid, ask = float(r.k), float(r.bid), float(r.ask)
            if not (0 < bid < 1 and 0 < ask < 1 and ask >= bid): continue
            pt = 1.0 - np.searchsorted(resid, K - E, side="right") / len(resid)
            eY = pt - ask - fee(ask)
            eN = bid - pt - fee(bid)
            for side, edge, cost in (("YES", eY, ask + fee(ask)),
                                     ("NO", eN, (1 - bid) + fee(bid))):
                if edge <= 0: continue
                win = (row.total > K) if side == "YES" else (row.total <= K)
                out.append({"event": row.event, "date": row.date, "K": K,
                            "side": side, "edge": edge, "cost": cost,
                            "win": win, "pnl": (1.0 - cost) if win else -cost})
    d = pd.DataFrame(out)
    print(f"\n=== {label}   ({g.event.nunique()} games, "
          f"{max(0,len(g)-MIN_TRAIN)} tradeable after walk-forward warmup)")
    if not len(d):
        print("    no positive-edge quotes at all"); return d
    for mode in ("best rung/game", "all qualifying rungs"):
        print(f"  -- {mode}")
        print(f"     {'min edge':>9} {'trades':>7} {'hit':>6} {'$ P&L':>9} "
              f"{'$ staked':>9} {'ROI':>8}")
        for th in THRESH:
            s = d[d.edge >= th]
            if mode == "best rung/game" and len(s):
                s = s.loc[s.groupby("event").edge.idxmax()]
            if not len(s):
                print(f"     {th:>8.0%} {0:>7}      -         -         -        -")
                continue
            pnl, cost = s.pnl.sum(), s.cost.sum()
            print(f"     {th:>8.0%} {len(s):>7} {s.win.mean():>5.0%} "
                  f"{pnl:>+9.2f} {cost:>9.2f} {pnl/cost:>+8.1%}")
    return d


# ---------------- NBA ----------------
CODE = {"Atlanta":"ATL","Boston":"BOS","Brooklyn":"BKN","Charlotte":"CHA","Chicago":"CHI",
 "Cleveland":"CLE","Dallas":"DAL","Denver":"DEN","Detroit":"DET","Golden State":"GSW",
 "Houston":"HOU","Indiana":"IND","LA Clippers":"LAC","Los Angeles Clippers":"LAC",
 "LA Lakers":"LAL","Los Angeles Lakers":"LAL","Los Angeles":"LAL","Memphis":"MEM",
 "Miami":"MIA","Milwaukee":"MIL","Minnesota":"MIN","New Orleans":"NOP","New York":"NYK",
 "Oklahoma City":"OKC","Orlando":"ORL","Philadelphia":"PHI","Phoenix":"PHX","Portland":"POR",
 "Sacramento":"SAC","San Antonio":"SAS","Toronto":"TOR","Utah":"UTA","Washington":"WAS"}
NBA_C = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_candles.sqlite"
con = sqlite3.connect(NBA_C)
meta = pd.read_sql("select distinct event_ticker e, away_team, home_team, game_date from markets", con)
con.close()
raw = pd.read_csv(CSV, low_memory=False); raw["season"] = season_label(raw).astype(str)
m = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
m["date"] = pd.to_datetime(m["DATE"], errors="coerce")
m = m[(m.date >= "2025-10-20") & (m.date <= "2025-12-23")].copy()
for c in ("1Q_H","2Q_H","1Q_R","2Q_R","PTS_H","PTS_R","CLOSING TOTAL_H"):
    m[c] = pd.to_numeric(m[c], errors="coerce")
m["h1"] = m["1Q_H"]+m["2Q_H"]+m["1Q_R"]+m["2Q_R"]; m["total"] = m["PTS_H"]+m["PTS_R"]
m["pre"] = m["CLOSING TOTAL_H"]
meta["key"] = meta.game_date.astype(str)+"|"+meta.away_team+"@"+meta.home_team
m["event"] = (m.date.dt.strftime("%Y-%m-%d")+"|"+m["TEAM_R"].map(CODE)+"@"+m["TEAM_H"].map(CODE)).map(dict(zip(meta.key, meta.e)))
con = sqlite3.connect("/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite.bak-20260823")
tp = pd.read_sql("select distinct event_ticker e, tipoff_ts from markets where tipoff_ts is not null", con); con.close()
m["T"] = m.event.map(dict(zip(tp.e, tp.tipoff_ts)))
m = m.dropna(subset=["event","T","h1","total","pre"])
nba_lad = ladders(NBA_C, set(m.event))
print(f"[nba] {len(m)} games, ladders for {len(nba_lad)} events")
for off, lab in ((70, "NBA  PUBLISHED  T+70 (biased ~10min early)"),
                 (84, "NBA  CORRECTED  T+84 (audit peak)")):
    mm = m.copy(); mm["dts"] = mm["T"] + off*60
    simulate(mm[["event","date","pre","h1","total","dts"]], nba_lad, lab)

# ---------------- WNBA ----------------
WN_C = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
CACHE_W = "/tmp/claude-1000/wnba_L.pkl"
if os.path.exists(CACHE_W):
    ser = pickle.load(open(CACHE_W, "rb"))
else:
    ser = A.build_L_series(WN_C)
    os.makedirs(os.path.dirname(CACHE_W), exist_ok=True)
    pickle.dump(ser, open(CACHE_W, "wb"))
bref = R.bref_totals(R.BREF); panel = pd.read_csv(A.PANEL)
pre_by = dict(zip(panel.event_ticker, panel.L_pre))
rows = []
for e, s in ser.items():
    hit = R.bref_lookup(e, bref)
    if not hit or e not in pre_by: continue
    total, h1, n_ot = hit
    a1 = A.convergence_anchor(s, total)
    bad = np.where((s.L-total).abs().values > 2.5)[0]
    a2 = int(s.ts.values[bad[-1]+1]) if len(bad) and bad[-1]+1 < len(s) else None
    if a1 is None or a2 is None: continue
    rows.append({"event": e, "date": R.event_date(e), "pre": pre_by[e],
                 "h1": h1, "total": total, "a1": a1, "a2": a2})
w = pd.DataFrame(rows)
wn_lad = ladders(WN_C, set(w.event))
print(f"\n[wnba] {len(w)} games (OT included), ladders for {len(wn_lad)} events")
for col, off, lab in (("a1", 58, "WNBA PUBLISHED convergence anchor -58 (samples pregame)"),
                      ("a2", 58, "WNBA CORRECTED settled anchor -58")):
    ww = w.copy(); ww["dts"] = ww[col] - off*60
    simulate(ww[["event","date","pre","h1","total","dts"]], wn_lad, lab)
