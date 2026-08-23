"""PREREG_injury_surprise.md -- the SINGLE surprise estimate.

  SurpriseOUT = (1 - P(OUT | prior_status)) * 1(OUT_late)   P strictly historical
  InjuryShock = SurpriseOUT * MIN_SHARE
  N_LATE / S_LATE / I_LATE summed over both teams

  tmove ~ MOVE_RIDGE + MOVE_LATENT + OUT_late_frozen + N_LATE (+ S_LATE | I_LATE)

Control-free sample (no rsk.CTRL -- prereg section 0). Run exactly once.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import injury_market as IM
import opening_line_error_decomposition as OLE
from injury_market import SQL, norm_name

PANEL = "injury_status_panel.csv"
SIDECAR = "/mnt/c/NBA2/move_signal_states.csv"
DEV_MAX, HOLD = 2023, 2024
MIN_CELL, MIN_PRIOR_G, W = 200, 10, 20
NPERM = 5000
RNG = np.random.default_rng(20260823)
STATUSES = ["Questionable", "Doubtful", "Probable", "Available", "UNLISTED"]


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se, 1 - r.var() / y.var()


def prior_of(v):
    idx = np.where(v == "Out")[0]
    if not len(idx):
        return "NEVER"
    i = idx[0]
    return v[i - 1] if i > 0 else "UNLISTED"


def build():
    g = OLE.load()
    g["gid"] = g.gid.astype(str).str.strip()
    g = g[(g.season >= 2020) & (g.season <= HOLD)].copy()
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    g["gk"] = (g.date.dt.strftime("%Y-%m-%d") + "|"
               + g.away.map(mp) + "@" + g.home.map(mp))

    # ---------- report sequence: prior status, final status, late OUT --------
    P = pd.read_csv(PANEL, parse_dates=["report_ts", "game_date"])
    P = P[(P.game_date >= "2020-10-01") & (P.game_date <= "2025-07-01")].copy()
    P["key"] = P.player.map(norm_name)
    P["gk"] = P.game_date.dt.strftime("%Y-%m-%d") + "|" + P.matchup
    P = P.sort_values("report_ts")
    seq = P.groupby(["gk", "key"], sort=False)["status"]
    E = pd.concat([seq.last().rename("final"),
                   seq.apply(lambda s: prior_of(s.values)).rename("prior")],
                  axis=1).reset_index()
    E["date"] = pd.to_datetime(E.gk.str.split("|").str[0])
    E["out_late"] = E.final.eq("Out") & ~E.prior.isin(["NEVER", "Out"])

    # ---------- P(OUT | prior status), STRICTLY HISTORICAL -------------------
    # CONFORMANCE FIX. The first implementation derived `prior` only for
    # sequences that CONTAIN an Out, so conditioning on prior status already
    # selected players who became Out and every P came back ~1.0 (Questionable
    # .9996, Doubtful 1.0000, UNLISTED .9843) -- a rescaled count, not a
    # surprise. The prereg says "among ALL player-game-reports carrying that
    # status", which is what this now does.
    final_map = E.set_index(["gk", "key"])["final"].to_dict()
    R = P[["gk", "key", "status", "game_date"]].copy()
    R["is_out"] = [final_map.get((a, b)) == "Out"
                   for a, b in zip(R.gk, R.key)]
    R = R[R.status.isin(["Questionable", "Doubtful", "Probable", "Available"])]
    R["date"] = R.game_date

    # UNLISTED has no report row carrying it: the denominator is players ADDED
    # to a game's report after its first report, and the question is what
    # fraction of those end up Out.
    firstrep = P.groupby("gk")["report_ts"].transform("min")
    seen1 = P.assign(first_rep=firstrep).groupby(
        ["gk", "key"]).agg(t_seen=("report_ts", "min"),
                           first_rep=("first_rep", "min"),
                           d=("game_date", "min")).reset_index()
    late_added = seen1[seen1.t_seen > seen1.first_rep].copy()
    late_added["is_out"] = [final_map.get((a, b)) == "Out"
                            for a, b in zip(late_added.gk, late_added.key)]
    late_added["status"] = "UNLISTED"
    late_added["date"] = late_added.d
    R = pd.concat([R[["date", "status", "is_out"]],
                   late_added[["date", "status", "is_out"]]])
    R["is_out"] = R.is_out.astype(float)

    daily = R.groupby(["date", "status"])["is_out"].agg(["sum", "count"])
    daily = daily.unstack("status").fillna(0.0).sort_index()
    cum = daily.cumsum().shift(1).fillna(0.0)         # strictly earlier days
    print("  P(OUT | prior status), strictly historical (final-day values):")
    Pmap = {}
    for st in STATUSES:
        if ("count", st) not in cum.columns:
            continue
        n = cum[("count", st)]
        Pmap[st] = pd.Series(
            np.where(n >= MIN_CELL, cum[("sum", st)] / n.replace(0, np.nan),
                     np.nan), index=cum.index)
        v = Pmap[st].dropna()
        print(f"    {st:14} P={v.iloc[-1] if len(v) else np.nan:.4f}   "
              f"surprise={1-(v.iloc[-1] if len(v) else np.nan):.4f}   "
              f"n_prior={int(n.iloc[-1]):,}")
    idx = {st: Pmap[st].to_dict() for st in Pmap}
    E["p_out"] = [idx.get(st, {}).get(dt, np.nan)
                  for st, dt in zip(E.prior, E.date)]
    E["surprise"] = np.where(E.out_late & E.p_out.notna(), 1.0 - E.p_out, 0.0)

    # ---------- importance: prior-only MIN_SHARE, as-of the game date --------
    M = duckdb.connect().execute(SQL).fetchdf()
    M["gid"] = M.gid.astype(str)
    M["key"] = M.pname.map(norm_name)
    gz = g[["gid", "season", "date"]].copy()
    gz["gid"] = gz.gid.str.zfill(10)      # PBP ids are zero-padded; g's are not
    M = M.merge(gz, on="gid", how="inner")
    M["tot"] = M.groupby(["gid", "abbr"])["events"].transform("sum")
    M["share"] = M.events / M.tot
    M = M.sort_values("date")
    M["min_share"] = M.groupby(["season", "key"])["share"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MIN_PRIOR_G).mean())
    state = M.loc[M.min_share.notna(),
                  ["date", "key", "min_share"]].sort_values("date")
    E = pd.merge_asof(E.sort_values("date"), state, on="date", by="key",
                      direction="backward", allow_exact_matches=False)
    E["min_share"] = E.min_share.fillna(0.0)
    E["shock"] = E.surprise * E.min_share

    # ---------- game-level states -------------------------------------------
    L = E[E.out_late]
    agg = L.groupby("gk").agg(N_LATE=("out_late", "sum"),
                              S_LATE=("surprise", "sum"),
                              I_LATE=("shock", "sum")).reset_index()
    d = g.merge(agg, on="gk", how="left").fillna(
        {"N_LATE": 0.0, "S_LATE": 0.0, "I_LATE": 0.0})

    # frozen OUT_late (SALIENT-restricted) as the incumbent control
    d0 = IM.build()[["gid", "OUT_late_DEF", "OUT_late_OFF"]]
    d0["OUT_frozen"] = d0.OUT_late_DEF + d0.OUT_late_OFF
    d = d.merge(d0[["gid", "OUT_frozen"]], on="gid", how="left").fillna(
        {"OUT_frozen": 0.0})
    sc = pd.read_csv(SIDECAR)
    sc["gid"] = sc["GAME-ID"].astype(str).str.strip()
    d = d.merge(sc[["gid", "MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"]], on="gid",
                how="left")
    d = d.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS", "tmove"])
    return d, E


def perm_p(x, col, base):
    y = x.tmove.values
    ctl = [x[c].values for c in base]
    b, _, _ = ols(y, ctl + [x[col].values])
    obs = b[-1]
    yrs = x.season.values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    v = x[col].values
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for bl in blocks:
            p[bl] = v[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols(y, ctl + [p])
        null[i] = bb[-1]
    return obs, (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)


def main():
    d, E = build()
    print(f"\n  sample {len(d):,} games   dev {int((d.season<=DEV_MAX).sum()):,}"
          f"   holdout {int((d.season==HOLD).sum()):,}")
    L = E[E.out_late]
    print(f"  late-OUT player-events: {len(L):,}")
    print(f"  prior-status mix among late-OUT events:")
    vc = L.prior.value_counts()
    for st in STATUSES:
        print(f"    {st:14} {int(vc.get(st,0)):>7,}")
    print(f"  corr(surprise, min_share) among late-OUT events: "
          f"{L[['surprise','min_share']].corr().iloc[0,1]:+.4f}   "
          f"[prereg s7 risk 1]")
    print(f"  games firing: N_LATE>0 {int((d.N_LATE>0).sum()):,}   "
          f"OUT_frozen>0 {int((d.OUT_frozen>0).sum()):,}")

    BASE = ["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS", "OUT_frozen", "N_LATE"]
    print("\n" + "=" * 94)
    print("MODELS  (target: open->close total movement)")
    print("=" * 94)
    for lab, x in (("development", d[d.season <= DEV_MAX]),
                   ("holdout 2024-25", d[d.season == HOLD])):
        y = x.tmove.values
        b0, t0, r0 = ols(y, [x[c].values for c in BASE])
        print(f"\n  {lab}   n={len(x):,}")
        print(f"    BASE   ridge {b0[1]:+.3f}({t0[1]:+.2f})  "
              f"latent {b0[2]:+.3f}({t0[2]:+.2f})  "
              f"OUT_frozen {b0[3]:+.3f}({t0[3]:+.2f})  "
              f"N_LATE {b0[4]:+.3f}({t0[4]:+.2f})   R2 {r0:+.5f}")
        for nm in ("S_LATE", "I_LATE"):
            b, t, r = ols(y, [x[c].values for c in BASE] + [x[nm].values])
            drop = (1 - abs(b[3]) / abs(b0[3])) * 100 if b0[3] else np.nan
            print(f"    +{nm:7} {nm} {b[5]:+.4f}(t={t[5]:+.2f})   "
                  f"OUT_frozen now {b[3]:+.3f}({t[3]:+.2f})  "
                  f"[{drop:+.0f}% vs base]   incr R2 {r-r0:+.5f}")

    dev = d[d.season <= DEV_MAX]
    for nm in ("S_LATE", "I_LATE"):
        obs, p = perm_p(dev, nm, BASE)
        print(f"\n  permutation ({nm}, development): observed {obs:+.4f}  p={p:.4f}")

    print("\n" + "=" * 94)
    print("MONOTONICITY (development, treated games only)")
    print("=" * 94)
    t = dev[dev.N_LATE > 0].copy()
    for nm, lab in (("S_LATE", "surprise terciles"),
                    ("I_LATE", "shock terciles")):
        try:
            t["b"] = pd.qcut(t[nm], 3, duplicates="drop")
            m = t.groupby("b")["tmove"].agg(["mean", "size"])
            print(f"  {lab:20} " + "  ".join(
                f"{i}: {r['mean']:+.3f} (n={int(r['size'])})"
                for i, r in m.iterrows()))
        except Exception as e:
            print(f"  {lab}: {e}")
    ms = L.groupby("gk")["min_share"].max().rename("imp")
    t = t.merge(ms, on="gk", how="left")
    try:
        t["q"] = pd.qcut(t.imp, 4, duplicates="drop")
        m = t.groupby("q")["tmove"].agg(["mean", "size"])
        print("  importance quartiles  " + "  ".join(
            f"[{i}]: {r['mean']:+.3f} (n={int(r['size'])})"
            for i, r in m.iterrows()))
    except Exception as e:
        print(f"  importance quartiles: not formable ({e})")

    print("\n" + "=" * 94)
    print("PRIOR-STATUS CATEGORIES (fixed order) and AGGREGATION")
    print("=" * 94)
    for st in ["Questionable", "Doubtful", "Probable", "UNLISTED"]:
        gks = set(L[L.prior == st].gk)
        x = dev[dev.gk.isin(gks)]
        print(f"  {st+'->Out':22} n={len(x):>5,}  mean tmove {x.tmove.mean():+.3f}"
              if len(x) else f"  {st+'->Out':22} n=0")
    print()
    for n, lab in ((1, "exactly 1"), (2, "exactly 2"), (3, ">= 3")):
        x = dev[dev.N_LATE == n] if n < 3 else dev[dev.N_LATE >= 3]
        if len(x):
            print(f"  N_LATE {lab:10} n={len(x):>5,}  mean tmove {x.tmove.mean():+.3f}")


if __name__ == "__main__":
    main()
