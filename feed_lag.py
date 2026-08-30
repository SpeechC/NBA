"""
===============================================================================
 FEED LAG — the last unmeasured term in F2 (spec s20)
===============================================================================
 `m2_latency.py` measured the MARKET: 32s median from the halftime buzzer to
 the ladder's first movement, over 250 games. That is only half of F2. The
 other half is OUR detection latency, and it has two parts:

     detection latency  =  score-feed lag  +  U(0, POLL_S)

 POLL_S we choose. The feed lag -- how long after the real buzzer the WNBA
 scoreboard endpoint reports `period 2 / Half` -- we do not, and it had never
 been measured. This measures it by differencing the monitor's own first
 halftime detection against the ESPN play-by-play buzzer for the same game.

 Because each observation carries an unknown U(0, POLL_S) phase, the feed lag
 is recovered two ways: mean minus POLL_S/2 (unbiased if the phase is uniform)
 and the minimum observed (an upper bound, tight only with many games). They
 should agree; if they do not, the phase assumption is wrong.
===============================================================================
"""
import datetime as dt
import glob
import json
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m2_latency as M                                        # noqa: E402

LOGS = "/mnt/d/Kalshi/wnba_monitor/monitor2_2026*.jsonl"
F2_BAR = 0.80


def detections(pattern=LOGS):
    """-> {event_key: (first 'Half' detection ts, POLL_S of that session)}."""
    out = {}
    for f in sorted(glob.glob(pattern)):
        poll = 30                       # pre-s19 default
        for ln in open(f):
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("poll_s"):
                poll = r["poll_s"]
                continue
            if r.get("type") != "ladder":
                continue
            st = r.get("game_state") or {}
            if st.get("period") == 2 and \
                    str(st.get("status", "")).lower().startswith("half"):
                k = r["event"].split("-")[1]
                out.setdefault(k, (dt.datetime.fromisoformat(r["ts_utc"]), poll))
    return out


def main():
    buz = M.buzzers()
    det = detections()
    pairs = []
    for k in sorted(set(buz) & set(det)):
        t, poll = det[k]
        pairs.append((k, (t - dt.datetime.fromtimestamp(buz[k], dt.timezone.utc).replace(tzinfo=None)).total_seconds(),
                      poll))
    if len(pairs) < 3:
        print(f"only {len(pairs)} matched games — need ESPN clocks for the "
              f"monitored nights")
        return 1
    print("OUR HALFTIME DETECTION vs THE REAL BUZZER")
    for k, d, p in pairs:
        print(f"  {k:<14}{d:>6.0f}s   (= feed lag + U(0,{p}))")
    ds = [d for _, d, _ in pairs]
    est = S.mean([d - p / 2 for _, d, p in pairs])
    print(f"\n  n={len(ds)}  min {min(ds):.0f}s  median {S.median(ds):.0f}s  "
          f"max {max(ds):.0f}s")
    print(f"  feed lag: {est:.1f}s (mean - POLL_S/2)   "
          f"<= {min(ds):.0f}s (min observed)")

    px = sorted(g[0] for g in M.first_moves(M.buzzers()).values()
                if g[0] is not None)
    print(f"\nF2 WITH THE FEED LAG INCLUDED  ({len(px)} games of market data)")
    print(f"  {'POLL_S':<9}{'detect mean':>13}{'ahead':>8}{'detect worst':>14}"
          f"{'ahead':>8}{'  F2':>7}")
    for p in (30, 20, 15, 10, 5, 0):
        m, w = est + p / 2, est + p
        fm = sum(1 for x in px if x > m) / len(px)
        fw = sum(1 for x in px if x > w) / len(px)
        print(f"  {p:<9}{m:>12.0f}s{100*fm:>7.0f}%{w:>13.0f}s{100*fw:>7.0f}%"
              f"{('PASS' if fm >= F2_BAR else 'FAIL'):>7}")
    tgt = px[int((1 - F2_BAR) * len(px))]
    print(f"\n  F2 needs detection <= {tgt:.0f}s. The feed lag ALONE is "
          f"{est:.0f}s, so no poll cadence clears it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
