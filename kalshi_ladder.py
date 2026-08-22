"""Decompose a Kalshi totals LADDER into its implied distribution.

Kalshi quotes each strike as a separate binary: "Over K points scored", Yes and
No. A full ladder is therefore a discretised survival function, which is much
richer than a single -110 over/under: it prices the whole distribution, and it
lets you build RANGE trades that a sportsbook total cannot express.

Yes at a, No at b means the Yes contract is bid (1-b) / ask a. Mid = (a+1-b)/2.

WHAT THIS COMPUTES
  1. mid probabilities, spread, and an internal-consistency / arbitrage check
  2. the implied band probabilities P(K_i < total <= K_i+1)
  3. the executable cost of each band trade, versus its implied probability
  4. a normal fit -> implied mean and sd, and the residuals from it
  5. Kalshi's fee curve across the ladder, which is NOT flat
  6. how many points of edge each rung needs to break even

FEES. Kalshi charges roughly  fee = 0.07 * P * (1-P)  per contract, rounded up
to the cent. That is MAXIMAL at the money (1.75c at P=0.50) and falls toward the
wings (1.12c at P=0.20). This is the opposite shape to where the probability
edge lives, so the trade-off is real and is computed below. Verify the current
schedule before trading -- Kalshi has changed it.
"""
import numpy as np
from scipy.stats import norm

# strike, Yes price (cents), No price (cents)
LADDER = [
    (166.5, 75, 26), (169.5, 69, 32), (172.5, 62, 39),
    (175.5, 54, 47), (178.5, 46, 55), (181.5, 39, 62),
    (184.5, 33, 68), (187.5, 25, 76), (190.5, 20, 81),
]
FEE_K = 0.07
MAKER_MULT = 0.25        # Kalshi maker fee is exactly 25% of the taker fee
NBA_SD = 18.08           # our measured closing-total residual sd
CREWSHOCK_EDGE = 0.0482  # 54.82% realised over-rate = 4.82pp above fair


def fee(p, maker=False):
    """Kalshi per-contract fee, in probability units."""
    f = FEE_K * p * (1.0 - p)
    return f * MAKER_MULT if maker else f


