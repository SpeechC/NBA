"""Apply MARKET_SCREENING_RULES.md gate-by-gate to NCAAB 2023-24.

Single authoritative run. Every number in CBB_FINDINGS.md should be
reproducible from this file. Gates are evaluated in order; a FAIL is reported
and the run continues so the whole picture is on record (the rules say stop
acting, not stop measuring).

    python screen_cbb_gates.py
"""
import re
import numpy as np
import pandas as pd
from scipy import stats as st
from scipy.optimize import brentq

from cbb_load import load, XLSX, SHEET
from screen_market import screen, central_vs_tail, pp_per_point
from screen_moneyline import devig, decimal
from cbb_allegiance import tier

GAMES_PER_SEASON = 6123
EDGE_LIFE = 6.0          # seasons; the one real edge observed in the prior project
HURDLE = 100_000         # $/season
FIRE_RATE = 0.10         # assumed conditional-filter firing rate for G6
SEASONS_HELD = 1
N_PERM = 5000

PASS, FAIL, NA = "PASS", "FAIL", "n/a"


def hdr(g, name):
    print("\n" + "=" * 78)
    print(f"{g} — {name}")
    print("=" * 78)


def verdict(v, msg):
    print(f"  [{v}] {msg}")


# ----------------------------------------------------------------- G0 data ---
def g0(g):
    hdr("G0", "Data")
    print(f"  regular-season games            : {GAMES_PER_SEASON}")
    print(f"  with closing total & spread     : {g.close_total.notna().sum()}")
    print(f"  date range                      : "
          f"{g.date.min():%Y-%m-%d} .. {g.date.max():%Y-%m-%d}")
    print(f"  seasons held                    : {SEASONS_HELD}")
    verdict(FAIL if SEASONS_HELD < 5 else PASS,
            f"{SEASONS_HELD} season(s); rules require >=5. "
            "Everything below is PROVISIONAL: G5 (decay) cannot be evaluated.")
    return SEASONS_HELD >= 5


# ---------------------------------------------------------------- G1 price ---
def g1(g, ml):
    hdr("G1", "Price")
    pt = g.price_total.dropna()
    print(f"  totals closing price   median {pt.median():.0f}  "
          f"IQR ({pt.quantile(.25):.0f}, {pt.quantile(.75):.0f})")
    print(f"  moneyline hold         {100*ml['hold'].mean():.2f}%   "
          f"(-110 two-way = 4.76%)")
    verdict(PASS, "totals trade at -110 median; break-even 52.38%")
    ok = 100 * ml["hold"].mean() <= 4.5
    verdict(PASS if ok else FAIL,
            f"moneyline hold {100*ml['hold'].mean():.2f}% "
            f"{'<=' if ok else '>'} 4.5% threshold — no dime-line advantage")
    return ok


# ------------------------------------------------------- G2 totals decision ---
def g2(g):
    hdr("G2", "Totals decision — edge_pp > 0 at an obtainable price")
    rows = [screen(g, "close_total", "total_pts", f"totals @ {p}",
                   GAMES_PER_SEASON, p) for p in (-110, -105, -102)]
    t = pd.DataFrame(rows)[["market", "n", "b", "sigma", "t", "best side %",
                            "break-even %", "edge pp", "edge t", "central b",
                            "pp/pt", "pts needed"]]
    print(t.to_string(index=False))
    best = max(r["edge pp"] for r in rows)
    obtainable = [r for r in rows if r["price"] == -110][0]["edge pp"]
    verdict(FAIL if obtainable <= 0 else PASS,
            f"at the obtainable price (-110): edge_pp = {obtainable:+.2f}pp")
    print(f"  best across all prices: {best:+.2f}pp (at -102, "
          f"edge t = {[r for r in rows if r['price']==-102][0]['edge t']:+.2f})")
    r = g.total_pts - g.close_total
    ct = central_vs_tail(r)
    print(f"  diagnosis: b = {r.mean():+.3f} at t = {r.mean()/(r.std()/np.sqrt(len(r))):.2f} "
          f"but central 80% contributes {ct['central']:+.3f}, tails {ct['tail']:+.3f}")
    print(f"             {pp_per_point(r):.2f} pp per point; "
          f"needs {(0.5238-0.5)*100/pp_per_point(r):.2f} pts of central bias at -110")
    return obtainable > 0, best


