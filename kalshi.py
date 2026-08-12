"""Would the move model be profitable on Kalshi?

Kalshi is an exchange, not a sportsbook. Contracts settle at $1 or $0 and trade
at a price in cents that IS the implied probability. The fee is curved rather
than a flat vig:

    fee_per_contract = 0.07 * P * (1 - P)

which peaks at P = 0.50 (1.75c) and falls toward the wings. A totals bet struck
at a fair number sits near 50c, i.e. at the worst point of the curve.

Break-even at price P is therefore  w = P + fee, so at P = 0.50:

    Kalshi taker   51.75%     vs  -110  52.38%   -105  51.22%
    Kalshi maker   50.00%     (Kalshi has run zero maker fees; a resting order
                               that fills pays no trading fee)

Maker pricing is the interesting case and the reason this is worth computing:
it removes the vig entirely, which is a bigger change than any model improvement
found in this project.

Economics per contract at price P with fee f:
    risked     = P + f
    win        = +(1 - P - f)
    lose       = -(P + f)
    E[profit]  = w - P - f
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds

PRICE = 0.50                      # a totals bet at a fair number
TAKER_FEE = 0.07 * PRICE * (1 - PRICE)      # 0.0175
MAKER_FEE = 0.0


def load(spec):
    d = pd.read_csv(f"staking_bets_{spec}.csv", parse_dates=["date"])
    d = d[d["actual_total"] != d["open_total"]].copy()
    side = np.sign(d["pm"])
    over = d["actual_total"] > d["open_total"]
    d["won"] = np.where(side > 0, over, ~over)
    return ds.tag(d)


def econ(w, fee, price=PRICE):
    risked = price + fee
    return {"break-even %": round(100 * (price + fee), 2),
            "ROI %": round(100 * (w - price - fee) / risked, 2)}


def main():
    venues = {
        "-110 (book)": ("book", 110 / 210),
        "-105 (book)": ("book", 105 / 205),
        "Kalshi taker": ("kalshi", TAKER_FEE),
        "Kalshi maker": ("kalshi", MAKER_FEE),
    }
    rows = []
    for spec in ("A", "D"):
        d = load(spec)
        for thr in (0.0, 0.75, 1.25):
            for lab, s in (("DEV", ds.dev(d)), ("HOLDOUT", d[d["is_holdout"]])):
                sub = s[s["pm"].abs() > thr]
                if len(sub) < 50:
                    continue
                w = sub["won"].mean()
                r = {"spec": spec, "thr": thr, "set": lab, "n": len(sub),
                     "win %": round(100 * w, 2)}
                for vname, (kind, param) in venues.items():
                    if kind == "book":
                        be = param
                        payout = (1 - param) / param
                        roi = w * payout - (1 - w)
                    else:
                        be = PRICE + param
                        roi = (w - PRICE - param) / (PRICE + param)
                    r[vname] = round(100 * roi, 2)
                    r[f"{vname} BE"] = round(100 * be, 2)
                rows.append(r)

    t = pd.DataFrame(rows)
    cols = ["spec", "thr", "set", "n", "win %"] + list(venues)
    print("=" * 104)
    print("ROI % by venue — same bets, same sides, only the cost of trading changes")
    print("=" * 104)
    print(t[cols].to_string(index=False))

    print("\nbreak-even win rate required:")
    for vname in venues:
        print(f"  {vname:16} {t[f'{vname} BE'].iloc[0]:.2f}%")

    print("\n" + "=" * 104)
    print("Dollar view, $100 base, quadratic capped staking, HOLDOUT only")
    print("=" * 104)
    import staking
    for spec in ("A", "D"):
        d = load(spec)
        ho = d[d["is_holdout"]]
        for thr in (0.0, 0.75, 1.25):
            sub = ho[ho["pm"].abs() > thr].copy()
            if len(sub) < 50:
                continue
            sub["stake_$"] = staking.stake_dollars(sub["pm"])
            risked = sub["stake_$"].sum()
            w = sub["won"].mean()
            line = {"spec": spec, "thr": thr, "bets": len(sub),
                    "risked $": round(risked)}
            for vname, (kind, param) in venues.items():
                if kind == "book":
                    payout = (1 - param) / param
                    won = (sub["stake_$"] * np.where(sub["won"], payout, -1)).sum()
                else:
                    # scale: stake_$ is the amount risked = (P+f) per unit
                    unit = PRICE + param
                    won = (sub["stake_$"] / unit
                           * np.where(sub["won"], 1 - unit, -unit)).sum()
                line[vname] = round(won)
            print(line)


if __name__ == "__main__":
    main()
