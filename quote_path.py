"""QUOTE-PATH DECOMPOSITION — executes PREREG_quote_path.md.

Does the PATH the line took carry information beyond its NET movement?
P1 primary (total), P2/P3 secondary. Nothing here is tuned; every choice
(q3 dropped, split, leg definitions, one-sided direction) is fixed in the
prereg and read from it.
"""
import re
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side

NPERM = 5000
RNG = np.random.default_rng(42)
LM = [f"LINE \nMOVEMENT #{i}" for i in (1, 2)]        # q3 dropped: era gate
NUM = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")
DEV_SEASONS = ("2017-2018", "2018-2019", "2020-2021", "2021-2022",
               "2022-2023", "2023 In-Season", "2023-2024")


def lead(s):
    m = NUM.match(str(s))
    return float(m.group(1)) if m else np.nan


def ols_t(y, cols):
    """Return (betas, tstats) for [1, *cols] on rows finite everywhere."""
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    n, k = X.shape
    s2 = r @ r / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return b, b / se


def r2(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    return 1 - (r @ r) / ((y - y.mean()) @ (y - y.mean()))


def build():
    raw = read_master(verbose=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].astype(str).str.contains(
        "Regular Season|In-Season", na=False)].copy()

    d = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip(),
                      "season": raw["season"].astype(str)})
    d["to_open"] = pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce")
    d["to_close"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    d["sp_open"] = pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce")
    d["sp_close"] = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")

    for i, c in enumerate(LM, start=1):
        h = raw[f"{c}_H"].map(lead).values
        r = raw[f"{c}_R"].map(lead).values
        sp_h = np.where(np.abs(h) <= 30, h, np.nan)
        sp_r = np.where(np.abs(r) <= 30, r, np.nan)
        to_h = np.where((np.abs(h) > 60) & (h >= 150) & (h <= 300), h, np.nan)
        to_r = np.where((np.abs(r) > 60) & (r >= 150) & (r <= 300), r, np.nan)
        d[f"sp_q{i}"] = np.where(~np.isnan(sp_h), sp_h, -sp_r)   # _R = away side
        d[f"to_q{i}"] = np.where(~np.isnan(to_h), to_h, to_r)

    # outcomes (first use of any outcome variable in this branch)
    hp = _side(raw, "H")["Y"].values.astype(float)
    ap = _side(raw, "R")["Y"].values.astype(float)
    d["actual_total"] = hp + ap
    d["actual_margin"] = hp - ap                       # home-side

    for k, o, c in (("to", "to_open", "to_close"), ("sp", "sp_open", "sp_close")):
        d[f"{k}_early"] = d[f"{k}_q1"] - d[o]
        d[f"{k}_mid"] = d[f"{k}_q2"] - d[f"{k}_q1"]
        d[f"{k}_late"] = d[c] - d[f"{k}_q2"]
        d[f"{k}_net"] = d[c] - d[o]
        d[f"{k}_churn"] = (d[[f"{k}_early", f"{k}_mid", f"{k}_late"]].abs().sum(axis=1)
                           - d[f"{k}_net"].abs())
        d[f"{k}_nrep"] = d[[o, f"{k}_q1", f"{k}_q2", c]].apply(
            lambda r: r.dropna().nunique(), axis=1)

    # dev: c_true - c_market.  spread is quoted home-side, so margin + spread.
    d["dev"] = d["actual_total"] - d["to_close"]
    d["dev_s"] = d["actual_margin"] + d["sp_close"]

    mf = pd.read_csv("movement_full_games.csv")
    mf["gid"] = mf.game_id.astype(str).str.strip()
    d = d.merge(mf[["gid", "dis_open"]].drop_duplicates("gid"), on="gid", how="left")

    d["is_dev"] = d.season.str.contains("|".join(DEV_SEASONS))
    return d


def perm_block(d, stat_fn, cols, label):
    """Within-season joint permutation of the path rows (5,000 reps)."""
    yrs = d["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    V = d[cols].values
    obs = stat_fn(V)
    null = np.empty(NPERM)
    for i in range(NPERM):
        P = V.copy()
        for bl in blocks:
            P[bl] = V[bl][RNG.permutation(len(bl))]     # legs move together
        null[i] = stat_fn(P)
    p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    print(f"    {label:34} obs {obs:+.5f}  null {null.mean():+.5f} "
          f"sd {null.std():.5f}   p2={p2:.4f}  p1={p1:.4f}")
    return obs, p1, p2


def report(d, k, name):
    x = d[d.is_dev].dropna(subset=[f"{k}_early", f"{k}_mid", f"{k}_late",
                                   "dev" if k == "to" else "dev_s"])
    y = x["dev" if k == "to" else "dev_s"].values
    legs = [x[f"{k}_{p}"].values for p in ("early", "mid", "late")]
    b, t = ols_t(y, legs)
    net_b, net_t = ols_t(y, [x[f"{k}_net"].values])
    print(f"\n  {name}  development n={len(x):,}")
    print(f"    incumbent   dev ~ net      beta {net_b[1]:+.4f} (t={net_t[1]:+.2f})"
          f"   R2 {r2(y, [x[f'{k}_net'].values]):.5f}")
    for j, p in enumerate(("early", "mid", "late")):
        sd = np.std(legs[j])
        print(f"    leg {p:6}  beta {b[j+1]:+.4f} (t={t[j+1]:+.2f})   "
              f"sd {sd:.2f}  nonzero {100*np.mean(legs[j] != 0):.0f}%")
    print(f"    joint R2 {r2(y, legs):.5f}")
    return x, y, legs, b


def main():
    d = build()
    print(f"built {len(d):,} games;  development {int(d.is_dev.sum()):,}"
          f"   holdout {int((~d.is_dev).sum()):,}")

    for k, name in (("to", "TOTAL  (PRIMARY)"), ("sp", "SPREAD (secondary)")):
        x, y, legs, b = report(d, k, name)
        tgt = "dev" if k == "to" else "dev_s"

        print(f"    --- P1a joint test (R2 of the three legs) ---")
        perm_block(x, lambda V: r2(y, [V[:, 0], V[:, 1], V[:, 2]]),
                   [f"{k}_early", f"{k}_mid", f"{k}_late"], "P1a joint R2")

        print(f"    --- P1b  beta_early - beta_late  (one-sided, predicted >0) ---")
        def diff(V):
            bb, _ = ols_t(y, [V[:, 0], V[:, 1], V[:, 2]])
            return bb[1] - bb[3]
        perm_block(x, diff, [f"{k}_early", f"{k}_mid", f"{k}_late"],
                   "P1b beta_early - beta_late")

        if k != "to":
            continue

        print("\n    --- P2 book attention: dev ~ net + net x 1[nrep<=2] ---")
        low = (x[f"{k}_nrep"] <= 2).astype(float).values
        net = x[f"{k}_net"].values
        b2, t2 = ols_t(y, [net, net * low, low])
        print(f"      nrep distribution: " + "  ".join(
            f"{v}:{int((x[f'{k}_nrep'] == v).sum()):,}"
            for v in sorted(x[f"{k}_nrep"].unique())))
        print(f"      net {b2[1]:+.4f} (t={t2[1]:+.2f})   "
              f"net x low {b2[2]:+.4f} (t={t2[2]:+.2f})  [predicted > 0]")

        print("\n    --- P3 churn (descriptive, variance, NOT tradeable) ---")
        ch = x[f"{k}_churn"].values
        b3, t3 = ols_t(np.abs(y), [ch])
        print(f"      churn>0 on {100*np.mean(ch > 0):.1f}% of games; "
              f"|dev| ~ churn  beta {b3[1]:+.4f} (t={t3[1]:+.2f}) [predicted > 0]")

        # ---- §5 incremental test, scored ONCE on holdout -------------------
        print("\n    === SECTION 5 INCREMENTAL TEST (holdout, scored once) ===")
        ho = d[~d.is_dev].dropna(subset=[f"{k}_early", f"{k}_mid", f"{k}_late", tgt])
        for extra in ([], ["dis_open"]):
            tag = "+dis_open" if extra else "bare     "
            tr = x.dropna(subset=extra) if extra else x
            te = ho.dropna(subset=extra) if extra else ho
            ytr, yte = tr[tgt].values, te[tgt].values

            def fit_score(cols_tr, cols_te):
                X = np.column_stack([np.ones(len(ytr))] + cols_tr)
                bb, *_ = np.linalg.lstsq(X, ytr, rcond=None)
                Xt = np.column_stack([np.ones(len(yte))] + cols_te)
                pr = Xt @ bb
                return 1 - ((yte - pr) @ (yte - pr)) / ((yte - yte.mean()) @ (yte - yte.mean()))

            A = fit_score([tr[f"{k}_net"].values] + [tr[c].values for c in extra],
                          [te[f"{k}_net"].values] + [te[c].values for c in extra])
            B = fit_score([tr[f"{k}_{p}"].values for p in ("early", "mid", "late")]
                          + [tr[c].values for c in extra],
                          [te[f"{k}_{p}"].values for p in ("early", "mid", "late")]
                          + [te[c].values for c in extra])
            print(f"      {tag}  n_ho={len(te):,}   A(net) OOS R2 {A:+.5f}   "
                  f"B(legs) OOS R2 {B:+.5f}   B-A {B-A:+.5f}   "
                  f"{'B WINS' if B > A else 'A WINS -> P1 does not advance'}")


if __name__ == "__main__":
    main()
