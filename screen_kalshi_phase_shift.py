"""Phase-shift thinning: does sub-point mu movement re-phase the 1c grid?

The 3-point rung criterion was far too coarse. With sigma ~= 18.2,
dp/dmu = phi(0)/18.2 = 0.0219 per point, so a HALF-TICK re-rounding needs only
0.005/0.0219 = 0.23 pts near the centre (~0.35 at 20/80c, ~0.5 at 10/90c).
Requiring 3 points discarded almost every useful re-rounding, so the claim that
"mu does not move enough" is not supported by that test.

Note the joint band cannot IMPROVE under thinning -- dropping snapshots removes
constraints. So this cannot beat the all-distinct-states figure of ~2.3 pts.
What it settles is the EXPLANATION: how many genuinely phase-distinct books
does an event supply? If many, mu does re-phase the grid and the limit is that
re-phasing does not help enough. If few, the stationarity story survives.

CRITERION (as specified): retain a snapshot when, at a reference scale, the
modelled probability at >= MIN_STRIKES body strikes moves by >= 0.5c relative
to the last retained snapshot.
"""
import sqlite3, argparse, importlib.util, numpy as np, pandas as pd
from scipy.stats import norm

spec = importlib.util.spec_from_file_location(
    'rl', '/home/dpope/projects/nba_entropy_replication/screen_kalshi_repeated_ladders.py')
rl = importlib.util.module_from_spec(spec)
import sys
_argv, sys.argv = sys.argv, ['x']
spec.loader.exec_module(rl)
sys.argv = _argv

SIG_REF = 18.0
PHASE_C = 0.005
MIN_STRIKES = 3


def location_from_bounds(K, L, U, sig=SIG_REF):
    """CONTINUOUS location from the executable bounds, never a midpoint.

    A first version used the centre of the two strikes bracketing 50c. That is
    quantised to half the 3-point rung spacing -- 1.5 pts -- so it structurally
    CANNOT see the ~0.23 pt movement a half-tick re-round needs, and it reported
    a median travel of exactly 0.00. Using the closed form instead:

        mu in [max_k(K - sig*z_L), min_k(K - sig*z_U)]

    which is continuous in the quotes. Returns the centre of that interval; NaN
    if the bounds are inconsistent at sig.
    """
    Lo = np.clip(L - rl.TICK_SLACK, 1e-9, 1 - 1e-9)
    Up = np.clip(U + rl.TICK_SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), rl.BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -rl.BIG)
    lo = (K - sig * zL).max()
    hi = (K - sig * zU).min()
    return (lo + hi) / 2.0 if lo <= hi + 1e-9 else np.nan


def phase_thin(K, Lm, Um):
    """Indices of snapshots that re-phase the cent grid."""
    body = (Lm[0] >= 0.10) & (Um[0] <= 0.90)
    Kb = K[body] if body.sum() >= MIN_STRIKES else K
    keep = [0]
    loc_last = location_from_bounds(K, Lm[0], Um[0])
    if not np.isfinite(loc_last): loc_last = K.mean()
    p_last = 1 - norm.cdf((Kb - loc_last) / SIG_REF)
    for i in range(1, len(Lm)):
        loc = location_from_bounds(K, Lm[i], Um[i])
        if not np.isfinite(loc): continue
        p = 1 - norm.cdf((Kb - loc) / SIG_REF)
        if (np.abs(p - p_last) >= PHASE_C).sum() >= MIN_STRIKES:
            keep.append(i)
            p_last = p
    return keep


def run(lo_h, hi_h, max_states):
    c = rl.load()
    c = c[(c.hrs >= hi_h) & (c.hrs <= lo_h)]
    rows = []
    for ev, g in c.groupby('ev'):
        K, Lm, Um, ns = rl.event_states(g, 0.0)
        if K is None or len(K) < 4 or ns == 0:
            continue
        ph = phase_thin(K, Lm, Um)
        Lp, Up = Lm[ph], Um[ph]
        if len(Lp) > max_states:
            pick = np.linspace(0, len(Lp) - 1, max_states).astype(int)
            Lp, Up = Lp[pick], Up[pick]
        La, Ua = Lm, Um
        if len(La) > max_states:
            pick = np.linspace(0, len(La) - 1, max_states).astype(int)
            La, Ua = La[pick], Ua[pick]
        r1 = rl.band(K, Lm[:1], Um[:1])
        rP = rl.band(K, Lp, Up)
        rA = rl.band(K, La, Ua)
        locs = np.array([location_from_bounds(K, Lm[i], Um[i]) for i in range(len(Lm))])
        locs = locs[np.isfinite(locs)]
        if len(locs) == 0: locs = np.array([np.nan])
        rows.append(dict(ev=ev, states=ns, phase_states=len(ph),
                         loc_range=locs.max() - locs.min(),
                         one_w=(r1[1] - r1[0]) if r1 else np.nan,
                         ph_w=(rP[1] - rP[0]) if rP else np.nan,
                         all_w=(rA[1] - rA[0]) if rA else np.nan))
    R = pd.DataFrame(rows)
    print(f"\nwindow T-{lo_h}h .. T-{hi_h}h   events {len(R)}")
    print(f"  distinct book states       median {R.states.median():.0f}")
    print(f"  PHASE-DISTINCT states      median {R.phase_states.median():.0f}  "
          f"(mean {R.phase_states.mean():.1f}, p90 {R.phase_states.quantile(.9):.0f})")
    print(f"  events with >=3 phase states: {100*(R.phase_states>=3).mean():.1f}%")
    print(f"  total location travel (pts) median {R.loc_range.median():.2f}  "
          f"p90 {R.loc_range.quantile(.9):.2f}")
    print(f"  sigma band  one snapshot {R.one_w.median():.2f} | "
          f"phase-thinned {R.ph_w.median():.2f} | all states {R.all_w.median():.2f}")
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-states", type=int, default=400)
    a = ap.parse_args()
    print("=" * 74)
    print("PHASE-SHIFT THINNING  (>=0.5c move at >=3 body strikes, sigma_ref=18)")
    print(f"  a half-tick re-round needs ~{PHASE_C/(norm.pdf(0)/18.2):.2f} pts of mu "
          f"near the centre")
    print("=" * 74)
    for w in ((6.0, 3.0), (1.0, 0.5)):
        run(*w, a.max_states)
