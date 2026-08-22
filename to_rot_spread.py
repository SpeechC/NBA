"""INDEPENDENT REPLICATION — low timeout use x high rotation concentration ->
larger absolute closing-SPREAD errors.  (external ref S_ea7031aacc25)

Stated mechanism: teams that historically use few timeouts and run concentrated
rotations permit longer uninterrupted lineup runs, so outcomes should deviate
further from the scalar closing spread.

    Regime = (HOME low timeouts AND HOME high HHI)
          OR (ROAD low timeouts AND ROAD high HHI)

both conditions on the SAME team, either orientation.

OUTCOME    |spread_resid| = |(PTS_H - PTS_R) + CLOSING_SPREAD_H|
ESTIMATOR  stratified within (season x 2-point closing-spread bin), identical
           to rot_b2b_spread.py, with the same within-stratum permutation.
STATES     prior-only shift(1).rolling(20, min_periods=10) within season;
           cutoffs = expanding prior-only quantiles over all history before the
           game date, 500-game burn-in. Timeouts use the LOWER 20% tail, HHI
           the UPPER 20%.
COVERAGE   EV_TIMEOUTS and lineup HHI both run 2017-18..2024-25 and are ABSENT
           for 2025-26. Development 2017-18..2023-24, validation 2024-25.

ENDOGENEITY CONCERN, recorded before the result. Timeouts are largely a
RESPONSE to game flow: coaches call them when the opponent goes on a run.
"Historically low timeout use" may therefore be a proxy for team quality or
game script rather than an exogenous structural state, which would make this
close to conditioning on an outcome. The script reports corr(prior timeout
rate, closing spread) and the favourite/underdog composition of the regime so
this can be judged rather than assumed.

MULTIPLICITY, recorded before the result. Rotation HHI has now appeared in
three separate dispersion hypotheses (x 3PA rate, x back-to-back, x timeouts).
An unadjusted p=.03448 drawn from a search over many candidate state pairs is
not evidence at face value: with ~30 pairs tested the expected count of p<.05
hits under the null is ~1.5.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
import rotation_extract

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
DEV_MAX, VALID = 2023, 2024
Q_HI, Q_LO = 0.80, 0.20
MIN_GAMES = 500
BIN = 2.0
NPERM = 5000
RNG = np.random.default_rng(20260820)


def build():
    R = rotation_extract.build()
    R["gid"] = R["gid"].astype(str).str.zfill(10)
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["spread_resid"] = (n("PTS_H") - n("PTS_R")) + m["spread"]
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R",
                     "EV_TIMEOUTS_H", "EV_TIMEOUTS_R"]], on="gid", how="left")

    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"],
            "to": pd.to_numeric(m[f"EV_TIMEOUTS_{s}"], errors="coerce"),
            "spread": m["spread"], "spread_resid": m["spread_resid"]}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(R[["gid", "team", "hhi"]].rename(columns={"gid": "gidz"}),
                on=["gidz", "team"], how="inner")
    L = L.sort_values(["date", "gidz"]).reset_index(drop=True)
    g = L.groupby(["yr", "team"])
    for c in ("hhi", "to"):
        L[f"prior_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    return L.dropna(subset=["prior_hhi", "prior_to", "spread",
                            "spread_resid"]).reset_index(drop=True)


def expanding_q(L, col, q):
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


def strat(x, col="regime"):
    num = den = 0.0
    for _, g in x.groupby(["yr", "sbin"]):
        a, b = g[g[col]]["abs_err"], g[~g[col]]["abs_err"]
        if len(a) == 0 or len(b) == 0:
            continue
        num += len(a) * (a.mean() - b.mean())
        den += len(a)
    return num / den if den else np.nan


def perm_p(x, obs):
    code = pd.factorize(pd.MultiIndex.from_arrays([x["yr"], x["sbin"]]))[0]
    K = code.max() + 1
    v = x["abs_err"].values.astype(float)
    flag = x["regime"].values.astype(bool)
    n_tot = np.bincount(code, minlength=K).astype(float)
    s_tot = np.bincount(code, weights=v, minlength=K)
    blocks = [b for b in (np.where(code == c)[0] for c in range(K))
              if len(b) > 1]

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
    return ((1 + np.nansum(np.abs(null) >= abs(obs))) / (NPERM + 1),
            np.nanmean(null), np.nanstd(null))


def main():
    L = build()
    L["q_hhi"] = expanding_q(L, "prior_hhi", Q_HI)
    L["q_to"] = expanding_q(L, "prior_to", Q_LO)
    L = L.dropna(subset=["q_hhi", "q_to"])
    L["hi"] = L["prior_hhi"] >= L["q_hhi"]
    L["lo"] = L["prior_to"] <= L["q_to"]
    L["pair"] = L["hi"] & L["lo"]
    print(f"  {len(L):,} team-game rows, {L['gidz'].nunique():,} games, "
          f"seasons {sorted(L['yr'].unique())}")
    print(f"  timeouts per team-game: mean {L['to'].mean():.3f} "
          f"sd {L['to'].std():.3f}")
    print(f"  high-HHI {100*L['hi'].mean():.2f}%   low-timeout "
          f"{100*L['lo'].mean():.2f}%   both {100*L['pair'].mean():.2f}%"
          f"   [independence would give "
          f"{100*L['hi'].mean()*L['lo'].mean()/100:.2f}%]")
    print(f"  corr(prior HHI, prior timeouts) = "
          f"{np.corrcoef(L['prior_hhi'], L['prior_to'])[0,1]:+.4f}")

    print("\n  ENDOGENEITY CHECK — are low-timeout teams just better teams?")
    L["own_spread"] = np.where(L["side"] == "H", L["spread"], -L["spread"])
    print(f"    corr(prior timeouts, own closing spread) = "
          f"{np.corrcoef(L['prior_to'], L['own_spread'])[0,1]:+.4f}"
          f"   [negative own spread = favourite]")
    print(f"    mean own spread: low-timeout teams "
          f"{L[L['lo']]['own_spread'].mean():+.3f} vs rest "
          f"{L[~L['lo']]['own_spread'].mean():+.3f}")
    print(f"    mean own spread: regime teams "
          f"{L[L['pair']]['own_spread'].mean():+.3f} vs rest "
          f"{L[~L['pair']]['own_spread'].mean():+.3f}")

    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), regime=("pair", "max"), n_side=("pair", "sum"),
        hi_any=("hi", "max"), lo_any=("lo", "max"),
        spread=("spread", "first"), spread_resid=("spread_resid", "first"))
    G["abs_err"] = G["spread_resid"].abs()
    G["sbin"] = (G["spread"] / BIN).round() * BIN
    dv, va = G[G["yr"] <= DEV_MAX], G[G["yr"] == VALID]
    print(f"\n  games {len(G):,}   development {len(dv):,}   "
          f"validation 2024-25 {len(va):,}")
    print(f"  regime games: development {int(dv['regime'].sum())}   "
          f"validation {int(va['regime'].sum())}")

    print("\n" + "=" * 96)
    print("PRIMARY — stratified within season x 2-point closing-spread bin")
    print("=" * 96)
    print(f"  {'window':18}{'n regime':>10}{'raw diff':>11}{'stratified':>12}"
          f"{'t (raw)':>10}{'perm p':>10}")
    for lab, x in (("development", dv), ("validation 24-25", va),
                   ("pooled", G)):
        a, b = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        raw = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
        s_ = strat(x)
        p, nm_, nsd = perm_p(x, s_)
        print(f"  {lab:18}{len(a):10,}{raw:+11.3f}{s_:+12.3f}{raw/se:10.2f}"
              f"{p:10.4f}")

    print("\n" + "=" * 96)
    print("EACH CONDITION ALONE — is the conjunction doing the work?")
    print("=" * 96)
    for col, nm in (("hi_any", "high rotation HHI"), ("lo_any", "low timeouts")):
        for lab, x in (("development", dv), ("validation", va)):
            y = x.copy()
            y["regime"] = y[col].astype(bool)
            a, b = y[y["regime"]]["abs_err"], y[~y["regime"]]["abs_err"]
            print(f"  {nm:20}{lab:14} n={len(a):5,}  raw "
                  f"{a.mean()-b.mean():+.3f}   stratified {strat(y):+.3f}")

    print("\n" + "=" * 96)
    print("DOSE — 0, 1 or 2 qualifying teams")
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


if __name__ == "__main__":
    main()
