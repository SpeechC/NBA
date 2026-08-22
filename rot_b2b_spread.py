"""INDEPENDENT REPLICATION — high rotation concentration x back-to-back ->
larger absolute closing-SPREAD errors.

The hypothesis as stated: a team with prior-only ROTATION_CONCENTRATION_HHI in
its upper 20% that is ALSO on a back-to-back has less substitution flexibility
and concentrates production into fatigue-sensitive lineups, so game outcomes
should be more extreme than the scalar closing spread anticipates.

    Regime = (HOME high HHI AND HOME on B2B) OR (ROAD high HHI AND ROAD on B2B)

Note the conjunction is SAME-TEAM in both orientations, as specified.

OUTCOME  |actual home margin - closing implied home margin| = |spread_resid|
         spread_resid = (PTS_H - PTS_R) + CLOSING_SPREAD_H

ESTIMATOR  stratified within (season x 2-point closing-spread bin), so regime
           games are compared with games carrying the same market-implied
           expected margin. Strata containing only one arm contribute nothing.

STATE      HHI from rotation_extract.py, prior-only shift(1).rolling(20,
           min_periods=10) within season; cutoff = expanding prior-only 80th
           percentile over all history before the game date, 500-game burn-in
           (models_frozen.py PROTOCOL).
B2B        the team played on the previous calendar day.

COVERAGE   lineup PBP runs 2017-18..2024-25 and is ABSENT for 2025-26, so the
           validation slice is 2024-25 only. Development 2017-18..2023-24.

PRIOR, recorded before the result. This is the seventh dispersion test in this
project. The first six were all negative, and `dispersion_priced.py` measured
the market as pricing dispersion at ~96% of truth (c_market +4.24, t=+12.5,
against c_true +4.43, gap t=+0.16). A reported discovery p=.0865 and validation
p~.1059 are both inside what that prior predicts. This script exists to check
whether an independent implementation reproduces the reported +0.725/+1.955 at
all, not to promote it.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
import rotation_extract

W, MINP = 20, 10
DEV_MAX, VALID = 2023, 2024
Q = 0.80
MIN_GAMES = 500
BIN = 2.0
NPERM = 5000
RNG = np.random.default_rng(20260819)


def build():
    R = rotation_extract.build()
    R["gid"] = R["gid"].astype(str).str.zfill(10)

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["spread_resid"] = (n("PTS_H") - n("PTS_R")) + m["spread"]
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]], on="gid",
                how="left")

    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "spread": m["spread"],
            "spread_resid": m["spread_resid"]}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(R[["gid", "team", "hhi"]].rename(columns={"gid": "gidz"}),
                on=["gidz", "team"], how="inner")
    L = L.sort_values(["date", "gidz"]).reset_index(drop=True)

    # B2B: this team played on the previous calendar day (across the whole
    # panel, so a season's opener can never be a B2B)
    L = L.sort_values(["team", "date"])
    L["prev"] = L.groupby("team")["date"].shift(1)
    L["b2b"] = ((L["date"] - L["prev"]).dt.days == 1).astype(int)

    # prior-only rotation concentration
    L = L.sort_values(["date", "gidz"])
    L["prior_hhi"] = L.groupby(["yr", "team"])["hhi"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    return L.dropna(subset=["prior_hhi", "spread", "spread_resid"]) \
            .sort_values(["date", "gidz"]).reset_index(drop=True)


def expanding_q(L, col, q=Q):
    v = L[col].to_numpy(dtype=float)
    dates = L["date"].to_numpy()
    gid = L["gidz"].to_numpy()
    starts = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1]])
    out = np.full(len(L), np.nan)
    for i, s in enumerate(starts):
        if s == 0 or len(np.unique(gid[:s])) < MIN_GAMES:
            continue
        e = starts[i + 1] if i + 1 < len(starts) else len(L)
        out[s:e] = np.quantile(v[:s], q)
    return out


def strat(x, flag_col="regime"):
    """Stratified mean difference within (season x 2-pt spread bin).
    Weighted by regime-game count; strata with only one arm are dropped."""
    num = den = 0.0
    kept = drop = 0
    for _, g in x.groupby(["yr", "sbin"]):
        a = g[g[flag_col]]["abs_err"]
        b = g[~g[flag_col]]["abs_err"]
        if len(a) == 0 or len(b) == 0:
            drop += len(a)
            continue
        num += len(a) * (a.mean() - b.mean())
        den += len(a)
        kept += len(a)
    return (num / den if den else np.nan), kept, drop


def main():
    L = build()
    L["q_hhi"] = expanding_q(L, "prior_hhi")
    L = L.dropna(subset=["q_hhi"])
    L["hi"] = L["prior_hhi"] >= L["q_hhi"]
    L["pair"] = L["hi"] & L["b2b"].astype(bool)
    print(f"  {len(L):,} team-game rows, {L['gidz'].nunique():,} games, "
          f"seasons {sorted(L['yr'].unique())}")
    print(f"  B2B rate {100*L['b2b'].mean():.2f}%   high-HHI rate "
          f"{100*L['hi'].mean():.2f}%   both {100*L['pair'].mean():.2f}%")
    print(f"  corr(prior HHI, B2B) = "
          f"{np.corrcoef(L['prior_hhi'], L['b2b'])[0,1]:+.4f}")

    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        regime=("pair", "max"), n_side=("pair", "sum"),
        hi_any=("hi", "max"), b2b_any=("b2b", "max"),
        spread=("spread", "first"), spread_resid=("spread_resid", "first"))
    G["abs_err"] = G["spread_resid"].abs()
    G["sbin"] = (G["spread"] / BIN).round() * BIN
    dv, va = G[G["yr"] <= DEV_MAX], G[G["yr"] == VALID]
    print(f"\n  games {len(G):,}   development {len(dv):,}   "
          f"validation 2024-25 {len(va):,}")
    print(f"  regime games: development {int(dv['regime'].sum())}   "
          f"validation {int(va['regime'].sum())}")
    print(f"  baseline |spread error| {G['abs_err'].mean():.3f} "
          f"(sd {G['abs_err'].std():.3f})")

    print("\n" + "=" * 96)
    print("PRIMARY — stratified within season x 2-point closing-spread bin")
    print("=" * 96)
    print(f"  {'window':18}{'n regime':>10}{'used':>7}{'dropped':>9}"
          f"{'raw diff':>11}{'stratified':>12}{'t (raw)':>10}")
    for lab, x in (("development", dv), ("validation 24-25", va),
                   ("pooled", G)):
        a, b = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        raw = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
        s_, kept, dropped = strat(x)
        print(f"  {lab:18}{len(a):10,}{kept:7}{dropped:9}{raw:+11.3f}"
              f"{s_:+12.3f}{raw/se:10.2f}")

    print("\n" + "=" * 96)
    print("EACH CONDITION ALONE — is the conjunction doing the work?")
    print("=" * 96)
    for col, nm in (("hi_any", "high rotation HHI"), ("b2b_any", "on B2B")):
        for lab, x in (("development", dv), ("validation", va)):
            y = x.copy()
            y["regime"] = y[col].astype(bool)
            s_, kept, _ = strat(y)
            a, b = y[y["regime"]]["abs_err"], y[~y["regime"]]["abs_err"]
            print(f"  {nm:20}{lab:14} n={len(a):5,}  raw "
                  f"{a.mean()-b.mean():+.3f}   stratified {s_:+.3f}")

    print("\n" + "=" * 96)
    print("DOSE — 0, 1 or 2 qualifying teams in the game")
    print("=" * 96)
    print(f"  {'sides':>6}{'n dev':>8}{'|err| dev':>12}{'n val':>8}"
          f"{'|err| val':>12}")
    for k in (0, 1, 2):
        a, b = dv[dv["n_side"] == k]["abs_err"], va[va["n_side"] == k]["abs_err"]
        print(f"  {k:>6}{len(a):8,}{a.mean() if len(a) else np.nan:12.3f}"
              f"{len(b):8,}{b.mean() if len(b) else np.nan:12.3f}")

    print("\n" + "=" * 96)
    print("FALSIFICATION — signed spread error should be unaffected")
    print("=" * 96)
    for lab, x in (("development", dv), ("validation 24-25", va)):
        a, b = x[x["regime"]]["spread_resid"], x[~x["regime"]]["spread_resid"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
        print(f"  {lab:18} signed {a.mean():+7.3f} vs {b.mean():+7.3f}   "
              f"diff {d:+7.3f} (t={d/se:+5.2f})")

    print("\n" + "=" * 96)
    print(f"PERMUTATION — regime flag reshuffled WITHIN (season x spread bin), "
          f"{NPERM} reps")
    print("=" * 96)
    for lab, x in (("development", dv), ("validation 24-25", va),
                   ("pooled", G)):
        obs, _, _ = strat(x)
        code = pd.factorize(pd.MultiIndex.from_arrays(
            [x["yr"], x["sbin"]]))[0]
        K = code.max() + 1
        v = x["abs_err"].values.astype(float)
        flag = x["regime"].values.astype(bool)
        n_tot = np.bincount(code, minlength=K).astype(float)
        s_tot = np.bincount(code, weights=v, minlength=K)
        blocks = [np.where(code == c)[0] for c in range(K)]
        blocks = [b for b in blocks if len(b) > 1]

        def stat(f):
            na = np.bincount(code[f], minlength=K).astype(float)
            sa = np.bincount(code[f], weights=v[f], minlength=K)
            nb = n_tot - na
            ok = (na > 0) & (nb > 0)
            if not ok.any():
                return np.nan
            d = sa[ok] / na[ok] - (s_tot[ok] - sa[ok]) / nb[ok]
            return float((na[ok] * d).sum() / na[ok].sum())

        null = np.empty(NPERM)
        for j in range(NPERM):
            f2 = flag.copy()
            for bl in blocks:
                f2[bl] = flag[bl][RNG.permutation(len(bl))]
            null[j] = stat(f2)
        p2 = (1 + np.nansum(np.abs(null) >= abs(obs))) / (NPERM + 1)
        print(f"  {lab:18} observed {obs:+.4f}   null {np.nanmean(null):+.4f} "
              f"sd {np.nanstd(null):.4f}   two-sided p={p2:.4f}")


if __name__ == "__main__":
    main()
