"""Forward paper-trading harness for the frozen totals-movement models.

This does not backtest. It runs forward, one slate at a time, and its whole
purpose is to produce evidence that the six-season sample cannot: performance on
games nobody has looked at.

Why this matters more than any further modelling: roughly 22 model variants have
been evaluated on 2019-2024. Every additional in-sample test makes the winner
more likely to be the luckiest rather than the best. Only out-of-sample data adds
information now.

------------------------------------------------------------------------------
DAILY WORKFLOW
------------------------------------------------------------------------------
  1.  As soon as totals post, capture them:
          python paper_trade.py capture --date 2026-10-21
      Reads openers from the configured source and writes them to the log with a
      UTC timestamp. Timestamp matters: alpha decay showed 92.4% of the edge is
      gone by the first repost, so how quickly you capture is itself data.

  2.  Generate bets:
          python paper_trade.py bet --date 2026-10-21
      Applies the FROZEN model (spec A, threshold 1.25) to the captured openers
      and writes a bet ticket. Nothing here is fitted at run time -- the model is
      refit only on games that have already finished.

  3.  After the games, grade:
          python paper_trade.py grade --date 2026-10-21
      Records closing total, actual total, CLV and win/loss.

  4.  Any time:
          python paper_trade.py report
      Running totals, and the honest comparison against the backtest anchor.

------------------------------------------------------------------------------
WHAT YOU MUST SUPPLY
------------------------------------------------------------------------------
  * An odds source for openers. Two are supported:
      - "manual": a CSV you fill in yourself (works today, no API needed)
      - "oddsapi": The Odds API, needs ODDS_API_KEY in the environment
    Manual is not a downgrade for this purpose -- you only need ~5 numbers per
    game, and you are trying to measure whether YOU can get the opener.
  * A rolling team-stats history, so lagged pace/efficiency features exist for
    the current season. `refresh_history` rebuilds this from the season to date.

------------------------------------------------------------------------------
WHAT TO RECORD THAT THE BACKTEST COULD NOT
------------------------------------------------------------------------------
  * the timestamp you saw the opener, and the timestamp you could have bet
  * the PRICE at the opener (-110? -115?) -- this decides viability by itself:
    break-even needs ~1.35 pts of CLV at -110 but only ~0.69 at -105
  * the LIMIT available at that number
  * whether the number was still there when you tried
These four are the binding constraints and none of them exist in historical data.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from models_frozen import (BACKTEST, FROZEN_ON, OPERATING_THRESHOLD, SPECS,
                           add_pace_terms, make_estimator)

LOG_DIR = Path("paper_trades")
OPENERS = LOG_DIR / "openers.csv"
BETS = LOG_DIR / "bets.csv"
GRADED = LOG_DIR / "graded.csv"

OPENER_COLUMNS = [
    "date", "gid", "home_team", "away_team",
    "open_total", "open_price",        # e.g. -110 ; the price is not optional
    "captured_utc",                    # when you saw it
    "limit_available",                 # max stake offered at that number
    "book",
]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init():
    LOG_DIR.mkdir(exist_ok=True)
    if not OPENERS.exists():
        pd.DataFrame(columns=OPENER_COLUMNS).to_csv(OPENERS, index=False)
    print(f"initialised {LOG_DIR}/")
    print(f"fill {OPENERS} by hand, or wire an odds source, then run `bet`")


def capture_template(date):
    """Write a blank row set for a slate, to be filled in by hand."""
    init()
    print(f"\nAdd one row per game to {OPENERS}, for example:\n")
    print(",".join(OPENER_COLUMNS))
    print(f"{date},0022600001,Boston,Miami,224.5,-110,{_now()},2000,Pinnacle")
    print("\nCapture the opener as early as you can and record the timestamp "
          "honestly -- if you routinely capture 20 minutes late, the log should "
          "show that, because it is the thing being tested.")


def load_openers(date=None):
    if not OPENERS.exists():
        raise SystemExit("no openers logged yet -- run `init` first")
    df = pd.read_csv(OPENERS)
    if date:
        df = df[df["date"].astype(str) == str(date)]
    return df


def make_bets(date, threshold=OPERATING_THRESHOLD, spec="A"):
    """Apply the frozen model to captured openers.

    Requires current-season lagged features. Until a live feature pipeline is
    wired in, this refuses rather than guessing -- a paper trade produced from
    stale or invented features is worse than no paper trade.
    """
    op = load_openers(date)
    if op.empty:
        raise SystemExit(f"no openers captured for {date}")
    feat_path = LOG_DIR / f"features_{date}.csv"
    if not feat_path.exists():
        raise SystemExit(
            f"missing {feat_path}\n"
            f"  The frozen model needs lagged pace/efficiency features for both\n"
            f"  teams ({len(SPECS[spec])} columns, see models_frozen.SPECS['{spec}']).\n"
            f"  Build them from the season to date with refresh_history, or\n"
            f"  supply the file directly. This deliberately does not fabricate\n"
            f"  features when they are unavailable.")
    feats = pd.read_csv(feat_path)
    d = op.merge(feats, on="gid", how="inner")
    d = add_pace_terms(d)
    cols = SPECS[spec]
    missing = [c for c in cols if c not in d.columns]
    if missing:
        raise SystemExit(f"feature file is missing: {missing}")

    model_path = LOG_DIR / f"model_{spec}.pkl"
    if not model_path.exists():
        raise SystemExit(
            f"missing {model_path} -- fit the frozen estimator on all completed\n"
            f"  games to date and pickle it. It must never be fitted on games in\n"
            f"  the slate being predicted.")
    import pickle
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    d["pred_move"] = model.predict(d[cols].values)
    d["side"] = np.where(d["pred_move"].abs() <= threshold, 0,
                         np.sign(d["pred_move"])).astype(int)
    d["bet"] = np.where(d["side"] > 0, "OVER", np.where(d["side"] < 0, "UNDER", ""))
    d["threshold"] = threshold
    d["spec"] = spec
    d["bet_utc"] = _now()
    out = d[d["side"] != 0]
    cols_out = ["date", "gid", "home_team", "away_team", "open_total",
                "open_price", "pred_move", "bet", "spec", "threshold",
                "captured_utc", "bet_utc", "limit_available", "book"]
    keep = [c for c in cols_out if c in out.columns]
    hdr = not BETS.exists()
    out[keep].to_csv(BETS, mode="a", header=hdr, index=False)
    print(f"{len(out)} bets written to {BETS} (of {len(d)} games)")
    if len(d):
        print(f"selection rate {100 * len(out) / len(d):.1f}% "
              f"(backtest was ~20% at threshold {threshold})")
    return out


def grade(date, results_path=None):
    """Attach closing totals and actual results to logged bets."""
    if not BETS.exists():
        raise SystemExit("no bets logged")
    bets = pd.read_csv(BETS)
    bets = bets[bets["date"].astype(str) == str(date)]
    rp = Path(results_path or LOG_DIR / f"results_{date}.csv")
    if not rp.exists():
        raise SystemExit(f"missing {rp} with columns: gid, close_total, actual_total")
    res = pd.read_csv(rp)
    d = bets.merge(res, on="gid", how="inner")
    side = np.where(d["bet"] == "OVER", 1, -1)
    d["clv"] = side * (d["close_total"] - d["open_total"])
    push = d["actual_total"] == d["open_total"]
    over = d["actual_total"] > d["open_total"]
    d["result"] = np.where(push, "PUSH",
                           np.where(np.where(side > 0, over, ~over), "WIN", "LOSS"))
    price = pd.to_numeric(d.get("open_price", -110), errors="coerce").fillna(-110)
    payout = np.where(price > 0, price / 100, 100 / -price)
    d["profit_units"] = np.where(d["result"] == "PUSH", 0.0,
                                 np.where(d["result"] == "WIN", payout, -1.0))
    hdr = not GRADED.exists()
    d.to_csv(GRADED, mode="a", header=hdr, index=False)
    print(f"graded {len(d)} bets for {date}")
    return d


def report():
    if not GRADED.exists():
        raise SystemExit("nothing graded yet")
    d = pd.read_csv(GRADED)
    nz = d[d["result"] != "PUSH"]
    n = len(nz)
    if n == 0:
        raise SystemExit("no settled bets yet")
    w = (nz["result"] == "WIN").mean()
    roi = nz["profit_units"].mean()
    clv = d["clv"].mean()
    from scipy import stats
    lo, hi = stats.beta.ppf([.025, .975],
                            (nz["result"] == "WIN").sum() + .5,
                            n - (nz["result"] == "WIN").sum() + .5)
    print(f"FORWARD PAPER TRADE   (frozen {FROZEN_ON}, threshold {OPERATING_THRESHOLD})")
    print(f"  settled bets   {n}")
    print(f"  win rate       {100 * w:.2f}%   95% CI [{100 * lo:.2f}, {100 * hi:.2f}]")
    print(f"  ROI            {100 * roi:+.2f}%")
    print(f"  mean CLV       {clv:+.3f} pts")
    print(f"  beat close     {100 * (d['clv'] > 0).mean():.1f}%")
    print()
    print(f"  backtest anchor at this threshold: "
          f"ROI {BACKTEST['A'][OPERATING_THRESHOLD]:+.2f}%, CLV +1.844, "
          f"win 54.05%, beat close 66.6%")
    print()
    if n < 300:
        need = 300 - n
        print(f"  NOTE: {n} bets is not yet decisive. At a ~54% true rate you need")
        print(f"  roughly 300+ settled bets before the interval excludes break-even;")
        print(f"  {need} to go, about {need / 159:.1f} seasons at the backtested rate.")
    if "captured_utc" in d.columns and "bet_utc" in d.columns:
        try:
            lag = (pd.to_datetime(d["bet_utc"]) - pd.to_datetime(d["captured_utc"]))
            print(f"  median capture->bet lag: {lag.median()}")
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["init", "capture", "bet", "grade", "report"])
    ap.add_argument("--date")
    ap.add_argument("--threshold", type=float, default=OPERATING_THRESHOLD)
    ap.add_argument("--spec", default="A")
    a = ap.parse_args()
    if a.cmd == "init":
        init()
    elif a.cmd == "capture":
        capture_template(a.date or datetime.now().date().isoformat())
    elif a.cmd == "bet":
        make_bets(a.date, a.threshold, a.spec)
    elif a.cmd == "grade":
        grade(a.date)
    elif a.cmd == "report":
        report()


if __name__ == "__main__":
    main()
