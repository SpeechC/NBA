"""
===============================================================================
 BRACKETING-INDEPENDENT IMPLIED LINE — fixing the attrition defect
===============================================================================
 THE DEFECT. The median-crossing estimator needs the ladder to bracket 0.5:
 a strike priced above and one below. Kalshi sets strikes around the PREGAME
 expectation, so when a game runs away from that expectation the true line
 leaves the listed range, no crossing exists, and the game is silently
 dropped. The dropped games are the extreme ones -- selection on the outcome.

 It has corrupted three findings already:
   - NBA halftime slope: dropped games had sd(H1) 19.9-20.7 vs 9.2 kept, and
     removing large-move games biases the slope DOWN, toward "under-reaction"
   - WNBA halftime bias: the bracketed subset averages 177.9 pts vs 174.7 for
     the league -- +3.2, which was essentially the entire "finding"
   - the frozen residual CDF was fit on that same restricted panel

 THE FIX. A ladder is a sampled survival function: each rung gives
 P(total > K). Under a normal implied distribution,

     P(total > K) = 1 - Phi((K - mu) / sigma)
     =>  K = mu + sigma * z,   where  z = Phi^-1(1 - p)

 so regressing STRIKE on the probit of PRICE gives mu (the implied line) as
 the intercept and sigma (the implied width) as the slope. It needs no
 crossing -- only two or more unsaturated rungs -- and it uses every rung
 rather than the two straddling 0.5. When the ladder does bracket, mu is the
 same quantity median-crossing estimates (both are the p=0.5 point), so the
 two must agree; that is the validation.

 WEIGHTING. A rung's price responds to mu at rate phi(z)/sigma, so with
 roughly constant quote error the information about mu goes as phi(z)^2.
 Weighted and unweighted fits are both provided; `validate.py` reports which
 reproduces median-crossing better.

 DIAGNOSTICS. Extrapolation distance (how far p=0.5 sits outside the quoted
 range, in sigmas) is returned with every estimate, because an extrapolated
 line is not as good as an interpolated one and callers should be able to
 filter on it rather than trust it blindly.
===============================================================================
"""
import numpy as np
from scipy import stats

PMIN, PMAX = 0.02, 0.98        # saturated rungs carry no usable probit
MIN_RUNGS = 3


def probit_line(strikes, mids, weighted=True, min_rungs=MIN_RUNGS):
    """Implied line from a ladder, with or without a 0.5 crossing.

    strikes : floor strikes
    mids    : P(total > strike), same order

    Returns dict:
      mu        implied line (the p=0.5 point)
      sigma     implied sd of the outcome distribution
      n         rungs used
      bracketed did the raw ladder actually straddle 0.5
      extrap    how far mu sits outside the quoted range, in sigmas
                (0.0 when interpolated; larger = less trustworthy)
      r2        fit quality of the probit-linear form
    """
    k = np.asarray(strikes, dtype=float)
    p = np.asarray(mids, dtype=float)
    ok = np.isfinite(k) & np.isfinite(p) & (p > PMIN) & (p < PMAX)
    n = int(ok.sum())
    out = {"mu": np.nan, "sigma": np.nan, "n": n, "bracketed": False,
           "extrap": np.nan, "r2": np.nan}
    if n < min_rungs:
        return out
    kk, pp = k[ok], p[ok]
    z = stats.norm.ppf(1.0 - pp)
    w = stats.norm.pdf(z) ** 2 if weighted else np.ones_like(z)
    if not np.isfinite(w).all() or w.sum() <= 0:
        return out
    # weighted least squares of k on z: k = mu + sigma*z
    W = w / w.sum()
    zbar, kbar = (W * z).sum(), (W * kk).sum()
    vz = (W * (z - zbar) ** 2).sum()
    if vz <= 0:
        return out
    sigma = (W * (z - zbar) * (kk - kbar)).sum() / vz
    mu = kbar - sigma * zbar
    pred = mu + sigma * z
    ss = (W * (kk - kbar) ** 2).sum()
    out.update(mu=float(mu), sigma=float(sigma),
               bracketed=bool((pp >= 0.5).any() and (pp < 0.5).any()),
               r2=float(1 - (W * (kk - pred) ** 2).sum() / ss) if ss > 0 else np.nan)
    if sigma > 0:
        lo, hi = kk.min(), kk.max()
        d = 0.0 if lo <= mu <= hi else (lo - mu if mu < lo else mu - hi)
        out["extrap"] = float(d / sigma)
    return out


def median_cross(strikes, mids):
    """The incumbent estimator, for comparison. Returns nan when unbracketed."""
    q = sorted((float(a), float(b)) for a, b in zip(strikes, mids)
               if np.isfinite(a) and np.isfinite(b))
    if len(q) < 4:
        return np.nan
    xs = [a for a, _ in q]
    ps = [b for _, b in q]
    ab = [i for i, v in enumerate(ps) if v >= 0.5]
    bl = [i for i, v in enumerate(ps) if v < 0.5]
    if not ab or not bl or max(ab) > min(bl):
        return np.nan
    i, j = max(ab), min(bl)
    if ps[i] == ps[j]:
        return xs[i]
    return xs[i] + (xs[j] - xs[i]) * (ps[i] - 0.5) / (ps[i] - ps[j])
