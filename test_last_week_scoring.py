"""Is there a MEAN SHIFT IN TOTAL POINTS SCORED in the last 7 days?

Distinct from test_last_week.py, which asked whether the LINE was wrong. Points
scored and line error are different quantities, and they come apart: scoring can
fall while the book lowers totals to match, giving a real shift with no bias.

    total_pts  =  close_total  +  residual
    Δ points   =  Δ line       +  Δ residual
                  ^ what the book anticipated   ^ what it missed

Only the second term is bettable. Reporting all three.

TWO CONFOUNDS, both handled below:
  * COMPOSITION. The last week is conference tournaments: the teams still
    playing are the ones that advanced, not a random draw. A raw mean shift may
    be entirely a change in who is on the floor.
  * TEMPORAL CLUSTERING. Games in a window share slates and opponents, so the
    null uses random CONTIGUOUS windows, not random subsets.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

from cbb_load import load

N_PERM = 20000
WINDOW_DAYS = 7


def main():
    g = load().dropna(subset=["close_total", "total_pts"]).copy()
    g["resid"] = g.total_pts - g.close_total
    g = g.sort_values("date").reset_index(drop=True)
    last = g.date.max()
    cut = last - pd.Timedelta(days=WINDOW_DAYS - 1)
    win, rest = g[g.date >= cut], g[g.date < cut]

    print("=" * 84)
    print("CBB — MEAN SHIFT IN TOTAL POINTS SCORED, LAST 7 DAYS")
    print("=" * 84)
    print(f"window {cut:%Y-%m-%d} .. {last:%Y-%m-%d}   "
          f"{len(win)} games ({100*len(win)/len(g):.1f}% of season) vs {len(rest)}")

    print("\n" + "-" * 84)
    print("DECOMPOSITION:  Δ points = Δ line + Δ residual")
    print("-" * 84)
    rows = []
    for col, name in (("total_pts", "total points SCORED"),
                      ("close_total", "closing TOTAL (the line)"),
                      ("resid", "residual (points − line)")):
        a, b = win[col], rest[col]
        t = st.ttest_ind(a, b, equal_var=False)
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        rows.append({
            "quantity": name, "last 7d": round(a.mean(), 2),
            "rest": round(b.mean(), 2), "Δ": round(d, 2),
            "se": round(se, 2), "t": round(t.statistic, 2),
            "p": round(t.pvalue, 4),
            "95% CI": f"({d-1.96*se:+.2f}, {d+1.96*se:+.2f})",
        })
    print(pd.DataFrame(rows).to_string(index=False))

    # ---- permutation on the raw scoring shift, contiguous windows ----
    rng = np.random.default_rng(17)
    k = len(win)
    v = g.total_pts.values.astype(float)
    obs = win.total_pts.mean()
    starts = rng.integers(0, len(g) - k, N_PERM)
    null = np.array([v[s:s + k].mean() for s in starts])
    pct = 100 * (null < obs).mean()
    print(f"\npermutation — random contiguous {k}-game windows ({N_PERM:,} draws):")
    print(f"  observed mean total {obs:.2f}   null mean {null.mean():.2f}, "
          f"sd {null.std():.2f}")
    print(f"  2.5th–97.5th pct: {np.quantile(null,.025):.2f} .. "
          f"{np.quantile(null,.975):.2f}")
    print(f"  observed at the {pct:.1f}th percentile   "
          f"[{'SIGNIFICANT' if pct<2.5 or pct>97.5 else 'NOT SIGNIFICANT'}]")

    # ---- composition control: same teams, both periods ----
    print("\n" + "-" * 84)
    print("COMPOSITION CONTROL — teams appearing in BOTH periods, paired")
    print("-" * 84)
    lng = pd.concat([
        g[["date", "TEAM_h", "total_pts"]].rename(columns={"TEAM_h": "team"}),
        g[["date", "TEAM_r", "total_pts"]].rename(columns={"TEAM_r": "team"}),
    ])
    lng["late"] = lng.date >= cut
    piv = lng.groupby(["team", "late"]).total_pts.agg(["mean", "size"]).unstack()
    both = piv.dropna()
    both = both[(both[("size", False)] >= 5) & (both[("size", True)] >= 1)]
    diff = both[("mean", True)] - both[("mean", False)]
    tt = st.ttest_1samp(diff, 0)
    print(f"  teams in both periods (≥5 early games): {len(both)}")
    print(f"  mean within-team change in game total: {diff.mean():+.2f} pts")
    print(f"    se {diff.std()/np.sqrt(len(diff)):.2f}, t = {tt.statistic:+.2f}, "
          f"p = {tt.pvalue:.4f}")
    print(f"    95% CI ({diff.mean()-1.96*diff.std()/np.sqrt(len(diff)):+.2f}, "
          f"{diff.mean()+1.96*diff.std()/np.sqrt(len(diff)):+.2f})")

    # did the line follow the same teams down?
    lngl = pd.concat([
        g[["date", "TEAM_h", "close_total"]].rename(columns={"TEAM_h": "team"}),
        g[["date", "TEAM_r", "close_total"]].rename(columns={"TEAM_r": "team"}),
    ])
    lngl["late"] = lngl.date >= cut
    pl = lngl.groupby(["team", "late"]).close_total.mean().unstack().dropna()
    pl = pl.loc[pl.index.intersection(both.index)]
    dl = pl[True] - pl[False]
    print(f"  mean within-team change in the LINE  : {dl.mean():+.2f} pts")
    print(f"  => book anticipated {100*dl.mean()/diff.mean():.0f}% of the "
          f"within-team scoring change"
          if diff.mean() else "")

    # ---- daily trace for context ----
    print("\n" + "-" * 84)
    print("Final 14 days: scoring vs line, day by day")
    print("-" * 84)
    d = g[g.date >= last - pd.Timedelta(days=13)]
    tr = d.groupby(d.date.dt.date).agg(
        n=("total_pts", "size"), pts=("total_pts", "mean"),
        line=("close_total", "mean"), resid=("resid", "mean")).round(2)
    print(tr.to_string())


if __name__ == "__main__":
    main()