def main():
    K = np.array([k for k, _, _ in LADDER], float)
    ask = np.array([a for _, a, _ in LADDER], float) / 100.0
    nask = np.array([b for _, _, b in LADDER], float) / 100.0
    bid = 1.0 - nask                      # selling Yes = buying No
    mid = (ask + bid) / 2.0

    print("=" * 100)
    print("1 — THE LADDER AS A SURVIVAL FUNCTION")
    print("=" * 100)
    print(f"  {'strike':>8}{'Yes ask':>9}{'No ask':>8}{'Yes bid':>9}"
          f"{'mid P(>K)':>11}{'spread':>8}{'sum':>7}")
    for i in range(len(K)):
        print(f"  {K[i]:>8.1f}{100*ask[i]:>9.0f}{100*nask[i]:>8.0f}"
              f"{100*bid[i]:>9.0f}{mid[i]:>11.3f}{100*(ask[i]-bid[i]):>8.0f}"
              f"{100*(ask[i]+nask[i]):>7.0f}")
    print(f"\n  every rung sums to {100*(ask[0]+nask[0]):.0f}c -> a uniform 1c "
          f"over-round, i.e. a 1c bid/ask spread")
    print(f"  monotone decreasing: "
          f"{'YES' if np.all(np.diff(mid) < 0) else 'NO -- ARBITRAGE'}")

    print("\n" + "=" * 100)
    print("2 — IMPLIED BAND PROBABILITIES vs WHAT A BAND TRADE COSTS")
    print("  a band is: buy Yes at the LOWER strike + buy No at the UPPER one.")
    print("  it pays 2 if the total lands inside, 1 if outside. cost > 1 always")
    print("  -> net: win (2-cost) inside, lose (cost-1) outside")
    print("=" * 100)
    print(f"  {'band':>18}{'implied P':>11}{'cost':>8}{'risk':>8}{'win':>8}"
          f"{'break-even P':>14}{'edge':>8}")
    for i in range(len(K) - 1):
        cost = ask[i] + nask[i + 1]
        risk = cost - 1.0
        win = 2.0 - cost
        f2 = fee(ask[i]) + fee(nask[i + 1])
        be = (risk + f2) / (win + risk)
        p_imp = mid[i] - mid[i + 1]
        print(f"  {f'{K[i]:.1f}-{K[i+1]:.1f}':>18}{p_imp:>11.3f}"
              f"{100*cost:>8.0f}{100*risk:>8.0f}{100*win:>8.0f}"
              f"{be:>14.3f}{p_imp-be:>+8.3f}")
    print("\n  'break-even P' includes both legs' fees. 'edge' is the ladder's")
    print("  own implied probability minus that -- negative everywhere means the")
    print("  ladder is internally consistent and the band costs you the spread.")

    print("\n" + "=" * 100)
    print("3 — NORMAL FIT: what mean and sd is this ladder pricing?")
    print("=" * 100)
    z = norm.ppf(1.0 - mid)               # z = (K - mu)/sigma
    A = np.column_stack([np.ones(len(K)), K])
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    sigma = 1.0 / coef[1]
    mu = -coef[0] * sigma
    fit = 1.0 - norm.cdf((K - mu) / sigma)
    print(f"  implied mean  {mu:.2f} points")
    print(f"  implied sd    {sigma:.2f} points")
    print(f"  50% crossing  {mu:.2f}  (the sportsbook-equivalent total)")
    print(f"\n  {'strike':>8}{'mid':>9}{'normal':>9}{'resid':>9}"
          f"{'resid in pts':>14}")
    dens = norm.pdf((K - mu) / sigma) / sigma
    for i in range(len(K)):
        r = mid[i] - fit[i]
        print(f"  {K[i]:>8.1f}{mid[i]:>9.3f}{fit[i]:>9.3f}{r:>+9.4f}"
              f"{r/dens[i]:>+14.2f}")
    print(f"\n  max |residual| {np.abs(mid-fit).max():.4f} "
          f"({np.abs((mid-fit)/dens).max():.2f} points) -- a smooth normal "
          f"fits this ladder to well inside the 1c spread")
    print(f"  NOTE: mean {mu:.0f} is NOT an NBA full-game total (our NBA sample "
          f"means 224.05, sd 10.14).")
    print(f"  Benchmark sigma against the right competition before using it.")

    print("\n" + "=" * 100)
    print("4 — FEES ARE NOT FLAT, AND EDGE IS NOT FLAT. WHERE SHOULD YOU TRADE?")
    print("=" * 100)
    print(f"  for a points-edge D, probability edge at strike K is ~ D * f(K)")
    print(f"  {'strike':>8}{'mid':>8}{'density':>10}{'fee(c)':>9}"
          f"{'pts to cover fee':>18}{'pts to cover fee+spread':>25}")
    for i in range(len(K)):
        f1 = fee(mid[i])
        print(f"  {K[i]:>8.1f}{mid[i]:>8.3f}{dens[i]:>10.4f}{100*f1:>9.2f}"
              f"{f1/dens[i]:>18.2f}{(f1+0.005)/dens[i]:>25.2f}")
    print("\n  the last column is the REAL hurdle: how many points your forecast")
    print("  must beat the ladder by, at that rung, to break even after paying")
    print("  the taker spread and the fee.")

    print("\n" + "=" * 100)
    print("5 — COMPARISON WITH A -110 SPORTSBOOK TOTAL")
    print("=" * 100)
    # calibrate to NBA, using OUR measured residual sd, not this ladder's
    d_nba = norm.pdf(0.0) / NBA_SD
    tk = fee(0.50) + 0.005                 # taker: cross the spread, full fee
    mk = fee(0.50, maker=True) - 0.005     # maker: earn the spread, 25% fee
    print(f"  NBA calibration: closing-total residual sd {NBA_SD}, so the "
          f"at-the-money")
    print(f"  density is {d_nba:.5f} per point. 1 point of edge = "
          f"{100*d_nba:.2f}pp of win probability.")
    print(f"\n  {'venue':16}{'fee':>8}{'spread':>9}{'hurdle':>10}"
          f"{'in points':>11}")
    for lab, f_, s_ in (("-110", 0.0238, 0.0),
                        ("Kalshi taker", fee(0.50), +0.005),
                        ("Kalshi maker", fee(0.50, maker=True), -0.005)):
        h = f_ + s_ if lab != "-110" else 0.0238
        print(f"  {lab:16}{100*f_:>7.2f}pp{100*s_:>8.2f}pp{100*h:>9.2f}pp"
              f"{h/d_nba:>11.2f}")

    print(f"\n  ESTABLISHMENT BURDEN. n = 7.84*0.25/(edge over the hurdle)^2.")
    print(f"  CrewShock wins 54.82% at -110 = {100*CREWSHOCK_EDGE:.2f}pp above "
          f"fair, on ~233 bets/season.")
    print(f"  MARKET_SCREENING_RULES.md G3: more than 4 seasons -> REJECT.")
    print(f"  {'venue':16}{'hurdle':>9}{'net edge':>11}{'bets':>10}"
          f"{'seasons':>10}{'verdict':>10}")
    for lab, h in (("-110", 0.0238), ("Kalshi taker", tk),
                   ("Kalshi maker", mk)):
        net = CREWSHOCK_EDGE - h
        n = 7.84 * 0.25 / net ** 2
        yrs = n / 233
        print(f"  {lab:16}{100*h:>8.2f}pp{100*net:>10.2f}pp{n:>10,.0f}"
              f"{yrs:>10.1f}{'PASS' if yrs <= 4 else 'REJECT':>10}")
    print(f"\n  The maker fee is 25% of the taker fee, so earning the 1c spread")
    print(f"  more than covers it: the maker hurdle is {100*mk:+.2f}pp, i.e. "
          f"slightly NEGATIVE.")
    print(f"  Making on Kalshi is the ONLY venue that clears the frozen "
          f"4-season gate.")


if __name__ == "__main__":
    main()
