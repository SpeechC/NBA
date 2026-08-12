"""Is the CBB total systematically biased in the last week of the season?

PRE-SPECIFIED: primary window = final 7 calendar days of the regular-season
file (2024-03-11 .. 2024-03-17). One test. The window-length sweep that follows
is SENSITIVITY, not confirmation, and is corrected with a null-of-max.

NULL DESIGN. Random *contiguous* windows of the same length, not random
subsets. Games in a window share a slate, opponents and scheduling context, so
a subset null understates the variance and inflates significance.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

from cbb_load import load
from screen_market import central_vs_tail, pp_per_point

N_PERM = 20000
PRICES = {-110: 52.38, -105: 51.22, -102: 50.50}


def cell(d, label):
    n = len(d)
    b, sd = d.r.mean(), d.r.std()
    se = sd / np.sqrt(n)
    over = (d.r > 0).mean()
    sw = np.sqrt(over * (1 - over) / n)
    out = {"window": label, "n": n, "b": round(b, 3), "t": round(b / se, 2),
           "over %": round(100 * over, 2),
           "±95%": round(196 * sw, 2)}
    for p, be in PRICES.items():
        out[f"edge@{p}"] = round(100 * over - be, 2)
    return out


def main():
    g = load().dropna(subset=["close_total", "total_pts"]).copy()
    g["r"] = g.total_pts - g.close_total
    g = g[g.r != 0].sort_values("date").reset_index(drop=True)
    last = g.date.max()

    print("=" * 88)
    print("CBB TOTALS — LAST WEEK OF THE SEASON")
    print("=" * 88)
    print(f"season: {g.date.min():%Y-%m-%d} .. {last:%Y-%m-%d}   games: {len(g)}")

    cut = last - pd.Timedelta(days=6)
    win = g[g.date >= cut]
    rest = g[g.date < cut]
    print(f"\nprimary window: {cut:%Y-%m-%d} .. {last:%Y-%m-%d}  "
          f"({len(win)} games = {100*len(win)/len(g):.1f}% of the season)")
    if 100 * len(win) / len(g) < 5:
        print("  ⚠ fires on <5% of games — R2.4 says prefer 5–10%. "
              "CIs will be wide.")

    rows = [cell(win, "last 7 days"), cell(rest, "rest of season"),
            cell(g, "whole season")]
    print("\n" + pd.DataFrame(rows).to_string(index=False))

    # difference in over-rate, window vs rest
    o1, n1 = (win.r > 0).mean(), len(win)
    o2, n2 = (rest.r > 0).mean(), len(rest)
    sed = np.sqrt(o1 * (1 - o1) / n1 + o2 * (1 - o2) / n2)
    print(f"\n  difference in over-rate: {100*(o1-o2):+.2f}pp  "
          f"(se {100*sed:.2f}pp, z = {(o1-o2)/sed:+.2f}, "
          f"p = {2*(1-st.norm.cdf(abs((o1-o2)/sed))):.3f})")

    # mean-bias difference
    tt = st.ttest_ind(win.r, rest.r, equal_var=False)
    print(f"  difference in mean bias : {win.r.mean()-rest.r.mean():+.3f} pts "
          f"(Welch t = {tt.statistic:+.2f}, p = {tt.pvalue:.3f})")

    # ---- permutation: random CONTIGUOUS windows of the same size ----
    rng = np.random.default_rng(5)
    k = len(win)
    v = (g.r > 0).values.astype(float)
    starts = rng.integers(0, len(g) - k, N_PERM)
    null = np.array([v[s:s + k].mean() for s in starts])
    pct = 100 * (null < o1).mean()
    print(f"\n  permutation (random contiguous {k}-game windows, {N_PERM:,} draws):")
    print(f"    observed over-rate {100*o1:.2f}%  |  null mean {100*null.mean():.2f}%, "
          f"sd {100*null.std():.2f}pp")
    print(f"    2.5th–97.5th pct of null: "
          f"{100*np.quantile(null,.025):.2f}% .. {100*np.quantile(null,.975):.2f}%")
    print(f"    observed sits at the {pct:.1f}th percentile   "
          f"[{'SIGNIFICANT' if pct<2.5 or pct>97.5 else 'NOT SIGNIFICANT'}]")

    # ---- where does the bias live in this window ----
    ct = central_vs_tail(win.r)
    print(f"\n  central/tail split inside the window: "
          f"b {win.r.mean():+.3f} = central {ct['central']:+.3f} "
          f"+ tail {ct['tail']:+.3f}")
    print(f"  pp per point in the window: {pp_per_point(win.r):.2f}")

    # ---- sensitivity sweep (NOT confirmation) ----
    print("\n" + "-" * 88)
    print("SENSITIVITY: other window lengths — reported for honesty, "
          "corrected with a null-of-max")
    print("-" * 88)
    lens = [3, 5, 7, 10, 14, 21]
    srows, devs, sizes = [], [], []
    for L in lens:
        w = g[g.date >= last - pd.Timedelta(days=L - 1)]
        srows.append(cell(w, f"last {L} days"))
        devs.append(abs((w.r > 0).mean() - 0.5))
        sizes.append(len(w))
    print(pd.DataFrame(srows).to_string(index=False))

    mx = max(devs)
    nullmax = np.empty(N_PERM // 4)
    for i in range(len(nullmax)):
        ms = []
        for kk in sizes:
            s = rng.integers(0, len(g) - kk)
            ms.append(abs(v[s:s + kk].mean() - 0.5))
        nullmax[i] = max(ms)
    print(f"\n  max |over-rate − 50%| across {len(lens)} windows = {100*mx:.2f}pp")
    print(f"  null-of-max: mean {100*nullmax.mean():.2f}pp, "
          f"95th pct {100*np.quantile(nullmax,.95):.2f}pp")
    print(f"  observed sits at the {100*(nullmax<mx).mean():.1f}th percentile   "
          f"[{'PASS' if 100*(nullmax<mx).mean()>95 else 'FAIL'}]")


if __name__ == "__main__":
    main()