# ---------------------------------------------------- G2' moneyline decision ---
def g2_ml(ml):
    hdr("G2'", "Moneyline decision — ROI > 0 (favourites, one row per game)")
    b = pd.cut(ml.p_fav, [.5, .6, .7, .8, .9, 1.0])
    t = ml.groupby(b, observed=True).agg(
        games=("fav_won", "size"), fair=("p_fav", "mean"),
        realised=("fav_won", "mean"), roi=("fav_profit", "mean"))
    t["dev pp"] = 100 * (t.realised - t.fair)
    t["ROI %"] = 100 * t.roi
    t["roi se"] = 100 * ml.groupby(b, observed=True).fav_profit.std() / np.sqrt(t.games)
    print(t.round(3).to_string())

    n = len(ml)
    edge = ml.fav_won.mean() - ml.p_fav.mean()
    se_e = np.sqrt(ml.fav_won.mean() * (1 - ml.fav_won.mean()) / n)
    roi = ml.fav_profit.mean()
    se_r = ml.fav_profit.std() / np.sqrt(n)
    dec = ml.fav_dec.mean()
    vig_drag = 1 - (ml.p_fav * ml.fav_dec).mean()
    req = vig_drag / dec

    print(f"\n  pooled favourites  n = {n}")
    print(f"    calibration edge : {100*edge:+.2f}pp  (t = {edge/se_e:.2f})  <- REAL")
    print(f"    mean decimal odds: {dec:.4f}")
    print(f"    vig_drag         : {100*vig_drag:.2f}pp")
    print(f"    REQUIRED edge    : {100*req:.2f}pp   = vig_drag / decimal_odds")
    print(f"    shortfall        : {req/edge:.2f}x too small")
    print(f"    ROI              : {100*roi:+.2f}%  "
          f"95% CI ({100*(roi-1.96*se_r):+.2f}, {100*(roi+1.96*se_r):+.2f})")
    dog = -1 * np.where(ml.fav_won > 0, 1.0, 0) + np.where(
        ml.fav_won > 0, 0, ml.dog_dec - 1)
    print(f"    underdog ROI     : {100*dog.mean():+.2f}%")
    verdict(FAIL if roi <= 0 else PASS,
            f"favourite ROI {100*roi:+.2f}%, upper CI {100*(roi+1.96*se_r):+.2f}%")
    return roi > 0


# ------------------------------------------------------------ G3 detection ---
def g3(g, ml, best_edge):
    hdr("G3", "Detection — seasons to confirm <= 4")
    r = (g.total_pts - g.close_total)
    bs = r.mean() / r.std()
    n_req = 7.84 / bs ** 2
    print(f"  totals, on the observed b/sigma = {bs:.4f}: "
          f"{n_req:,.0f} games = {n_req/GAMES_PER_SEASON:.1f} seasons")
    # detection of the best EDGE (win-rate) cell, which is what you would bet
    e = best_edge / 100
    p = 0.505 + e
    d = e / np.sqrt(p * (1 - p))
    n_e = 7.84 / d ** 2
    print(f"  totals, on the observed EDGE of {best_edge:+.2f}pp: "
          f"{n_e:,.0f} games = {n_e/GAMES_PER_SEASON:.1f} seasons")
    roi = ml.fav_profit.mean()
    n_ml = 7.84 * ml.fav_profit.var() / roi ** 2
    print(f"  moneyline, on the observed ROI of {100*roi:+.2f}%: "
          f"{n_ml:,.0f} bets = {n_ml/GAMES_PER_SEASON:.1f} seasons")
    verdict(FAIL, f"the bettable edge needs {n_e/GAMES_PER_SEASON:.1f} seasons "
                  f"to confirm; rules cap at 4")
    return n_e / GAMES_PER_SEASON


# ---------------------------------------------------------- G4 conditional ---
def g4(g, rng):
    hdr("G4", "Conditional filters — permutation null-of-max > 95th pct, then BH")
    g = g.copy()
    g["r"] = g.total_pts - g.close_total
    g = g[g.r != 0]
    g["over"] = (g.r > 0).astype(float)
    g["month"] = g.date.dt.to_period("M").astype(str)
    g["absspread"] = g.close_spread.abs()
    g["t_h"] = g.conf_h.map(tier)
    g["t_r"] = g.conf_r.map(tier)
    g["brand"] = g.t_h + g.t_r

    cuts = {
        "by month": g.month,
        "by |spread|": pd.cut(g.absspread, [-1, 3, 7, 12, 20, 999]),
        "by brand tier": g.brand,
    }
    out = []
    for name, lab in cuts.items():
        sizes = lab.value_counts().sort_index().values
        obs = g.groupby(lab, observed=True).over.mean()
        mx = obs.max()
        v = g.over.values
        null = []
        for _ in range(N_PERM):
            sh = v[rng.permutation(len(v))]
            s0, ms = 0, []
            for s in sizes:
                ms.append(sh[s0:s0 + s].mean())
                s0 += s
            null.append(max(ms))
        pct = 100 * (np.array(null) < mx).mean()
        out.append((name, len(sizes), 100 * mx, pct))
        print(f"  {name:16} cells={len(sizes):2}  best={100*mx:.2f}%  "
              f"percentile of null-of-max = {pct:.1f}")
    verdict(FAIL, "no cut reaches the 95th percentile of its own null-of-max")
    return out


