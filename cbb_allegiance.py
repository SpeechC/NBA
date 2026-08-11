"""Stage 2 screen — does college allegiance bias the CBB line?

This is a SCREEN, not a model. It asks one question: do brand-name programs
attract enough public money to shade their lines measurably?

PRE-REGISTERED before looking at any output.

HYPOTHESIS (the reason CBB was proposed)
    Public money concentrates on high-profile programs. A book shading its
    line toward the popular side leaves the UNPOPULAR side with value.
    Prediction: the high-profile side COVERS LESS THAN 50% of the time,
    and the gap grows with the brand asymmetry of the matchup.

    This is invisible to the unconditional screen. Pooled over all games the
    popular side is home about as often as away and the effect cancels — which
    is consistent with the observed 50.29% unconditional home cover rate.

TIERS (fixed by conference membership, declared before running)
    POWER6    ACC, Big Ten, Big 12, SEC, Big East, Pac-12
    MID       A-10, AAC, Mountain West, WCC, Missouri Valley, CAA,
              Sun Belt, C-USA, MAC
    LOW       all remaining D-I conferences

CELLS (all declared up front; every one is reported, including nulls)
    SIDES  1. POWER6 vs LOW          -- largest brand asymmetry
           2. POWER6 vs MID
           3. MID    vs LOW
           4. POWER6 vs POWER6       -- symmetric, should be null
           5. LOW    vs LOW          -- no public interest, should be null
    TOTALS 6. same five splits, over rate

STATISTIC
    sides : cover rate OF THE HIGHER-TIER SIDE (home or road, whichever)
            H1 predicts < 50%. Break-even to FADE it at -110 is 52.38%.
    totals: over rate.

CONTROLS
    - Benjamini-Hochberg across all cells tested.
    - Permutation null on the maximum |deviation| across the five sides cells,
      to price in that five cells were examined.
"""
import numpy as np
import pandas as pd

from cbb_load import load

POWER6 = {
    "Atlantic Coast Conference", "Big Ten Conference", "Big 12 Conference",
    "Southeastern Conference", "Big East Conference", "Pac-12 Conference",
}
MID = {
    "Atlantic 10 Conference", "American Athletic Conference",
    "Mountain West Conference", "West Coast Conference",
    "Missouri Valley Conference", "Coastal Athletic Association",
    "Sun Belt Conference", "Conference USA", "Mid-American Conference",
}
N_PERM = 5000
BE = {-110: 52.38, -105: 51.22, -102: 50.50}


def tier(conf):
    if conf in POWER6:
        return 2
    if conf in MID:
        return 1
    return 0


def bh(pvals, q=0.05):
    """Benjamini-Hochberg; returns boolean array of rejections."""
    p = np.asarray(pvals)
    order = np.argsort(p)
    m = len(p)
    keep = np.zeros(m, bool)
    thresh = q * (np.arange(1, m + 1)) / m
    passed = p[order] <= thresh
    if passed.any():
        last = np.max(np.where(passed)[0])
        keep[order[: last + 1]] = True
    return keep


