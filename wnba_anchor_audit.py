"""
===============================================================================
 WNBA HALFTIME FINDING — ADVERSARIAL AUDIT OF THE CONVERGENCE ANCHOR
===============================================================================
 PREREG_wnba_halftime.md locates halftime WITHOUT a tip time: it finds game
 end as the first run of 5 bars where the ladder's implied line L sits within
 2.5 points of the realized total, then takes halftime = end - 58 minutes.

 That offset is a free parameter, and everything rests on it. A WNBA game runs
 roughly 2 hours, so end-58 is meant to land inside the halftime break. But
 real-time game duration varies by 15+ minutes, and if the anchor lands BEFORE
 the second-quarter buzzer then L has not yet seen all of H1 while the
 regressor H1 is the true box-score value. That mechanically drives s below 1
 in a perfectly efficient market — the exact shape the paper reports.

 This script does not assume that is happening. It measures it:
   A. reproduce s at the published offset (fidelity check on this rebuild)
   B. sweep the offset and plot s(offset) — a real market property should be
      flat across the plausible break window, an artifact should be monotone
   C. split H1 into Q1 and Q2 — if the anchor lands mid-Q2 the market cannot
      have seen Q2, so Q2 must load strictly less than Q1
   D. quantify duration dispersion, which sets how often the anchor misses

 Read-only. Writes nothing but its own printed report.
===============================================================================
"""
import datetime as dt
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_reconcile as R                                   # noqa: E402

DB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
PANEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "wnba_halftime_rows.csv")
PUB_OFFSET = 58          # minutes back from the convergence anchor
CONV_TOL = 2.5           # |L - total| tolerance defining "converged"
CONV_RUN = 5             # consecutive bars required


def median_cross(strikes, probs):
    """Implied line at the 0.5 crossing; needs >=4 two-sided bracketed rungs."""
    q = sorted((float(k), float(p)) for k, p in zip(strikes, probs)
               if p is not None and np.isfinite(p))
    if len(q) < 4:
        return np.nan
    xs = [a for a, _ in q]
    ps = [b for _, b in q]
    ab = [i for i, p in enumerate(ps) if p >= 0.5]
    bl = [i for i, p in enumerate(ps) if p < 0.5]
    if not ab or not bl or max(ab) > min(bl):
        return np.nan
    i, j = max(ab), min(bl)
    if ps[i] == ps[j]:
        return xs[i]
    return xs[i] + (xs[j] - xs[i]) * (ps[i] - 0.5) / (ps[i] - ps[j])


def build_L_series(db_path):
    """-> {event: DataFrame[ts, L]} at 1-minute resolution."""
    con = sqlite3.connect(db_path)
    df = pd.read_sql(
        "select event_ticker, end_period_ts, strike_label, "
        "yes_bid_close, yes_ask_close from candles "
        "where period_interval = 1 and strike_label is not null", con)
    con.close()
    df["mid"] = (df.yes_bid_close + df.yes_ask_close) / 200.0   # cents -> prob
    df = df.dropna(subset=["mid"])
    out = {}
    for evt, g in df.groupby("event_ticker"):
        rows = []
        for ts, gg in g.groupby("end_period_ts"):
            L = median_cross(gg.strike_label.values, gg.mid.values)
            if np.isfinite(L):
                rows.append((ts, L))
        if len(rows) > 30:
            out[evt] = pd.DataFrame(rows, columns=["ts", "L"]).sort_values("ts")
    return out


def convergence_anchor(s, total, tol=CONV_TOL, run=CONV_RUN):
    """First ts beginning a run of `run` bars with |L - total| <= tol."""
    ok = (s.L - total).abs().le(tol).values
    if len(ok) < run:
        return None
    for i in range(len(ok) - run + 1):
        if ok[i:i + run].all():
            return int(s.ts.values[i])
    return None


def L_at(s, ts_target, tol_min=3):
    """L at the bar nearest ts_target, within tol_min minutes."""
    d = (s.ts - ts_target).abs()
    if d.min() > tol_min * 60:
        return np.nan
    return float(s.L.values[int(d.values.argmin())])


