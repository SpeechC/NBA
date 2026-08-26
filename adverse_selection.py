"""
===============================================================================
 ADVERSE SELECTION from the monitor's depth logs (M2, first measurement)
===============================================================================
 `ladder_residual_maker.py` left the programme's only surviving edge at
 +1.24c gross to a MAKER, CI [-0.04,+2.51] -- explicitly before any
 adverse-selection charge. This measures that charge.

 THE IDEA. A maker resting a YES bid is filled when someone sells into it.
 We never see fills (COMPONENT_ROLE = OBSERVER), but the monitor stores the
 top six levels of both books every 30s, so a fill can be INFERRED: when the
 size resting at the best bid falls while the price level holds, someone
 traded against it. Then the question is what the price does next. If the mid
 systematically falls after our hypothetical buy, that drop is adverse
 selection -- we were filled by someone who knew the price was going down.

 THE DECOMPOSITION (standard market-microstructure form):
     realised spread  =  quoted half-spread  -  adverse selection
 A maker keeps the realised spread. If adverse selection exceeds the quoted
 half-spread, making loses money no matter how good the quoting is.

 HONEST LIMITATION, stated up front: a size decrease can be a CANCELLATION
 rather than a trade, and the two are indistinguishable in this data. That
 biases the inferred-fill set toward including non-fills, which dilutes
 measured adverse selection TOWARD ZERO -- i.e. this measurement is
 optimistic for the maker case. The unconditional markout is reported beside
 it as the null: if the two are equal, the "fills" carry no information and
 the inference is not working.
===============================================================================
"""
import glob
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOGS = "/mnt/d/Kalshi/wnba_monitor/monitor2_*.jsonl"
RNG = np.random.default_rng(41)


def load():
    """-> tidy frame of (event, strike, ts, bid, ask, bid_sz, ask_sz)."""
    rows = []
    for p in sorted(glob.glob(LOGS)):
        for ln in open(p):
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("type") != "ladder":
                continue
            ts = r.get("ts_utc")
            for l in r.get("ladder") or []:
                yb = l.get("book_yes_top") or []
                nb = l.get("book_no_top") or []
                if not yb or not nb or l.get("strike") is None:
                    continue
                try:
                    bid, bsz = float(yb[0][0]), float(yb[0][1])
                    nbid, asz = float(nb[0][0]), float(nb[0][1])
                except (TypeError, ValueError, IndexError):
                    continue
                rows.append({"e": r["event"].split("-")[-1],
                             "k": float(l["strike"]), "ts": ts,
                             "bid": bid, "ask": 1.0 - nbid,
                             "bid_sz": bsz, "ask_sz": asz})
    d = pd.DataFrame(rows)
    if not len(d):
        return d
    d["ts"] = pd.to_datetime(d.ts)
    d["mid"] = (d.bid + d.ask) / 2
    d["hsp"] = (d.ask - d.bid) / 2
    return d.sort_values(["e", "k", "ts"]).reset_index(drop=True)


def markouts(d, horizons=(1, 3, 5, 10)):
    """Per rung: infer fills from depth consumption, mark out forward."""
    out = []
    for (e, k), g in d.groupby(["e", "k"]):
        g = g.reset_index(drop=True)
        t = g.ts.values.astype("datetime64[s]").astype(np.int64)
        mid = g.mid.values
        bid, ask = g.bid.values, g.ask.values
        bsz, asz = g.bid_sz.values, g.ask_sz.values
        for i in range(len(g) - 1):
            # inferred BUY fill: size at the best bid fell, level held
            hit_bid = (bid[i + 1] == bid[i]) and (bsz[i + 1] < bsz[i] * 0.9)
            hit_ask = (ask[i + 1] == ask[i]) and (asz[i + 1] < asz[i] * 0.9)
            rec = {"e": e, "k": k, "i": i, "hsp": (ask[i] - bid[i]) / 2,
                   "hit_bid": hit_bid, "hit_ask": hit_ask,
                   "bid": bid[i], "ask": ask[i], "mid": mid[i]}
            for h in horizons:
                j = np.searchsorted(t, t[i] + h * 60)
                rec[f"m{h}"] = mid[j] - mid[i] if j < len(mid) else np.nan
            out.append(rec)
    return pd.DataFrame(out)


def ci(v, keys, B=3000):
    ev = np.unique(keys)
    by = {k: v[keys == k] for k in ev}
    o = []
    for _ in range(B):
        s = np.concatenate([by[x] for x in RNG.choice(ev, len(ev), True)])
        o.append(np.nanmean(s))
    return np.nanpercentile(o, [2.5, 97.5])


def main():
    d = load()
    if not len(d):
        print("no depth rows found")
        return
    print(f"depth observations: {len(d):,} rung-polls, {d.e.nunique()} events, "
          f"{d.k.nunique()} distinct strikes")
    print(f"  resting size at the touch: bid median {d.bid_sz.median():,.0f}, "
          f"ask median {d.ask_sz.median():,.0f} (dollars)")
    print(f"  quoted half-spread: median {d.hsp.median()*100:.2f}c\n")

    mo = markouts(d)
    print(f"transitions analysed: {len(mo):,}; inferred bid-side fills "
          f"{int(mo.hit_bid.sum()):,}, ask-side {int(mo.hit_ask.sum()):,}")
    print("\nMARKOUT after an inferred fill (mid move, cents)")
    print("  a maker who BOUGHT at the bid loses when the mid FALLS\n")
    print(f"  {'horizon':>8} {'n fills':>8} {'markout|fill':>14} "
          f"{'markout|all':>13} {'adverse sel':>12}")
    for h in (1, 3, 5, 10):
        col = f"m{h}"
        f = mo[mo.hit_bid & mo[col].notna()]
        a = mo[mo[col].notna()]
        if len(f) < 30:
            print(f"  {h:>6}m {len(f):>8}   too few")
            continue
        # buying at the bid: adverse selection = -(mid move) after the fill
        adv = -f[col].mean()
        lo, hi = ci((-f[col]).values, f.e.values)
        print(f"  {h:>6}m {len(f):>8} {f[col].mean()*100:>+13.2f}c "
              f"{a[col].mean()*100:>+12.2f}c {adv*100:>+10.2f}c "
              f"CI [{lo*100:+.2f},{hi*100:+.2f}]")

    print("\nTHE MAKER LEDGER (bid side, 5-minute horizon)")
    f = mo[mo.hit_bid & mo.m5.notna()]
    if len(f) >= 30:
        hs = f.hsp.mean()
        adv = -f.m5.mean()
        fee = 0.07 * f.mid.mean() * (1 - f.mid.mean())
        print(f"  quoted half-spread earned   {hs*100:>+6.2f}c")
        print(f"  adverse selection          {-adv*100:>+6.2f}c")
        print(f"  fee at mean price          {-fee*100:>+6.2f}c")
        print(f"  ------------------------------------")
        print(f"  net per filled contract    {(hs-adv-fee)*100:>+6.2f}c")
        print(f"\n  ladder-residual edge measured earlier: +1.24c gross")
        print(f"  net of this adverse-selection charge: "
              f"{(1.24-adv*100):+.2f}c")
    print("\n  CAVEAT: size decreases include cancellations, which dilutes")
    print("  measured adverse selection toward zero. Compare 'markout|fill'")
    print("  with 'markout|all': if they match, the fill inference is inert.")


if __name__ == "__main__":
    main()
