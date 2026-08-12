"""Compare over-winners to over-losers inside the end-of-season window.

The proposal: rather than testing pre-specified filters, let the data say what
separates the games that went over from the ones that did not.

This is the right instinct and it needs a null, because the operation is a
multiple-comparison machine. Two things are reported side by side:

  OBSERVED  how many features significantly separate winners from losers
  NULL      the same count after SHUFFLING the outcome, repeated. That is what
            "nothing there" looks like after the identical search.

The power arithmetic matters more than the result. With ~537 games split near
50/50, the standard error on a standardised mean difference is sqrt(2/268) =
0.086 SD, so the smallest reliably detectable separation is about 0.24 SD.

A feature strong enough to lift the win rate from 55.9% to 60% would correlate
with the outcome at roughly r = 0.08, i.e. a separation near 0.16 SD -- BELOW
that floor. So the features worth having are undetectable here, and any feature
big enough to detect would be large enough that the market would already price
it. The window is squeezed shut from both sides.

That is a statement about sample size, not about basketball, and no amount of
model sophistication changes it.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)


def main():
    from end_of_season import load
    from models_frozen import add_pace_terms
    from symmetric_features import build

    d = load()
    G = add_pace_terms(build())
    G["gid"] = G["game_id"].astype(str).str.zfill(10)
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)

    feat = [c for c in G.columns
            if c.startswith(("h_f_", "a_f_", "pace_", "oeff_", "deff_"))
            or c in ("implied_minus_open", "dis_open")]
    d = d.merge(G[["gid"] + feat], on="gid", how="inner")
    d["abs_spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce").abs()
    extra = ["close_total", "abs_spread", "wpct_h", "wpct_a", "days_left", "move"]
    feat = feat + [c for c in extra if c in d.columns]

    for W in (7, 10, 14):
        w = d[d["days_left"] <= W].dropna(subset=feat + ["resid"]).copy()
        if len(w) < 100:
            continue
        y = (w["resid"] > 0).values
        X = w[feat].values

        def count_sig(yy):
            ps = []
            for j in range(X.shape[1]):
                a, b = X[yy, j], X[~yy, j]
                if len(a) < 5 or len(b) < 5:
                    ps.append(1.0)
                    continue
                ps.append(stats.ttest_ind(a, b, equal_var=False)[1])
            return np.array(ps)

        p_obs = count_sig(y)
        n_obs = int((p_obs < 0.05).sum())

        null = []
        for _ in range(400):
            yp = RNG.permutation(y)
            null.append(int((count_sig(yp) < 0.05).sum()))
        null = np.array(null)

        print("=" * 100)
        print(f"LAST {W} DAYS — n={len(w):,}  ({y.sum()} over, {(~y).sum()} under)"
              f"   {len(feat)} features tested")
        print("=" * 100)
        print(f"  features with p<0.05: OBSERVED {n_obs}   "
              f"NULL {null.mean():.1f} ± {null.std():.1f}   "
              f"percentile {100*np.mean(null < n_obs):.0f}")
        print(f"  expected by chance at alpha=.05: {0.05*len(feat):.1f}")

        # Benjamini-Hochberg
        order = np.argsort(p_obs)
        thresh = 0.10 * np.arange(1, len(p_obs) + 1) / len(p_obs)
        passed = p_obs[order] <= thresh
        k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
        print(f"  surviving BH FDR q<0.10: {k}")

        # largest separations, in SD units
        eff = []
        for j in range(X.shape[1]):
            a, b = X[y, j], X[~y, j]
            sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
            eff.append((feat[j], (a.mean() - b.mean()) / sd if sd else 0, p_obs[j]))
        eff.sort(key=lambda t: -abs(t[1]))
        print("\n  largest standardised separations:")
        for nm, e, p in eff[:5]:
            print(f"    {nm:22} {e:+.3f} SD   p={p:.4f}")
        se_d = np.sqrt(2 / (len(w) / 2))
        print(f"\n  se on a standardised difference: {se_d:.3f} SD")
        print(f"  smallest reliably detectable:    {2.8*se_d:.3f} SD")
        print(f"  separation a 60%-win feature needs: ~0.16 SD  "
              f"{'<-- BELOW the floor' if 0.16 < 2.8*se_d else ''}")
        print()


if __name__ == "__main__":
    main()
