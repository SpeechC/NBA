"""
===============================================================================
 HALFTIME REPRICE ECONOMICS — what passing F2 would have been worth (s22)
===============================================================================
 s20 failed the prototype on F2: our detection latency (17.6s feed lag plus
 the poll interval) exceeds the market's 30-32s reaction, so we are not
 reliably ahead of the marginal trader. That is a statement about SPEED. It
 leaves the prior question unasked: if we HAD been fast enough, would there
 have been anything to take?

 This measures the prize and the bar.

   PRIZE  the ladder's move across halftime, at rungs that can actually be
          traded, net of the fee and the half-spread crossed.
   BAR    that prize is only collectable with the DIRECTION right. Solving
          (2q-1)*|move| = cost for q gives the directional accuracy a
          latency strategy would need to break even.

 The natural candidate signal is tested against the bar: fade the price drift
 over the five minutes before the buzzer, on the theory that the pre-buzzer
 mid is stale and reverts once the book re-opens.

 HONEST LIMITATIONS. (1) Mids, not fills: a mid can move because bids are
 pulled harder than asks, with no tradeable price at either end, so |move| is
 an UPPER bound on what a taker could capture. (2) Candles are 1-minute bars.
 (3) The post window is buzzer+4..15min, inside a ~15-minute break, so no game
 time elapses between the two observations.
===============================================================================
"""
import math
import os
import sqlite3
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m2_latency as M                                        # noqa: E402

ATM = (0.25, 0.75)          # rungs quoted mid-range before the buzzer
TIGHT = 0.02                # "tradeable" spread ceiling
BANDS = ((0, 0.02, "<=2c (tight)"), (0.02, 0.05, "2-5c"),
         (0.05, 0.10, "5-10c"), (0.10, 9, ">10c (wide)"))


def fee(p):
    return 0.07 * p * (1 - p)


def observations(league):
    """Per rung-game: pre-buzzer mid/spread, the move across halftime, and the
    pre-buzzer drift (the only signal available before the fact)."""
    cf = M.LEAGUES[league]
    half = M.buzzers(league)
    con = sqlite3.connect(f"file:{cf['db']}?mode=ro", uri=True)
    cur = con.execute(
        "select event_ticker, ticker, end_period_ts, yes_bid_close, "
        "yes_ask_close, volume from candles where period_interval=1 "
        "and ticker like ? order by ticker, end_period_ts", (cf["prefix"] + "%",))
    out, tk_cur, key_cur, buf = [], None, None, []

    def flush(key, s):
        h = half.get(key)
        if not h or len(s) < 6:
            return
        pre = [x for x in s if x[0] <= h and x[1] is not None]
        post = [x for x in s if h + 240 <= x[0] <= h + 900 and x[1] is not None]
        if len(pre) < 2 or not post:
            return
        old = [x for x in pre if x[0] <= pre[-1][0] - 300]
        if not old:
            return
        m0 = (pre[-1][1] + pre[-1][2]) / 200.0
        m1 = (post[0][1] + post[0][2]) / 200.0
        out.append({"key": key, "m0": m0, "move": m1 - m0,
                    "sp": (pre[-1][2] - pre[-1][1]) / 100.0,
                    "drift": m0 - (old[-1][1] + old[-1][2]) / 200.0,
                    "vol": sum(x[3] or 0 for x in s if h < x[0] <= h + 240)})

    for e, tk, ts, b, a, v in cur:
        if tk != tk_cur:
            flush(key_cur, buf)
            tk_cur, buf = tk, []
            key_cur = e.split("-")[1] if "-" in e else e
        buf.append((ts, b, a, v))
    flush(key_cur, buf)
    con.close()
    return [x for x in out if ATM[0] <= x["m0"] <= ATM[1]]


def main(leagues=("wnba", "nba")):
    for lg in leagues:
        r = observations(lg)
        print(f"\n{'='*74}\n{lg.upper()}  halftime reprice, rungs quoted "
              f"{ATM[0]:.0%}-{ATM[1]:.0%} pre-buzzer  (n={len(r)}, "
              f"{len({x['key'] for x in r})} games)\n{'='*74}")
        print(f"  {'pre-buzzer spread':<20}{'n':>6}{'|move|':>9}{'cost':>8}"
              f"{'net':>9}{'zero-vol':>11}")
        for lo, hi, lab in BANDS:
            s = [x for x in r if lo < x["sp"] <= hi]
            if len(s) < 25:
                continue
            mv = S.mean([abs(x["move"]) for x in s])
            c = S.mean([fee(x["m0"]) + x["sp"] / 2 for x in s])
            z = 100 * sum(1 for x in s if not x["vol"]) / len(s)
            print(f"  {lab:<20}{len(s):>6}{100*mv:>8.2f}c{100*c:>7.2f}c"
                  f"{100*(mv-c):>+8.2f}c{z:>10.0f}%")

        t = [x for x in r if x["sp"] <= TIGHT]
        mv = S.mean([abs(x["move"]) for x in t])
        c = S.mean([fee(x["m0"]) + x["sp"] / 2 for x in t])
        q = (c / mv + 1) / 2
        dr = [x["drift"] for x in t]
        mo = [x["move"] for x in t]
        mx, my = S.mean(dr), S.mean(mo)
        den = sum((a - mx) ** 2 for a in dr)
        beta = sum((a - mx) * (b - my) for a, b in zip(dr, mo)) / den if den else 0
        cor = beta * math.sqrt(den / max(1e-12, sum((b - my) ** 2 for b in mo)))
        fade = [(-1 if x["drift"] > 0 else 1) * x["move"] - fee(x["m0"])
                - x["sp"] / 2 for x in t if x["drift"]]
        print(f"\n  TRADEABLE SUBSET (spread <= {TIGHT:.0%}), n={len(t)}")
        print(f"    mean |move| {100*mv:.2f}c   cost {100*c:.2f}c   "
              f"net if direction known {100*(mv-c):+.2f}c")
        print(f"    >> BREAK-EVEN DIRECTIONAL ACCURACY: {100*q:.1f}%")
        print(f"    mean SIGNED move {100*my:+.2f}c  "
              f"(0 under a martingale; see s22 open question)")
        print(f"    fade-the-drift: beta {beta:+.3f}, corr {cor:+.3f}, "
              f"net {100*S.mean(fade):+.2f}c/contract")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ("wnba", "nba")))