def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    s2 = (resid @ resid) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return dict(zip(["const"] + names, beta)), dict(zip(["const"] + names, se))


def main():
    print(__doc__.split("===\n")[1].strip()[:0] or "", end="")
    print("[audit] building L(t) from 1-minute candles ...")
    series = build_L_series(DB)
    print(f"  {len(series)} event(s) with a usable ladder series")

    bref = R.bref_totals(R.BREF)
    panel = pd.read_csv(PANEL)
    pre_by_evt = dict(zip(panel.event_ticker, panel.L_pre))
    print(f"  panel supplies L_pre for {len(pre_by_evt)} event(s)")

    rows = []
    for evt, s in series.items():
        hit = R.bref_lookup(evt, bref)
        if not hit:
            continue
        total, h1, n_ot = hit
        if n_ot:                       # prereg: non-OT games only
            continue
        end_ts = convergence_anchor(s, total)
        if end_ts is None:
            continue
        pre = pre_by_evt.get(evt)
        if pre is None or not np.isfinite(pre):
            continue
        rec = {"event": evt, "total": total, "h1": h1, "pre": pre,
               "end_ts": end_ts,
               "span_min": (s.ts.max() - s.ts.min()) / 60.0,
               "active_min": (end_ts - s.ts.min()) / 60.0}
        for off in range(30, 101, 2):
            rec[f"L{off}"] = L_at(s, end_ts - off * 60)
        rows.append(rec)

    d = pd.DataFrame(rows)
    print(f"  {len(d)} non-OT game(s) with an anchor and a pregame L\n")

    # ---- A. fidelity: reproduce the published offset ----------------------
    c = d.dropna(subset=[f"L{PUB_OFFSET}", "pre", "h1"])
    b, se = ols(c[f"L{PUB_OFFSET}"].values, [c.pre.values, c.h1.values],
                ["pre", "h1"])
    print("A. REBUILD AT THE PUBLISHED OFFSET (end - 58 min)")
    print(f"   L_half = {b['const']:+.2f} {b['pre']:+.3f}*pre "
          f"{b['h1']:+.3f}*H1     n={len(c)}")
    print(f"   s(H1) = {b['h1']:.3f}  se {se['h1']:.3f}   "
          f"(s-1)/se = {(b['h1'] - 1) / se['h1']:.1f}")
    br, ser = ols(c.total.values, [c.pre.values, c.h1.values], ["pre", "h1"])
    print(f"   realized benchmark s' = {br['h1']:.3f} (se {ser['h1']:.3f})"
          f"  <- the efficient value H1 should carry")
    print("   [paper: s = 0.276, se 0.051, s' = 0.940 on n=79]\n")

    # ---- B. the offset sweep ---------------------------------------------
    print("B. OFFSET SWEEP — is s a property of the market, or of the offset?")
    print("   a real inefficiency is FLAT across the plausible break window;")
    print("   an artifact of sampling too early rises monotonically with it.\n")
    print(f"   {'offset':>7} {'n':>5} {'s(H1)':>8} {'se':>7} {'b(pre)':>8} "
          f"{'resid sd':>9}")
    sweep = []
    for off in range(30, 101, 2):
        cc = d.dropna(subset=[f"L{off}", "pre", "h1"])
        if len(cc) < 25:
            continue
        bb, ss = ols(cc[f"L{off}"].values, [cc.pre.values, cc.h1.values],
                     ["pre", "h1"])
        pred = (bb["const"] + bb["pre"] * cc.pre.values
                + bb["h1"] * cc.h1.values)
        rsd = float(np.std(cc[f"L{off}"].values - pred, ddof=3))
        sweep.append((off, len(cc), bb["h1"], ss["h1"], bb["pre"], rsd))
        mark = "  <-- published" if off == PUB_OFFSET else ""
        if off % 4 == 0 or off == PUB_OFFSET:
            print(f"   {off:>7} {len(cc):>5} {bb['h1']:>8.3f} {ss['h1']:>7.3f} "
                  f"{bb['pre']:>8.3f} {rsd:>9.2f}{mark}")
    sw = pd.DataFrame(sweep, columns=["off", "n", "s", "se", "bpre", "resid"])

    # ---- C. Q1 vs Q2 loading ---------------------------------------------
    print("\nC. Q1 vs Q2 LOADING — the sharpest test of a mistimed anchor.")
    print("   Both quarters are banked by the true halftime, so an efficient")
    print("   line must load them EQUALLY. If the anchor lands inside Q2 the")
    print("   market has not seen Q2 yet and its coefficient must collapse.\n")
    q = pd.read_csv(R.BREF)
    q["q1"] = q.a_q1 + q.h_q1
    q["q2"] = q.a_q2 + q.h_q2
    qk = {}
    for _, r in q.iterrows():
        def cds(n):
            for city, cs in R.CITY_CODES.items():
                if str(n).startswith(city):
                    return cs
            return ()
        for a in cds(r["away"]):
            for h in cds(r["home"]):
                dd = dt.datetime.strptime(str(r["date"]), "%Y%m%d").date()
                qk[(dd, a + h)] = (r["q1"], r["q2"])
    d["q1"] = [qk.get((R.event_date(e), e.rsplit("-", 1)[-1][7:]), (np.nan,) * 2)[0]
               for e in d.event]
    d["q2"] = [qk.get((R.event_date(e), e.rsplit("-", 1)[-1][7:]), (np.nan,) * 2)[1]
               for e in d.event]
    print(f"   {'offset':>7} {'n':>5} {'b(Q1)':>8} {'b(Q2)':>8} {'Q2-Q1':>8}")
    for off in (40, 50, 58, 62, 68, 74, 80):
        cc = d.dropna(subset=[f"L{off}", "pre", "q1", "q2"])
        if len(cc) < 25:
            continue
        bb, ss = ols(cc[f"L{off}"].values,
                     [cc.pre.values, cc.q1.values, cc.q2.values],
                     ["pre", "q1", "q2"])
        mark = "  <-- published" if off == PUB_OFFSET else ""
        print(f"   {off:>7} {len(cc):>5} {bb['q1']:>8.3f} {bb['q2']:>8.3f} "
              f"{bb['q2'] - bb['q1']:>+8.3f}{mark}")
    # realized: how do Q1 and Q2 enter the true total?
    cc = d.dropna(subset=["q1", "q2", "pre"])
    bb, _ = ols(cc.total.values, [cc.pre.values, cc.q1.values, cc.q2.values],
                ["pre", "q1", "q2"])
    print(f"   {'REALIZED':>7} {len(cc):>5} {bb['q1']:>8.3f} {bb['q2']:>8.3f} "
          f"{bb['q2'] - bb['q1']:>+8.3f}  <- truth: near-equal by construction")

    # ---- D. duration dispersion ------------------------------------------
    print("\nD. HOW OFTEN CAN THE ANCHOR MISS?")
    a = d.active_min.dropna()
    print(f"   market-active minutes before the anchor: median {a.median():.0f}"
          f", IQR {a.quantile(.25):.0f}-{a.quantile(.75):.0f}, "
          f"10-90pct {a.quantile(.10):.0f}-{a.quantile(.90):.0f}")
    print(f"   spread between the 10th and 90th percentile: "
          f"{a.quantile(.90) - a.quantile(.10):.0f} minutes — the anchor is a "
          f"FIXED 58, so that dispersion lands at different game-states.")
    return d, sw


