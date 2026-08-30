"""
===============================================================================
 M2 LATENCY — are we ahead of the marginal trader? (spec s19)
===============================================================================
 The monitor's own logs cannot answer this. Comparing our halftime stamp to
 the next repricing WE observe measures our poll grid, not the market: over
 the first 9 games that comparison returned 9/9 "ahead" with leads of 34-36s
 -- exactly one poll interval every time. A censored measurement that always
 passes is not a measurement.

 GROUND TRUTH instead. `espn_clocks_wnba.csv` carries the real halftime buzzer
 wallclock per game, and `kalshi_wnba_candles.sqlite` carries 1-minute bars
 for every rung. The gap between them is the MARKET's reaction time, measured
 without reference to anything the monitor does -- across the whole season
 rather than the handful of games the monitor has seen.

 We are ahead of the marginal trader iff our detection latency is shorter
 than that gap. Detection latency is ~U(0, POLL_S) plus the score feed's own
 lag, so the decision number is the fraction of games whose first post-half
 movement lands later than POLL_S.

 HONEST LIMITATION: candles are 1-minute bars, so a movement is located to the
 bar that contains it; sub-minute figures here are the bar boundary, which
 biases measured market latency UPWARD and is therefore optimistic for us.
 The score feed's own lag is NOT measured and adds to our side of the
 comparison -- every figure below is an upper bound on how far ahead we are.
===============================================================================
"""
import collections
import csv
import datetime as dt
import os
import sqlite3
import statistics as S
import sys

LEAGUES = {
    "wnba": {
        "db": "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite",
        "prefix": "KXWNBATOTAL-",
        "clocks": "espn_clocks_wnba.csv",
        # ESPN -> Kalshi codes where they differ
        "code": {"CON": "CONN", "POR": "PDX", "GSV": "GS", "LVA": "LV",
                 "WAS": "WSH", "NYL": "NY"},
    },
    "nba": {
        "db": "/mnt/c/NBA2/Kalshi/data/kalshi_nba_triangle.sqlite",
        "prefix": "KXNBATOTAL-",
        "clocks": "espn_clocks_nba.csv",
        "code": {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP",
                 "UTAH": "UTA", "WSH": "WAS"},
    },
}
REPO = os.path.dirname(os.path.abspath(__file__))
POLL_GRID = ((10, "POLL_S=20, mean case"), (20, "POLL_S=20, worst case"),
             (15, "POLL_S=30, mean case"), (30, "POLL_S=30, worst case"),
             (60, "one minute"), (120, "two minutes"))
F2_BAR = 0.80


def buzzers(league="wnba"):
    """-> {event_key: halftime buzzer unix ts} from ESPN play-by-play."""
    cf = LEAGUES[league]
    out = {}
    for r in csv.DictReader(open(os.path.join(REPO, cf["clocks"]))):
        if not r.get("half_utc"):
            continue
        t = dt.datetime.strptime(r["half_utc"], "%Y-%m-%dT%H:%M:%SZ") \
            .replace(tzinfo=dt.timezone.utc)
        d = dt.datetime.strptime(r["date"], "%Y%m%d")
        key = (d.strftime("%y%b%d").upper()
               + cf["code"].get(r["away"], r["away"])
               + cf["code"].get(r["home"], r["home"]))
        out[key] = t.timestamp()
    return out


def first_moves(half, league="wnba"):
    """-> {event_key: (secs to first quote change, secs to first trade)}.

    Streams the candle table ticker by ticker: the NBA total board is millions
    of rows and must not be materialised.
    """
    cf = LEAGUES[league]
    con = sqlite3.connect(f"file:{cf['db']}?mode=ro", uri=True)
    cur = con.execute(
        "select event_ticker, ticker, end_period_ts, yes_bid_close, "
        "yes_ask_close, volume from candles where period_interval=1 "
        "and ticker like ? order by ticker, end_period_ts", (cf["prefix"] + "%",))
    game = collections.defaultdict(lambda: [None, None])

    def flush(key, s):
        h = half.get(key)
        if not h or not s:
            return
        pre = [x for x in s if x[0] <= h]
        if not pre:
            return
        b0, a0 = pre[-1][1], pre[-1][2]
        for ts, b, a, v in s:
            if ts <= h or ts - h > 3600:
                continue
            if b is not None and (b, a) != (b0, a0):
                g = game[key]
                g[0] = ts - h if g[0] is None else min(g[0], ts - h)
                break
        for ts, b, a, v in s:
            if ts <= h or ts - h > 3600:
                continue
            if v:
                g = game[key]
                g[1] = ts - h if g[1] is None else min(g[1], ts - h)
                break

    cur_tk = None
    cur_key = None
    buf = []
    for e, tk, ts, b, a, v in cur:
        if tk != cur_tk:
            flush(cur_key, buf)
            cur_tk, buf = tk, []
            cur_key = e.split("-")[1] if "-" in e else e
        buf.append((ts, b, a, v))
    flush(cur_key, buf)
    con.close()
    return game


def main(league="wnba"):
    half = buzzers(league)
    game = first_moves(half, league)
    px = sorted(g[0] for g in game.values() if g[0] is not None)
    vo = sorted(g[1] for g in game.values() if g[1] is not None)
    if not px:
        print("no games matched — check team-code mapping")
        return 1
    print(f"[{league.upper()}]  ESPN halftime buzzers {len(half)}; "
          f"games matched to a ladder {len(px)}\n")
    print("TIME FROM THE HALFTIME BUZZER TO THE LADDER'S FIRST MOVEMENT")
    print(f"  quote change : median {S.median(px):3.0f}s   "
          f"p10 {px[len(px)//10]:3.0f}s   p90 {px[9*len(px)//10]:3.0f}s")
    print(f"  first trade  : median {S.median(vo):3.0f}s   "
          f"p10 {vo[len(vo)//10]:3.0f}s   p90 {vo[9*len(vo)//10]:3.0f}s\n")
    print(f"  {'we are ahead if we detect within':<34}{'% of games':>11}"
          f"{'  F2 (>=80%)':>13}")
    for t, lab in POLL_GRID:
        f = sum(1 for x in px if x > t) / len(px)
        print(f"  {str(t) + 's  (' + lab + ')':<34}{100*f:>10.0f}%"
              f"{('  PASS' if f >= F2_BAR else '  FAIL'):>13}")
    need = px[int((1 - F2_BAR) * len(px))]
    print(f"\n  to clear F2 on WORST-CASE detection, POLL_S must be <= "
          f"{need:.0f}s")
    print("  (score-feed lag is unmeasured and adds to our side: these are "
          "upper bounds)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "wnba"))
