"""The ageing problem: Kelly stakes peak exactly when decay risk peaks.

Two things grow together over a strategy's life:
  - the DOLLAR stake, because the bankroll compounds and the edge estimate
    firms up (less shrinkage toward break-even)
  - the HAZARD that the edge has decayed, because markets adapt and
    mechanisms drift

So the largest bets are placed at the moment of greatest doubt. This script
measures the size of that asymmetry and tests three defences.

Estimators compared
  FLAT        $100 per bet, no compounding                    (the frozen rule)
  KELLY-ALL   quarter Kelly, edge from ALL settled bets       (what was simulated)
  KELLY-ROLL  quarter Kelly, edge from the last 500 bets only
  KELLY-STOP  KELLY-ROLL plus the PROSPECTIVE.md rule: suspend after two
              consecutive losing 200-bet blocks

Decay scenarios applied at a fixed point in a 1,900-bet life (~8 seasons).
"""
import warnings

import numpy as np

warnings.filterwarnings("ignore")

B = 100.0 / 110.0
BE = 110.0 / 210.0
FRAC = 0.25
BANK0 = 100_000.0
NBETS = 1900
NSIM = 2000
RNG = np.random.default_rng(31337)


def kelly(p):
    return max((B * p - (1 - p)) / B, 0.0)


def run(outcomes, mode):
    """Return (final bank, peak bank, max drawdown, bets placed, flat P&L)."""
    bank, peak, mdd = BANK0, BANK0, 0.0
    cw = cn = 0
    hist = []
    placed = 0
    blocks_lost = 0
    block_w = block_n = 0
    stopped = False
    for i, w in enumerate(outcomes):
        f = 0.0
        if not stopped:
            if mode == "flat":
                f = 100.0 / bank if bank > 0 else 0.0
            elif cn >= 200:
                if mode == "all":
                    p = (cw + 200 * BE) / (cn + 200)
                else:                       # rolling 500
                    h = hist[-500:]
                    p = (sum(h) + 200 * BE) / (len(h) + 200)
                f = FRAC * kelly(p)
        stake = f * bank
        bank += stake * B if w else -stake
        peak = max(peak, bank)
        mdd = max(mdd, (peak - bank) / peak)
        if f > 0:
            placed += 1
        hist.append(int(w))
        cw += int(w)
        cn += 1
        # suspension rule: two consecutive losing 200-bet blocks
        block_w += int(w)
        block_n += 1
        if block_n == 200:
            blocks_lost = blocks_lost + 1 if block_w / 200 < BE else 0
            if mode == "stop" and blocks_lost >= 2:
                stopped = True
            block_w = block_n = 0
    return bank, peak, mdd, placed, stopped


def scenario(p0, p1, brk):
    p = np.full(NBETS, p0)
    p[brk:] = p1
    return p


def main():
    scen = {
        "no decay (54.8% throughout)": scenario(0.5482, 0.5482, NBETS),
        "halves at bet 1200 (~season 6)": scenario(0.5482, 0.5360, 1200),
        "to break-even at bet 1200": scenario(0.5482, 0.5238, 1200),
        "to break-even at bet 900": scenario(0.5482, 0.5238, 900),
        "to 50% at bet 1200": scenario(0.5482, 0.5000, 1200),
    }
    modes = [("flat", "FLAT $100"), ("all", "KELLY-ALL"),
             ("roll", "KELLY-ROLL"), ("stop", "KELLY-STOP")]

    print("=" * 100)
    print("TERMINAL WEALTH BY DECAY SCENARIO   (2,000 sims, 1,900 bets, "
          "$100k start)")
    print("=" * 100)
    for sname, pv in scen.items():
        print(f"\n  {sname}")
        print(f"    {'method':13}{'median $':>11}{'5th pct':>10}"
              f"{'P(loss)':>9}{'med maxDD':>11}{'med giveback':>14}")
        for mode, lab in modes:
            fin, dd, gb, loss = [], [], [], 0
            for _ in range(NSIM):
                out = RNG.random(NBETS) < pv
                b, pk, m, _, _ = run(out, mode)
                fin.append(b)
                dd.append(m)
                gb.append((pk - b) / max(pk - BANK0, 1e-9)
                          if pk > BANK0 else 0.0)
                loss += b < BANK0
            f = np.array(fin)
            print(f"    {lab:13}{np.median(f):11,.0f}"
                  f"{np.percentile(f,5):10,.0f}{100*loss/NSIM:8.1f}%"
                  f"{100*np.median(dd):10.1f}%"
                  f"{100*np.clip(np.median(gb),0,1):13.1f}%")

    print("\n" + "=" * 100)
    print("WHY: DETECTION LAG OF THE FULL-HISTORY ESTIMATOR")
    print("=" * 100)
    print("  after N settled bets at 54.8%, edge collapses to 50%.")
    print("  how many further bets before the stake is halved / zeroed?")
    print(f"  {'N settled':>11}{'stake at break':>15}{'bets to half':>14}"
          f"{'bets to zero':>14}")
    for N in (400, 800, 1200, 1600):
        cw = 0.5482 * N
        f0 = FRAC * kelly((cw + 200 * BE) / (N + 200))
        half = zero = None
        for k in range(1, 4000):
            p = (cw + 0.5 * k + 200 * BE) / (N + k + 200)
            f = FRAC * kelly(p)
            if half is None and f <= f0 / 2:
                half = k
            if zero is None and f <= 0:
                zero = k
                break
        print(f"  {N:>11,}{100*f0:>14.2f}%{half:>14,}{zero:>14,}")

    print("\n" + "=" * 100)
    print("THE ASYMMETRY, STATED DIRECTLY")
    print("=" * 100)
    out_good = np.ones(NBETS, dtype=bool)
    print("  a 200-bet stretch at 52% (below break-even) costs, in dollars:")
    for N, lab in ((300, "early life"), (900, "mid life"),
                   (1500, "late life")):
        bank = BANK0
        cw = cn = 0
        # grow the bankroll to that point at the measured edge
        for i in range(N):
            w = RNG.random() < 0.5482
            f = FRAC * kelly((cw + 200 * BE) / (cn + 200)) if cn >= 200 else 0.0
            bank += f * bank * B if w else -f * bank
            cw += int(w)
            cn += 1
        start = bank
        for i in range(200):
            w = RNG.random() < 0.52
            f = FRAC * kelly((cw + 200 * BE) / (cn + 200))
            bank += f * bank * B if w else -f * bank
            cw += int(w)
            cn += 1
        print(f"    {lab:12} after {N:,} bets: bankroll ${start:9,.0f} -> "
              f"${bank:9,.0f}   loss ${start-bank:8,.0f} "
              f"({100*(start-bank)/start:5.1f}%)")


if __name__ == "__main__":
    main()
