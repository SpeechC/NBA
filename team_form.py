"""Is team scoring form a real transient state, and is it priced?

THE TRAP. "High-scoring teams score less afterwards" is mechanically true and
means nothing. If observed scoring = stable team level + white noise, a high
rolling average is high partly by luck, and later games revert fully. That is
regression to the mean, not a streak converging.

THE DISCRIMINATOR. Demean every team WITHIN its own season. That removes the
stable level by construction, so under level-plus-noise the autocorrelation of
what remains is ZERO AT EVERY LAG. Any systematic positive autocorrelation is a
genuine transient component -- real form. A decaying ACF is form with a
half-life; a flat-zero ACF is no form at all.

(Full-season demeaning induces a small mechanical negative bias of about
-1/(n-1) ~ -0.013 at n~77 games; it is reported so the ACF can be read against
the right zero.)

THE ONLY QUESTION THAT MATTERS. If a transient state exists, is it PRICED?
Built as a short-minus-long prior-only deviation, mirroring the LeagueFoulState
construction in ref_features.py:

    form = mean(last SHORT games' points) - mean(last LONG games' points)

then compared as c_true vs c_market:

    c_true   : actual game total ~ combined form
    c_market : closing total     ~ combined form
    gap      : actual - closing  ~ combined form

A market that correctly prices form gives c_market ~ c_true and gap ~ 0. A
market that EXTRAPOLATES hot form gives gap < 0 (total set too high). A market
that ignores form gives c_market ~ 0 with c_true live -- the CrewShock pattern.

Everything is strictly prior-only: shift(1) within season.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

SHORT, LONG = 10, 40
MINL = 20
MAXLAG = 20


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]], on="gid",
                how="left")
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"],
            "pts": n(f"PTS_{s}"), "pts_a": n(f"PTS_{o}"),
            "total": m["total"], "actual": m["actual"]}))
    L = pd.concat(rows, ignore_index=True).dropna(
        subset=["pts", "team", "total", "actual"])
    return L.sort_values(["date", "gid"]).reset_index(drop=True)


def acf_within(L, col, maxlag=MAXLAG):
    """Autocorrelation of team-season-demeaned values, pooled over team-seasons.
    Under stable-level-plus-noise this is zero at every lag."""
    out = []
    g = L.sort_values("date").groupby(["yr", "team"])
    dev = {k: (v[col] - v[col].mean()).values for k, v in g}
    dev = {k: v for k, v in dev.items() if len(v) >= 40}
    for lag in range(1, maxlag + 1):
        num = den = 0.0
        cnt = 0
        for v in dev.values():
            if len(v) <= lag:
                continue
            num += np.dot(v[:-lag], v[lag:])
            den += np.dot(v, v)
            cnt += len(v) - lag
        out.append((lag, num / den if den else np.nan, cnt))
    return out, len(dev), np.mean([len(v) for v in dev.values()])


def main():
    L = build()
    print(f"  {len(L):,} team-games, {L['gid'].nunique():,} games, "
          f"seasons {sorted(L['yr'].unique())}")
    print(f"  team points per game: mean {L['pts'].mean():.2f} "
          f"sd {L['pts'].std():.2f}")

    print("\n" + "=" * 92)
    print("1 — IS THERE A REAL TRANSIENT STATE?")
    print("  team-season demeaned points; ZERO at every lag = no form, only "
          "level + noise")
    print("=" * 92)
    for col, nm in (("pts", "own points scored"),
                    ("pts_a", "points allowed")):
        a, nts, avg = acf_within(L, col)
        bias = -1.0 / (avg - 1)
        print(f"\n  {nm}   ({nts} team-seasons, {avg:.0f} games each)")
        print(f"  mechanical zero from full-season demeaning: {bias:+.4f}")
        print("   " + "".join(f"{l:>7}" for l, _, _ in a[:10]))
        print("   " + "".join(f"{r:+7.3f}" for _, r, _ in a[:10]))
        print("   " + "".join(f"{l:>7}" for l, _, _ in a[10:]))
        print("   " + "".join(f"{r:+7.3f}" for _, r, _ in a[10:]))
        se = 1.0 / np.sqrt(a[0][2])
        m5 = np.mean([r for _, r, _ in a[:5]])
        print(f"  approx SE per lag {se:.4f}   mean of lags 1-5 {m5:+.4f} "
              f"({(m5-bias)/se:+.2f} SE from the mechanical zero)")

    print("\n" + "=" * 92)
    print(f"2 — FORM STATE: last {SHORT} games minus last {LONG}, prior-only")
    print("=" * 92)
    g = L.groupby(["yr", "team"])["pts"]
    L["s"] = g.transform(lambda s: s.shift(1).rolling(SHORT, min_periods=SHORT
                                                      ).mean())
    L["l"] = g.transform(lambda s: s.shift(1).rolling(LONG, min_periods=MINL
                                                      ).mean())
    L["form"] = L["s"] - L["l"]
    F = L.dropna(subset=["form"])
    print(f"  usable team-games {len(F):,}   form mean {F['form'].mean():+.4f} "
          f"sd {F['form'].std():.4f}")
    # does form predict the team's OWN next-game scoring, beyond its level?
    b, se, t = ols(F["pts"].values,
                   np.column_stack([F["form"].values, F["l"].values]))
    print(f"  own next-game points ~ form + level:  form {b[1]:+.4f} "
          f"(t={t[1]:+.2f})   level {b[2]:+.4f} (t={t[2]:+.2f})")
    print(f"    [form coef > 0 = hot form persists; ~0 = it was noise;"
          f" < 0 = it over-corrects]")

    G = F.groupby("gid", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"), n=("form", "size"),
        form=("form", "sum"), lvl=("l", "sum"),
        total=("total", "first"), actual=("actual", "first"))
    G = G[G["n"] == 2]
    G["e"] = G["actual"] - G["total"]
    print(f"  games with both teams' form defined: {len(G):,}")

    print("\n" + "=" * 92)
    print("3 — IS IT PRICED?  c_true vs c_market on the combined form state")
    print("=" * 92)
    print(f"  {'window':16}{'c_true':>10}{'t':>7}{'c_market':>11}{'t':>7}"
          f"{'gap':>9}{'t':>7}{'n':>8}")
    for lab, x in (("development", G[G["date"] < SPLIT_DATE]),
                   ("holdout", G[G["date"] >= SPLIT_DATE]),
                   ("pooled", G)):
        X = np.column_stack([x["form"].values, x["lvl"].values])
        bt, _, tt = ols(x["actual"].values, X)
        bm, _, tm = ols(x["total"].values, X)
        be, _, te = ols(x["e"].values, X)
        print(f"  {lab:16}{bt[1]:+10.4f}{tt[1]:7.2f}{bm[1]:+11.4f}{tm[1]:7.2f}"
              f"{be[1]:+9.4f}{te[1]:7.2f}{len(x):8,}")
    print("\n  c_market ~ c_true and gap ~ 0  -> form is correctly priced")
    print("  gap < 0                        -> the market EXTRAPOLATES form")
    print("  c_market ~ 0 with c_true live  -> the market IGNORES form")

    print("\n" + "=" * 92)
    print("4 — THE TRADEABLE VERSION: extreme combined form deciles")
    print("=" * 92)
    dev = G[G["date"] < SPLIT_DATE]
    lo, hi = dev["form"].quantile(0.10), dev["form"].quantile(0.90)
    print(f"  frozen development deciles: form <= {lo:+.3f} (cold), "
          f">= {hi:+.3f} (hot)")
    print(f"  {'window':16}{'cell':8}{'n':>7}{'mean e':>10}{'over %':>9}"
          f"{'vs 52.38':>10}")
    for lab, x in (("development", dev), ("holdout", G[G["date"] >= SPLIT_DATE])):
        for nm, s in (("HOT", x[x["form"] >= hi]), ("COLD", x[x["form"] <= lo])):
            if not len(s):
                continue
            ov = 100 * (s["e"] > 0).mean()
            print(f"  {lab:16}{nm:8}{len(s):7,}{s['e'].mean():+10.3f}"
                  f"{ov:9.2f}%{ov-52.38:+10.2f}pp")


if __name__ == "__main__":
    main()
