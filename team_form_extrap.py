"""Does the totals line reflect the TREND more than the REVERSION?

The hypothesis is that the market extrapolates a team's recent scoring form and
under-weights the reversion that follows. That claim has an exact benchmark.

    form = mean(last SHORT games' points) - mean(last LONG games' points)

  NAIVE EXTRAPOLATION  the market believes the recent stretch outright and adds
                       the full deviation to its forecast:   c_market = 1.0
  CORRECT PRICING      the market shrinks by the true persistence:
                       c_market = c_true

So c_market is read against BOTH poles, not against zero. The prior run put
pooled c_market at 0.389 and c_true at 0.408, i.e. essentially correct. This
script asks whether the hypothesis survives anywhere more specific:

  1. NONLINEARITY   does the market over-weight form at the EXTREMES, where an
                    extrapolation story would bite hardest?
  2. HORIZON        does the mispricing depend on how the trend is measured?
                    SHORT in {5, 10, 20} against LONG = 40, ALL reported, so
                    this is a robustness sweep and not a search for a winner.
  3. INTRADAY       does the line MOVE with form from open to close, and if so
                    does it move too far? scoring_surprise.py documented
                    "recent scoring surprise -> public Over demand -> the total
                    rises". Movement with form is not mispricing; OVERSHOOT is.
                    Compared as the gap measured against the OPEN vs the CLOSE.

Strictly prior-only throughout: shift(1) within season.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import team_form as TF
from data_split import SPLIT_DATE
from dispersion_priced import ols

LONG, MINL = 40, 20


def panel(L, short):
    g = L.groupby(["yr", "team"])["pts"]
    L = L.copy()
    L["s"] = g.transform(
        lambda s: s.shift(1).rolling(short, min_periods=short).mean())
    L["l"] = g.transform(
        lambda s: s.shift(1).rolling(LONG, min_periods=MINL).mean())
    L["form"] = L["s"] - L["l"]
    F = L.dropna(subset=["form", "open"])
    G = F.groupby("gid", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"), n=("form", "size"),
        form=("form", "sum"), lvl=("l", "sum"), total=("total", "first"),
        open=("open", "first"), actual=("actual", "first"))
    G = G[G["n"] == 2].copy()
    G["e"] = G["actual"] - G["total"]
    G["e_open"] = G["actual"] - G["open"]
    G["move"] = G["total"] - G["open"]
    return G


def coefs(x, y):
    X = np.column_stack([x["form"].values, x["lvl"].values])
    b, se, t = ols(x[y].values, X)
    return b[1], t[1]


def main():
    L = TF.build()
    L["open"] = pd.to_numeric(L["open"], errors="coerce") if "open" in L \
        else np.nan
    if L["open"].isna().all():
        m = TF.refs.build()
        m["gid"] = m["GAME-ID"].astype(str).str.strip()
        L = L.drop(columns=["open"]).merge(
            m[["gid", "open"]].drop_duplicates("gid"), on="gid", how="left")

    print("=" * 96)
    print("1 — WHERE DOES c_market SIT BETWEEN 'NAIVE TREND' (1.0) AND "
          "'CORRECT' (c_true)?")
    print("=" * 96)
    G = panel(L, 10)
    print(f"  {'window':14}{'c_true':>9}{'c_market':>10}{'gap':>9}{'t':>7}"
          f"{'naive err':>11}{'actual err':>12}{'% of naive':>12}")
    for lab, x in (("development", G[G["date"] < SPLIT_DATE]),
                   ("holdout", G[G["date"] >= SPLIT_DATE]), ("pooled", G)):
        ct, _ = coefs(x, "actual")
        cm, _ = coefs(x, "total")
        ge, gt = coefs(x, "e")
        naive = abs(1.0 - ct)
        act = abs(cm - ct)
        print(f"  {lab:14}{ct:+9.4f}{cm:+10.4f}{ge:+9.4f}{gt:7.2f}"
              f"{naive:11.4f}{act:12.4f}{100*act/naive:11.1f}%")
    print("\n  'naive err'  = how far a full-extrapolation line would be from "
          "truth")
    print("  'actual err' = how far the real closing line is from truth")

    print("\n" + "=" * 96)
    print("2 — NONLINEARITY: does the market over-weight form at the EXTREMES?")
    print("=" * 96)
    q = G["form"].abs().quantile([1/3, 2/3]).values
    G["tier"] = np.where(G["form"].abs() <= q[0], "small",
                         np.where(G["form"].abs() <= q[1], "mid", "EXTREME"))
    print(f"  {'|form| tier':14}{'n':>7}{'c_true':>10}{'t':>7}{'c_market':>11}"
          f"{'t':>7}{'gap':>9}{'t':>7}")
    for tier in ("small", "mid", "EXTREME"):
        x = G[G["tier"] == tier]
        ct, tt = coefs(x, "actual")
        cm, tm = coefs(x, "total")
        ge, gt = coefs(x, "e")
        print(f"  {tier:14}{len(x):7,}{ct:+10.4f}{tt:7.2f}{cm:+11.4f}{tm:7.2f}"
              f"{ge:+9.4f}{gt:7.2f}")

    print("\n" + "=" * 96)
    print("3 — HORIZON SWEEP: SHORT in {5,10,20} vs LONG=40. ALL reported.")
    print("=" * 96)
    print(f"  {'SHORT':>7}{'n':>8}{'c_true':>10}{'c_market':>11}{'gap':>9}"
          f"{'t':>7}{'% of naive':>12}")
    for s in (5, 10, 20):
        x = panel(L, s)
        ct, _ = coefs(x, "actual")
        cm, _ = coefs(x, "total")
        ge, gt = coefs(x, "e")
        print(f"  {s:>7}{len(x):8,}{ct:+10.4f}{cm:+11.4f}{ge:+9.4f}{gt:7.2f}"
              f"{100*abs(cm-ct)/abs(1.0-ct):11.1f}%")

    print("\n" + "=" * 96)
    print("4 — INTRADAY: does the line MOVE with form, and does it OVERSHOOT?")
    print("=" * 96)
    x = G.dropna(subset=["open", "move"])
    cmv, tmv = coefs(x, "move")
    co, to_ = coefs(x, "open")
    ct, _ = coefs(x, "actual")
    cc, _ = coefs(x, "total")
    geo, gto = coefs(x, "e_open")
    gec, gtc = coefs(x, "e")
    print(f"  n={len(x):,}")
    print(f"  form -> OPENING total   {co:+.4f} (t={to_:+.2f})")
    print(f"  form -> CLOSING total   {cc:+.4f}")
    print(f"  form -> open->close MOVE {cmv:+.4f} (t={tmv:+.2f})"
          f"   [does the line drift toward form during the day?]")
    print(f"  truth (form -> actual)  {ct:+.4f}")
    print(f"\n  gap vs the OPEN   {geo:+.4f} (t={gto:+.2f})   "
          f"[was the open already right?]")
    print(f"  gap vs the CLOSE  {gec:+.4f} (t={gtc:+.2f})   "
          f"[did the day's move overshoot?]")
    print(f"\n  OVERSHOOT TEST: the move is {cmv:+.4f} per unit of form.")
    print(f"  For the close to overshoot, the open must be closer to truth "
          f"than the close.")
    print(f"    |open - truth|  = {abs(co-ct):.4f}")
    print(f"    |close - truth| = {abs(cc-ct):.4f}")
    print(f"    -> the day's move made the line "
          f"{'WORSE (overshoot)' if abs(cc-ct) > abs(co-ct) else 'BETTER (correction)'}")


if __name__ == "__main__":
    main()
