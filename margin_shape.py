"""TESTS 1 & 2 — is the NBA margin distribution Gaussian, and where would a
Gaussian-quoted SPREAD LADDER misprice it?

KXNBASPREAD was listed in June 2026 with zero volume, so there is no ladder to
test against. Both tests are therefore run on 8 seasons of realised margins
using SYNTHETIC rungs (strikes on a grid around each game's expected margin).
That answers the science now and yields a frozen, pre-registerable prediction
for when the market goes live.

TEST 2 (the gate) — PER-GAME SHAPE vs VARIANCE MIXTURE
  The pooled spread residual has excess kurtosis +1.44 even excluding OT. Two
  explanations:
    (a) each game's margin is fat-tailed          -> a shape mispricing exists
    (b) each game is Gaussian but variances DIFFER -> pooling manufactures
        kurtosis and there is no per-game shape error
  Margin variance is known to scale with |spread| (CLOSING.md t=5.59). Fit
  sd_i = f(|spread_i|) on development, standardise, and re-test. If the
  kurtosis collapses, (b) wins and test 1 is only about the OT hole, not tails.

TEST 1 — THE OT HOLE, and the mixture that prices it
  Mechanism, in two rules-driven steps:
    step 1  end-game strategy (trailing teams foul and shoot to tie) piles up
            mass at regulation margin ZERO
    step 2  a tie is impossible in the final score, so the NBA routes that mass
            through a 5-minute overtime, which returns it at |margin| ~ 4.7
  Model:  P(final = k) = P(R = k)  for k != 0,  plus  P(R = 0) * P(OT = k)
  with P(R=0) and the OT margin distribution estimated from prior seasons.

  Compared against a plain Gaussian on: (i) tie-rate realism, (ii) log loss over
  a grid of synthetic strikes, (iii) the per-strike mispricing pattern -- which
  is the object a live ladder would expose.

Development 2017-18..2023-24 for all estimation; 2024-25 + 2025-26 held out.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE


def build():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    ot_h = sum(n(f"OT{i}_H").fillna(0.0) for i in range(1, 6))
    ot_r = sum(n(f"OT{i}_R").fillna(0.0) for i in range(1, 6))
    d = pd.DataFrame({
        "date": m["date"], "yr": m["yr"],
        "margin": n("PTS_H") - n("PTS_R"),
        "spread": n("CLOSING SPREAD_H"),
        "ot_margin": ot_h - ot_r,
        "ot": (ot_h + ot_r) > 0})
    d = d.dropna(subset=["margin", "spread"])
    d["mu"] = -d["spread"]                    # market's expected home margin
    d["res"] = d["margin"] - d["mu"]
    d["reg_margin"] = d["margin"] - d["ot_margin"]
    d["reg_res"] = d["reg_margin"] - d["mu"]
    return d


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    hold = d[d["date"] >= SPLIT_DATE]
    print(f"  {len(d):,} games   development {len(dev):,}   holdout "
          f"{len(hold):,}   OT rate {100*d['ot'].mean():.2f}%")
    # sanity: OT games must have regulation margin exactly 0
    bad = (d[d["ot"]]["reg_margin"] != 0).sum()
    print(f"  sanity: OT games with non-zero regulation margin = {bad} "
          f"(must be 0)")

    print("\n" + "=" * 92)
    print("TEST 2 — PER-GAME SHAPE vs VARIANCE MIXTURE")
    print("=" * 92)
    # sd as a function of |spread|, fit on development via mean |residual|
    a = np.column_stack([np.ones(len(dev)), dev["spread"].abs()])
    b, *_ = np.linalg.lstsq(a, dev["res"].abs(), rcond=None)
    k_norm = np.sqrt(np.pi / 2)          # E|X| = sd*sqrt(2/pi) for centred X
    print(f"  E|residual| = {b[0]:.3f} + {b[1]:.4f}*|spread|   "
          f"(development fit)")
    for lab, x in (("development", dev), ("holdout", hold)):
        sd_hat = k_norm * (b[0] + b[1] * x["spread"].abs())
        z = x["res"] / sd_hat
        zr = x["reg_res"] / sd_hat
        print(f"\n  {lab}")
        print(f"    raw residual        kurt {kurtosis(x['res']):+.3f}   "
              f"skew {skew(x['res']):+.3f}   sd {x['res'].std():.2f}")
        print(f"    standardised by sd_hat  kurt {kurtosis(z):+.3f}   "
              f"skew {skew(z):+.3f}   sd {z.std():.3f}")
        print(f"    non-OT only, standardised  kurt "
              f"{kurtosis(z[~x['ot']]):+.3f}")
    print("\n  -> if standardising collapses the kurtosis, the pooled fat tail"
          " was a VARIANCE MIXTURE")
    print("     and there is no per-game shape error to trade in the tails.")

    print("\n" + "=" * 92)
    print("TEST 1a — THE TIE RATE: does a Gaussian get it right?")
    print("=" * 92)
    sd_reg = dev.loc[~dev["ot"], "reg_res"].std()
    tie_obs = dev["ot"].mean()
    tie_gauss = 2 * norm.cdf(0.5 / sd_reg) - 1
    print(f"  regulation-residual sd (non-OT games): {sd_reg:.3f}")
    print(f"  observed regulation TIE rate (= OT rate): {100*tie_obs:.2f}%")
    print(f"  Gaussian prediction for |margin| < 0.5:  {100*tie_gauss:.2f}%")
    print(f"  ratio {tie_obs/tie_gauss:.2f}x  -> end-game play piles up mass "
          f"at a tie")

    print("\n" + "=" * 92)
    print("TEST 1b — MIXTURE vs GAUSSIAN over a grid of synthetic strikes")
    print("=" * 92)
    ot_dist = dev.loc[dev["ot"], "ot_margin"].values      # empirical OT margins
    p_tie = tie_obs

    def gauss_p(k, sd):
        return 1.0 - norm.cdf(k / sd)

    def mix_p(k, sd):
        """P(final margin - mu > k). Regulation part excludes the tie mass;
        the tie mass returns via the empirical OT margin distribution."""
        reg = 1.0 - norm.cdf(k / sd)
        # remove the (already-Gaussian) tie band and re-add it through OT
        tie_band = norm.cdf(0.5 / sd) - norm.cdf(-0.5 / sd)
        reg_ex = reg - np.clip(np.where(k < 0.5, np.minimum(
            norm.cdf(0.5 / sd) - norm.cdf(np.maximum(k, -0.5) / sd),
            tie_band), 0.0), 0, None)
        # renormalise so the non-tie part carries (1 - p_tie)
        reg_ex = reg_ex / (1.0 - tie_band) * (1.0 - p_tie)
        ot_part = p_tie * np.mean(ot_dist[None, :] > k[:, None], axis=1) \
            if np.ndim(k) else p_tie * np.mean(ot_dist > k)
        return reg_ex + ot_part

    grid = np.arange(-12.5, 13.0, 1.0)
    rows = []
    for lab, x in (("development", dev), ("holdout", hold)):
        sd_hat = k_norm * (b[0] + b[1] * x["spread"].abs())
        res = x["res"].values
        ll_g = ll_m = 0.0
        for kk in grid:
            y = (res > kk).astype(float)
            pg = np.clip(gauss_p(np.full(len(x), kk) / 1.0 * 0 + kk,
                                 sd_hat.values), 1e-6, 1 - 1e-6)
            pm = np.clip(np.array([mix_p(np.array([kk]), s)[0]
                                   for s in sd_hat.values]), 1e-6, 1 - 1e-6)
            ll_g += -np.mean(y * np.log(pg) + (1 - y) * np.log(1 - pg))
            ll_m += -np.mean(y * np.log(pm) + (1 - y) * np.log(1 - pm))
            if lab == "development":
                rows.append({"k": kk, "obs": y.mean(), "gauss": pg.mean(),
                             "mix": pm.mean()})
        print(f"  {lab:14} mean log loss over {len(grid)} strikes: "
              f"Gaussian {ll_g/len(grid):.5f}   mixture {ll_m/len(grid):.5f}"
              f"   improvement {(ll_g-ll_m)/len(grid):+.6f}")

    print("\n" + "=" * 92)
    print("TEST 1c — THE PREDICTED MISPRICING PATTERN (development)")
    print("  what a Gaussian-quoted ladder would get wrong, per strike")
    print("=" * 92)
    R = pd.DataFrame(rows)
    print(f"  {'strike (pts from mu)':>22}{'observed':>10}{'Gaussian':>10}"
          f"{'mixture':>9}{'obs-gauss pp':>14}{'mix-gauss pp':>14}")
    for _, r in R.iterrows():
        if abs(r["k"]) > 8.5:
            continue
        print(f"  {r['k']:>22.1f}{r['obs']:>10.4f}{r['gauss']:>10.4f}"
              f"{r['mix']:>9.4f}{100*(r['obs']-r['gauss']):>+14.2f}"
              f"{100*(r['mix']-r['gauss']):>+14.2f}")
    print("\n  'mix-gauss' is the FROZEN PREDICTION for a live ladder;")
    print("  'obs-gauss' is what actually happened on 8 seasons.")


if __name__ == "__main__":
    main()
