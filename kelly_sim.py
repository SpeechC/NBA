"""Quarter-Kelly simulation on the frozen totals signals.

Three questions, kept separate because they answer different things:

  A  IN-SAMPLE      what a quarter-Kelly bettor would have made if they had
                    known the realised edge in advance. A historical
                    statement, NOT a forecast.
  B  WALK-FORWARD   what they would have made estimating the edge only from
                    bets already settled. This is the honest path.
  C  SENSITIVITY    what happens if the true edge is lower than measured,
                    including the case where it is exactly break-even.

Bets are grouped by DATE: same-day wagers are sized off the bankroll at the
start of that day, so simultaneous games do not compound within a day.
Flat -110 pricing throughout; win pays 100/110.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs

THR = 0.8682
B_ODDS = 100.0 / 110.0          # net fractional odds at -110
BE = 110.0 / 210.0
FRAC = 0.25                     # quarter Kelly
BANK0 = 100_000.0
RNG = np.random.default_rng(90210)


def kelly(p, b=B_ODDS):
    """Full-Kelly fraction; 0 if no edge."""
    f = (b * p - (1.0 - p)) / b
    return max(f, 0.0)


def load():
    d = refs.build()
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    d = d.merge(f[["gid", "CrewShock"]], on="gid", how="inner")
    d = d.dropna(subset=["CrewShock", "e"])
    d["days_left"] = (d.groupby("yr")["date"].transform("max")
                      - d["date"]).dt.days
    d["crew"] = d["CrewShock"] >= THR
    d["week"] = d["days_left"] <= 7
    d["win"] = d["e"] > 0
    d["push"] = d["e"] == 0
    return d.sort_values("date").reset_index(drop=True)


def simulate(bets, frac_fn, bank0=BANK0):
    """Day-grouped compounding. frac_fn(i) -> fraction of bankroll per bet."""
    bank = bank0
    path, peak, maxdd = [], bank0, 0.0
    for day, g in bets.groupby("date", sort=True):
        start = bank
        for i, r in g.iterrows():
            f = frac_fn(i)
            stake = f * start
            if r["push"]:
                continue
            bank += stake * B_ODDS if r["win"] else -stake
        peak = max(peak, bank)
        maxdd = max(maxdd, (peak - bank) / peak)
        path.append((day, bank))
        if bank <= 0:
            break
    P = pd.DataFrame(path, columns=["date", "bank"])
    return P, maxdd


def summarise(P, maxdd, n_bets, lab, n_seasons=8):
    fin = P["bank"].iloc[-1]
    mult = fin / BANK0
    cagr = mult ** (1.0 / n_seasons) - 1.0
    print(f"  {lab:34} final ${fin:12,.0f}  x{mult:6.2f}  "
          f"{100*cagr:+7.2f}%/season  maxDD {100*maxdd:5.1f}%  "
          f"n={n_bets:,}")
    return fin, cagr, maxdd


def main():
    d = load()
    strat = {"CrewShock Q85": d[d["crew"]],
             "final week": d[d["week"] & ~d["crew"]],
             "union": d[d["crew"] | d["week"]]}
    print("REALISED RATES (graded, pushes removed)")
    p_hat = {}
    for k, g in strat.items():
        w = int(g["win"].sum())
        l = int(((~g["win"]) & (~g["push"])).sum())
        p = w / (w + l)
        p_hat[k] = p
        print(f"  {k:16} n={len(g):5,}  win {100*p:6.2f}%  "
              f"full Kelly {100*kelly(p):5.2f}%  quarter {100*FRAC*kelly(p):5.2f}%")

    print("\n" + "=" * 92)
    print("A — IN-SAMPLE quarter Kelly (assumes the realised edge was known)")
    print("=" * 92)
    for k, g in strat.items():
        f = FRAC * kelly(p_hat[k])
        P, dd = simulate(g, lambda i, f=f: f)
        summarise(P, dd, len(g), k)

    print("\n" + "=" * 92)
    print("B — WALK-FORWARD quarter Kelly (edge from settled bets only)")
    print("   stake 0 until 200 bets have settled; edge shrunk toward "
          "break-even")
    print("=" * 92)
    for k, g in strat.items():
        g = g.copy().reset_index(drop=True)
        graded = (~g["push"]).values
        wins = g["win"].values
        fr = np.zeros(len(g))
        cw = cn = 0
        for i in range(len(g)):
            if cn >= 200:
                # shrink toward break-even: pseudo-count of 200 at BE
                p_est = (cw + 200 * BE) / (cn + 200)
                fr[i] = FRAC * kelly(p_est)
            if graded[i]:
                cw += int(wins[i])
                cn += 1
        g["_f"] = fr
        P, dd = simulate(g, lambda i, g=g: g["_f"].iloc[i])
        bets_made = int((fr > 0).sum())
        summarise(P, dd, bets_made, k)
        print(f"    {'':32} final stake fraction "
              f"{100*fr[-1]:.2f}%   bets skipped while learning: "
              f"{len(g)-bets_made:,}")

    print("\n" + "=" * 92)
    print("C — SENSITIVITY: quarter Kelly SIZED at 54.82% but true p differs")
    print("   1,000 resamples of the union bet sequence at each true p")
    print("=" * 92)
    g = strat["union"]
    n = int((~g["push"]).sum())
    f = FRAC * kelly(p_hat["union"])
    print(f"  staking {100*f:.2f}% per bet, {n:,} graded bets over 8 seasons\n")
    print(f"  {'true p':>8}{'median x':>11}{'5th pct':>10}{'95th pct':>11}"
          f"{'P(loss)':>10}{'P(>2x)':>9}{'med maxDD':>11}")
    for p_true in (0.5482, 0.5400, 0.5300, 0.5238, 0.5150, 0.5000):
        mults, dds = [], []
        for _ in range(1000):
            out = RNG.random(n) < p_true
            bank, peak, mdd = BANK0, BANK0, 0.0
            for w in out:
                bank += bank * f * B_ODDS if w else -bank * f
                peak = max(peak, bank)
                mdd = max(mdd, (peak - bank) / peak)
            mults.append(bank / BANK0)
            dds.append(mdd)
        m = np.array(mults)
        tag = "  <- measured" if p_true == 0.5482 else (
            "  <- break-even" if p_true == 0.5238 else "")
        print(f"  {100*p_true:7.2f}%{np.median(m):11.2f}"
              f"{np.percentile(m,5):10.2f}{np.percentile(m,95):11.2f}"
              f"{100*np.mean(m<1):9.1f}%{100*np.mean(m>2):8.1f}%"
              f"{100*np.median(dds):10.1f}%{tag}")

    print("\n" + "=" * 92)
    print("SEASON-BY-SEASON, walk-forward union")
    print("=" * 92)
    g = strat["union"].copy().reset_index(drop=True)
    graded = (~g["push"]).values
    wins = g["win"].values
    fr = np.zeros(len(g)); cw = cn = 0
    for i in range(len(g)):
        if cn >= 200:
            fr[i] = FRAC * kelly((cw + 200 * BE) / (cn + 200))
        if graded[i]:
            cw += int(wins[i]); cn += 1
    g["_f"] = fr
    bank = BANK0
    print(f"  {'season':10}{'bets':>7}{'win %':>8}{'stake %':>9}"
          f"{'start $':>12}{'end $':>12}{'return':>9}")
    for y, gg in g.groupby("yr"):
        s = bank
        for day, dd_ in gg.groupby("date", sort=True):
            st = bank
            for i, r in dd_.iterrows():
                if r["push"]:
                    continue
                stake = g["_f"].iloc[i] * st
                bank += stake * B_ODDS if r["win"] else -stake
        w = int(gg["win"].sum()); l = int(((~gg["win"]) & (~gg["push"])).sum())
        wp = 100 * w / (w + l) if w + l else np.nan
        print(f"  {int(y):<10}{len(gg):7,}{wp:8.2f}"
              f"{100*gg['_f'].mean():9.2f}{s:12,.0f}{bank:12,.0f}"
              f"{100*(bank/s-1):+8.1f}%")


if __name__ == "__main__":
    main()