def settled_anchor(s, total, tol=CONV_TOL):
    """Game end = the first bar after the LAST time L was away from the total.

    The market settles onto the answer and STAYS there. The published rule
    takes the FIRST brush with it instead, which any mid-game wobble past the
    eventual total triggers — and the pregame line is already a good forecast,
    so that brush often happens before tip.
    """
    bad = np.where((s.L - total).abs().values > tol)[0]
    if len(bad) == 0 or bad[-1] + 1 >= len(s):
        return None
    return int(s.ts.values[bad[-1] + 1])


def volume_tip(vseries):
    """Tip = first minute whose forward 30-min volume clears 25% of the game's
    peak. Uses NO outcome information, so it is an anchor the finding cannot
    have contaminated."""
    if vseries is None or len(vseries) < 60:
        return None
    r = vseries.rolling(30, min_periods=5).sum().shift(-29)
    if not np.isfinite(r.max()) or r.max() <= 0:
        return None
    hot = r[r > 0.25 * r.max()]
    return int(hot.index[0]) if len(hot) else None


def anchor_comparison(series, vmap):
    """E. Re-estimate s under anchors that are not broken."""
    bref = R.bref_totals(R.BREF)
    pre_by = dict(zip(*(lambda p: (p.event_ticker, p.L_pre))(
        pd.read_csv(PANEL))))
    rows = []
    for e, s in series.items():
        hit = R.bref_lookup(e, bref)
        if not hit:
            continue
        total, h1, n_ot = hit
        if n_ot or e not in pre_by:
            continue
        a1 = convergence_anchor(s, total)
        a2 = settled_anchor(s, total)
        tp = volume_tip(vmap.get(e))
        if a1 is None or a2 is None or tp is None:
            continue
        r = {"event": e, "total": total, "h1": h1, "pre": pre_by[e],
             "early_min": (a2 - a1) / 60.0}
        r["Lpub"] = L_at(s, a1 - PUB_OFFSET * 60)
        for off in (52, 58, 64):
            r[f"S{off}"] = L_at(s, a2 - off * 60)
        for off in (55, 65):
            r[f"T{off}"] = L_at(s, tp + off * 60)
        rows.append(r)
    d = pd.DataFrame(rows)
    print(f"\nE. RE-ESTIMATION UNDER NON-BROKEN ANCHORS   n={len(d)}")
    print(f"   published anchor fires early by: median "
          f"{d.early_min.median():.0f} min, >60 min early in "
          f"{(d.early_min > 60).mean():.0%} of games\n")
    br, ser = ols(d.total.values, [d.pre.values, d.h1.values], ["pre", "h1"])
    print(f"   {'REALIZED benchmark (the efficient value)':<38} "
          f"s={br['h1']:.3f} (se {ser['h1']:.3f})")

    def fit(col, lab):
        c = d.dropna(subset=[col, "pre", "h1"])
        if len(c) < 25:
            return
        b, se = ols(c[col].values, [c.pre.values, c.h1.values], ["pre", "h1"])
        print(f"   {lab:<38} s={b['h1']:.3f} (se {se['h1']:.3f})  "
              f"b(pre)={b['pre']:.3f}  n={len(c)}")
    fit("Lpub", "published anchor, end-58  [PAPER]")
    for off in (52, 58, 64):
        fit(f"S{off}", f"settled anchor,   end-{off}")
    for off in (55, 65):
        fit(f"T{off}", f"volume tip (outcome-free), tip+{off}")

    print("\n   SPLIT THE PUBLISHED PANEL BY ANCHOR SANITY")
    for grp, lab in ((d.early_min <= 45, "anchor OK (<=45 min early)"),
                     (d.early_min > 45, "anchor >45 min EARLY")):
        c = d[grp].dropna(subset=["Lpub", "pre", "h1"])
        if len(c) < 20:
            continue
        b, se = ols(c.Lpub.values, [c.pre.values, c.h1.values], ["pre", "h1"])
        print(f"   {lab:<38} s={b['h1']:.3f} (se {se['h1']:.3f})  n={len(c)}")
    return d


def run_all():
    d, sw = main()
    con = sqlite3.connect(DB)
    vol = pd.read_sql("select event_ticker e, end_period_ts t, sum(volume) v "
                      "from candles where period_interval=1 group by 1,2", con)
    con.close()
    vmap = {k: g.set_index("t").v.sort_index() for k, g in vol.groupby("e")}
    anchor_comparison(build_L_series(DB), vmap)


if __name__ == "__main__":
    run_all()