def main():
    rng = np.random.default_rng(23)
    g = load().dropna(subset=["close_total", "close_spread", "total_pts"]).copy()
    g = g.dropna(subset=["conf_h", "conf_r"])
    g["t_h"] = g.conf_h.map(tier)
    g["t_r"] = g.conf_r.map(tier)
    g["resid_tot"] = g.total_pts - g.close_total
    g = g[g.resid_tot != 0]

    # cover rate of the HIGHER-TIER side; ties excluded from the sides test
    g["hi_is_home"] = g.t_h > g.t_r
    g["hi_covered"] = np.where(g.hi_is_home,
                               g.margin_vs_line > 0,
                               g.margin_vs_line < 0)

    cells = [
        ("POWER6 vs LOW", (g.t_h == 2) & (g.t_r == 0) | (g.t_h == 0) & (g.t_r == 2)),
        ("POWER6 vs MID", (g.t_h == 2) & (g.t_r == 1) | (g.t_h == 1) & (g.t_r == 2)),
        ("MID vs LOW", (g.t_h == 1) & (g.t_r == 0) | (g.t_h == 0) & (g.t_r == 1)),
        ("POWER6 vs POWER6", (g.t_h == 2) & (g.t_r == 2)),
        ("LOW vs LOW", (g.t_h == 0) & (g.t_r == 0)),
    ]

    print("=" * 96)
    print("STAGE 2 — ALLEGIANCE / PUBLIC-MONEY BIAS, NCAAB 2023-24")
    print("=" * 96)
    print("H1: the higher-tier (more popular) side covers LESS than 50%.")
    print("    To profit by FADING it you need its cover rate below 47.62% (-110).\n")

    rows, pvals = [], []
    for name, mask in cells:
        d = g[mask]
        n = len(d)
        if n == 0:
            continue
        mixed = d.t_h != d.t_r
        if mixed.any():
            c = d.loc[mixed, "hi_covered"].mean()
            nm = int(mixed.sum())
        else:
            c, nm = np.nan, 0
        o = (d.resid_tot > 0).mean()
        se_c = np.sqrt(c * (1 - c) / nm) if nm else np.nan
        se_o = np.sqrt(o * (1 - o) / n)
        z = (c - 0.5) / se_c if nm else np.nan
        from scipy import stats as st
        p = 2 * (1 - st.norm.cdf(abs(z))) if nm else np.nan
        rows.append(dict(cell=name, n=n, n_mixed=nm,
                         hi_cover=round(100 * c, 2) if nm else None,
                         **{"±95%": round(196 * se_c, 2) if nm else None},
                         z=round(z, 2) if nm else None,
                         p=round(p, 4) if nm else None,
                         over_pct=round(100 * o, 2),
                         over_z=round((o - 0.5) / se_o, 2)))
        if nm:
            pvals.append(p)

    t = pd.DataFrame(rows)
    print(t.to_string(index=False))

    print("\nBenjamini-Hochberg across the %d sides cells at q=0.05:" % len(pvals))
    rej = bh(pvals)
    print("  rejections:", int(rej.sum()), "of", len(pvals))

    # permutation null on the max |deviation| across the mixed-tier cells
    mixed_all = g[g.t_h != g.t_r]
    obs = []
    for name, mask in cells:
        d = g[mask]
        d = d[d.t_h != d.t_r]
        if len(d):
            obs.append(abs(d.hi_covered.mean() - 0.5))
    mx = max(obs)
    sizes = [len(g[mask][g[mask].t_h != g[mask].t_r]) for _, mask in cells]
    sizes = [s for s in sizes if s]
    vals = mixed_all.hi_covered.values.astype(float)
    null = []
    for _ in range(N_PERM):
        sh = vals[rng.permutation(len(vals))]
        st_ = 0
        ms = []
        for s in sizes:
            ms.append(abs(sh[st_:st_ + s].mean() - 0.5))
            st_ += s
        null.append(max(ms))
    null = np.array(null)
    print("\npermutation null on the MAX |cover - 50pct| across %d cells:" % len(sizes))
    print("  observed max %.4f ; null mean %.4f ; null 95th pct %.4f"
          % (mx, null.mean(), np.quantile(null, 0.95)))
    print("  observed sits at the %.1fth percentile of its own null"
          % (100 * (null < mx).mean()))

    print("\npooled higher-tier cover rate, all mixed-tier games: %.2f%%  (n=%d)"
          % (100 * mixed_all.hi_covered.mean(), len(mixed_all)))
    p = mixed_all.hi_covered.mean()
    se = np.sqrt(p * (1 - p) / len(mixed_all))
    print("  95%% CI (%.2f, %.2f) ; to fade at -110 needs < 47.62%%"
          % (100 * (p - 1.96 * se), 100 * (p + 1.96 * se)))


if __name__ == "__main__":
    main()
