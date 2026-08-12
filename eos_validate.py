"""End-of-season overs: honest window selection, central-vs-tail, opener-vs-close.

Three tests, addressing the three ways the earlier result could be an artefact.

TEST 1 — LEAVE-ONE-SEASON-OUT WINDOW SELECTION.
  The 7-day window was chosen after seeing a ladder of windows on all eight
  seasons, so its win rate is an in-sample maximum. Correct procedure: for each
  held-out season, pick the best window using ONLY the other seven, apply that
  window to the held-out season, and aggregate the eight genuinely out-of-sample
  results. If "7 days" keeps being selected and held-out overs still clear
  break-even, the anomaly survives its own selection.

  Plus a permutation control: shuffle the residual sign within each season and
  re-run the entire LOSO procedure. That distribution is what the procedure
  returns when there is nothing there.

TEST 2 — IS THE BIAS CENTRAL OR A TAIL ARTEFACT?
  A positive MEAN residual can come from a few 30-point overs while the median
  sits at zero -- that pattern was already found on three totals markets and is
  not payoff-relevant. What matters is a shift THROUGH zero: median > 0, trimmed
  mean > 0, and P(residual>0) above break-even together.

TEST 3 — OPENER VERSUS CLOSE.
  Grading the same games at the opening total and at the closing total separates
  two worlds. If overs win more at the opener, the market discovers the effect
  during the day and the edge is partly arbitraged -- which makes entry timing
  the whole strategy. If the two are equal, the CLOSING market retains the bias,
  which is far more valuable and far more unusual.

Window variable is DAYS UNTIL THE END OF THE REGULAR SEASON, not a calendar
month, so seasons ending on different dates are handled correctly.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

BE = 110 / 210
WINDOWS = [3, 5, 7, 10, 14, 21, 30]


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open_total"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close_total", "open_total", "date", "actual"])
    d = d[d["close_total"].between(150, 300)]
    d["resid"] = d["actual"] - d["close_total"]
    d["resid_open"] = d["actual"] - d["open_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    return d


def pick_window(train, col="resid"):
    """Best window by over-rate on the training seasons."""
    best, best_w = -1, None
    for k in WINDOWS:
        s = train[train["days_left"] <= k]
        if len(s) < 150:
            continue
        r = (s[col] > 0).mean()
        if r > best:
            best, best_w = r, k
    return best_w, best


def loso(d, col="resid"):
    rows = []
    for s in sorted(d["season"].unique()):
        tr, te = d[d["season"] != s], d[d["season"] == s]
        w, tr_rate = pick_window(tr, col)
        held = te[te["days_left"] <= w]
        if len(held) < 20:
            continue
        rows.append({"held-out season": s, "window chosen": w,
                     "train over %": round(100 * tr_rate, 2),
                     "n": len(held),
                     "HELD-OUT over %": round(100 * (held[col] > 0).mean(), 2)})
    return pd.DataFrame(rows)


def main():
    d = load()
    d = d[d["resid"] != 0]
    print(f"{len(d):,} games, {d['season'].nunique()} seasons\n")

    print("=" * 96)
    print("TEST 1 — leave-one-season-out window selection")
    print("=" * 96)
    L = loso(d)
    print(L.to_string(index=False))
    tot_n = L["n"].sum()
    pooled = (L["HELD-OUT over %"] * L["n"]).sum() / tot_n / 100
    se = np.sqrt(pooled * (1 - pooled) / tot_n)
    print(f"\n  pooled genuinely out-of-sample: {tot_n:,} bets, "
          f"{100*pooled:.2f}%  95% CI "
          f"[{100*(pooled-1.96*se):.2f}, {100*(pooled+1.96*se):.2f}]")
    print(f"  ROI at -110: {100*(pooled*(100/110)-(1-pooled)):+.2f}%   "
          f"break-even {100*BE:.2f}%")
    print(f"  window chosen: {L['window chosen'].value_counts().to_dict()}")
    print(f"  seasons above break-even: "
          f"{int((L['HELD-OUT over %'] > 100*BE).sum())}/{len(L)}")

    print("\n  permutation: same LOSO procedure on sign-shuffled residuals")
    null = []
    for _ in range(400):
        p = d.copy()
        p["resid"] = p.groupby("season")["resid"].transform(
            lambda x: x.values * RNG.choice([-1, 1], len(x)))
        Ln = loso(p)
        if len(Ln):
            null.append((Ln["HELD-OUT over %"] * Ln["n"]).sum() / Ln["n"].sum() / 100)
    null = np.array(null)
    print(f"    null {100*null.mean():.2f}% ± {100*null.std():.2f}   "
          f"observed {100*pooled:.2f}%   "
          f"percentile {100*np.mean(null < pooled):.1f}")

    print("\n" + "=" * 96)
    print("TEST 2 — central shift or tail artefact?")
    print("=" * 96)
    for lab, m in (("last 7 days", d["days_left"] <= 7),
                   ("last 14 days", d["days_left"] <= 14),
                   ("rest of season", d["days_left"] > 14)):
        s = d[m]["resid"]
        tm = stats.trim_mean(s, 0.1)
        print(f"  {lab:16} n={len(s):5,}  mean {s.mean():+6.3f}  "
              f"MEDIAN {s.median():+6.2f}  trimmed10% {tm:+6.3f}  "
              f"P(>0) {100*(s>0).mean():5.2f}%  skew {stats.skew(s):+.3f}")
    print("\n  A payoff-relevant shift needs median and trimmed mean above zero,")
    print("  not just the mean.")

    print("\n" + "=" * 96)
    print("TEST 3 — opener versus close: does the market correct?")
    print("=" * 96)
    rows = []
    for lab, m in (("last 7 days", d["days_left"] <= 7),
                   ("last 14 days", d["days_left"] <= 14),
                   ("rest of season", d["days_left"] > 14)):
        s = d[m]
        so = s[s["resid_open"] != 0]
        ov_o = (so["resid_open"] > 0).mean()
        ov_c = (s["resid"] > 0).mean()
        rows.append({"window": lab, "n": len(s),
                     "mean open": round(s["open_total"].mean(), 2),
                     "mean close": round(s["close_total"].mean(), 2),
                     "mean move": round((s["close_total"]-s["open_total"]).mean(), 3),
                     "over % @OPEN": round(100 * ov_o, 2),
                     "over % @CLOSE": round(100 * ov_c, 2),
                     "ROI @open": round(100 * (ov_o*(100/110)-(1-ov_o)), 2),
                     "ROI @close": round(100 * (ov_c*(100/110)-(1-ov_c)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
