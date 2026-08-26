"""PREREG_attention_allocation.md — run once."""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import opening_line_error_decomposition as OLE

NPERM = 5000
RNG = np.random.default_rng(20260826)
THR = 1.0


def build():
    g = OLE.load(); g["gid"] = g.gid.astype(str).str.strip()
    sc = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
    sc["gid"] = sc["GAME-ID"].astype(str).str.strip()
    d = g.merge(sc[["gid", "MOVE_COMBINED_OOS"]], on="gid", how="left")
    # prior-only team quality (mu_state analogue): expanding mean points scored+allowed
    L = pd.concat([
        d[["gid", "season", "date", "home", "hpts", "apts"]].rename(
            columns={"home": "team", "hpts": "pf", "apts": "pa"}),
        d[["gid", "season", "date", "away", "apts", "hpts"]].rename(
            columns={"away": "team", "apts": "pf", "hpts": "pa"})]).sort_values("date")
    grp = L.groupby(["season", "team"])
    L["q"] = grp["pf"].transform(lambda s: s.shift(1).expanding().mean()) - \
             grp["pa"].transform(lambda s: s.shift(1).expanding().mean())
    L["np_"] = grp.cumcount()
    q = L.groupby("gid").agg(qual=("q", "sum"), minp=("np_", "min"))
    d = d.join(q, on="gid")
    d["slate"] = d.groupby("date")["gid"].transform("size")
    d["prom_rank"] = d.groupby("date")["qual"].rank(pct=True)
    d = d.dropna(subset=["MOVE_COMBINED_OOS", "tmove", "qual"])
    d = d[d.minp >= 10]
    d["clv"] = np.sign(d.MOVE_COMBINED_OOS) * d.tmove
    return d[d.MOVE_COMBINED_OOS.abs() >= THR].reset_index(drop=True)


def tstat(a, b):
    diff = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return diff, diff / se


def main():
    d = build()
    dev, hold = d[d.season <= 2023], d[d.season >= 2024]
    print(f"  bets at |m|>={THR}: {len(d):,}  dev {len(dev):,}  holdout {len(hold):,}"
          f"  dates {d.date.nunique()}")

    print("\n  POSITIVE CONTROL — pooled CLV (bar: >= +1.0 pts, t >= 5)")
    m = d.clv.mean(); t = m / (d.clv.std(ddof=1) / np.sqrt(len(d)))
    print(f"    pooled mean CLV {m:+.4f}  t={t:+.2f}   "
          f"{'PASS' if (m >= 1.0 and t >= 5) else 'FAIL'}")
    if not (m >= 1.0 and t >= 5):
        print("    harness unverified — halting per prereg s4."); return

    q67 = dev.slate.quantile(2/3)
    for x in (d, dev, hold):
        x["LOW_ATT"] = ((x.slate >= q67) & (x.prom_rank <= 0.5)).astype(int)
    print(f"\n  FROZEN dev Q67 of slate size = {q67:.1f}")
    print(f"  LOW_ATTENTION fires on {int(d.LOW_ATT.sum()):,} of {len(d):,} bets "
          f"({100*d.LOW_ATT.mean():.1f}%)")

    print(f"\n  PRIMARY — mean CLV, LOW_ATTENTION vs rest")
    print(f"    {'window':16}{'n low':>7}{'CLV low':>10}{'n rest':>8}{'CLV rest':>10}"
          f"{'diff':>9}{'t':>7}")
    res = {}
    for lab, x in (("development", dev), ("holdout", hold)):
        a, b = x[x.LOW_ATT == 1].clv, x[x.LOW_ATT == 0].clv
        diff, tt = tstat(a, b)
        res[lab] = (diff, tt)
        print(f"    {lab:16}{len(a):>7,}{a.mean():>+10.3f}{len(b):>8,}"
              f"{b.mean():>+10.3f}{diff:>+9.3f}{tt:>+7.2f}")

    # within-date permutation on development (holds slate size fixed)
    x = dev.reset_index(drop=True)
    obs = res["development"][0]
    groups = [np.where(x.date.values == u)[0] for u in x.date.unique()]
    v = x.LOW_ATT.values; clv = x.clv.values
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for gidx in groups:
            if len(gidx) > 1:
                p[gidx] = v[gidx][RNG.permutation(len(gidx))]
        a, b = clv[p == 1], clv[p == 0]
        null[i] = a.mean() - b.mean() if len(a) and len(b) else np.nan
    pv = (1 + np.nansum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"\n  within-date permutation (development): observed {obs:+.4f}  "
          f"null sd {np.nanstd(null):.4f}  p={pv:.4f}")

    print("\n  SECONDARY (reported, never promoted)")
    for lab, x in (("development", dev), ("holdout", hold)):
        for nm, sub in (("low-att", x[x.LOW_ATT == 1]), ("rest", x[x.LOW_ATT == 0])):
            nz = sub[sub.clv != 0]
            wr = 100 * (nz.clv > 0).mean()
            print(f"    {lab:12} {nm:8} beat-close {wr:5.1f}%  n={len(nz):,}")

    print("\n  A3 CORROBORATION (2025-26 Kalshi volume) — barred from the decision")
    try:
        import sqlite3
        c = sqlite3.connect("file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro", uri=True)
        mk = pd.read_sql("SELECT event_ticker, game_date, home_team, away_team, volume FROM markets", c)
        mk["volume"] = pd.to_numeric(mk.volume, errors="coerce")
        ev = mk.groupby(["game_date", "home_team", "away_team"], as_index=False).volume.sum()
        mp = pd.read_csv("team_mapping.csv").set_index("bigdataball_name")["abbr"].to_dict()
        h = d[d.season == 2025].copy()
        h["k"] = h.date.dt.strftime("%Y-%m-%d") + "|" + h.away.map(mp) + "|" + h.home.map(mp)
        ev["k"] = ev.game_date + "|" + ev.away_team + "|" + ev.home_team
        h = h.merge(ev[["k", "volume"]], on="k", how="inner").dropna(subset=["volume"])
        if len(h) > 50:
            lo = h[h.volume <= h.volume.median()]; hi = h[h.volume > h.volume.median()]
            dd, tt2 = tstat(lo.clv, hi.clv)
            print(f"    low-volume CLV {lo.clv.mean():+.3f} (n={len(lo)})  "
                  f"high-volume {hi.clv.mean():+.3f} (n={len(hi)})  diff {dd:+.3f} (t={tt2:+.2f})")
        else:
            print(f"    insufficient join ({len(h)} games)")
    except Exception as ex:
        print(f"    unavailable: {type(ex).__name__}")

    print("\n  DECISION (prereg s5)")
    c1 = res["development"][0] >= 0.35
    c2 = abs(res["development"][1]) >= 2
    c3 = np.sign(res["holdout"][0]) == np.sign(res["development"][0])
    c4 = pv < 0.05
    for nm, c in (("dev diff >= +0.35 pts", c1), ("dev |t| >= 2", c2),
                  ("holdout same sign", c3), ("within-date perm p < 0.05", c4)):
        print(f"    {nm:32} {'PASS' if c else 'FAIL'}")
    print(f"    -> {'CONCENTRATION ESTABLISHED' if all((c1,c2,c3,c4)) else 'CLV IS ATTENTION-INVARIANT'}")
    print("    [either way, the 2026-27 forward test runs UNCHANGED — prereg s6]")


if __name__ == "__main__":
    main()