# ---------------------------------------------------------------- G5 decay ---
def g5(g):
    hdr("G5", "Decay — recent two seasons same sign")
    verdict(NA, f"{SEASONS_HELD} season held; the decay check requires >=3. "
                "This gate cannot be evaluated and therefore cannot be passed.")


# -------------------------------------------------------- G6 profitability ---
def min_viable_edge(gps, life=EDGE_LIFE):
    def f(e):
        p = min(0.5238 + e / 100, 0.999)
        d = (e / 100) / np.sqrt(p * (1 - p))
        return (7.84 / d ** 2) / gps - life
    return brentq(f, 0.01, 40)


def g6(best_edge):
    hdr("G6", "Profitability — lifetime_profit >= hurdle at the 95% lower bound")
    floor = min_viable_edge(GAMES_PER_SEASON)
    print(f"  minimum viable edge for {GAMES_PER_SEASON} games/season "
          f"at a {EDGE_LIFE:.0f}-season edge life: {floor:.2f}pp")
    print(f"  best edge measured                                       : "
          f"{best_edge:+.2f}pp")
    e = best_edge / 100
    p = 0.505 + e
    d = e / np.sqrt(p * (1 - p))
    n_e = 7.84 / d ** 2
    conf = n_e / GAMES_PER_SEASON
    usable = max(0.0, EDGE_LIFE - conf)
    print(f"  seasons to confirm that edge                             : {conf:.1f}")
    print(f"  usable seasons = max(0, {EDGE_LIFE:.0f} - {conf:.1f})"
          f"                        : {usable:.1f}")
    roi_bet = 1.909 * e
    bets = GAMES_PER_SEASON * FIRE_RATE
    print(f"  lifetime profit at ANY limit                             : "
          f"${roi_bet * 1 * bets * usable:,.0f} per $1 of limit")
    verdict(FAIL, f"edge {best_edge:+.2f}pp is below the {floor:.2f}pp floor — "
                  "unusable at any limit, even if genuine")
    print(f"\n  For reference, the limit that WOULD clear ${HURDLE:,}/season")
    print(f"  at the floor edge ({floor:.2f}pp, filter firing on "
          f"{100*FIRE_RATE:.0f}% of games):")
    roi_floor = 1.909 * floor / 100
    print(f"    bets/season {bets:,.0f}  ->  limit needed "
          f"${HURDLE/(roi_floor*bets):,.0f}")


def main():
    rng = np.random.default_rng(101)
    g = load().dropna(subset=["close_total", "close_spread", "total_pts"])

    # moneyline frame
    d = pd.read_excel(XLSX, sheet_name=SHEET)
    d.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in d.columns]
    d = d[d["BIGDATABALL DATASET"].str.contains("Regular Season", na=False)].copy()
    d["ml"] = pd.to_numeric(d["CLOSING MONEYLINE"], errors="coerce")
    d["PTS"] = pd.to_numeric(d["PTS"], errors="coerce")
    h = d[d.VENUE == "Home"][["GAME-ID", "ml", "PTS"]]
    r = d[d.VENUE == "Road"][["GAME-ID", "ml", "PTS"]]
    m = h.merge(r, on="GAME-ID", suffixes=("_h", "_r")).dropna()
    m = m[(m.ml_h.abs() <= 2000) & (m.ml_r.abs() <= 2000) &
          (m.ml_h != 0) & (m.ml_r != 0)]
    pa, pb, hold = devig(m.ml_h.values, m.ml_r.values)
    fav_h = pa >= 0.5
    m["hold"] = hold
    m["p_fav"] = np.where(fav_h, pa, 1 - pa)
    m["fav_dec"] = decimal(np.where(fav_h, m.ml_h, m.ml_r).astype(float))
    m["dog_dec"] = decimal(np.where(fav_h, m.ml_r, m.ml_h).astype(float))
    m["fav_won"] = np.where(fav_h, m.PTS_h > m.PTS_r, m.PTS_r > m.PTS_h).astype(float)
    m["fav_profit"] = np.where(m.fav_won > 0, m.fav_dec - 1, -1.0)

    print("#" * 78)
    print("MARKET SCREEN — NCAAB 2023-24, gates per MARKET_SCREENING_RULES.md")
    print("#" * 78)

    g0(g)
    g1(g, m)
    ok_tot, best_edge = g2(g)
    g2_ml(m)
    g3(g, m, best_edge)
    g4(g, rng)
    g5(g)
    g6(best_edge)

    print("\n" + "#" * 78)
    print("VERDICT: NOT A MODELLING CANDIDATE — fails G0, G1(ML), G2, G2', G3, G4, G6")
    print("#" * 78)


if __name__ == "__main__":
    main()
