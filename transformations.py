"""Price-transformation errors: FG Total -> H1, and Spread -> Moneyline.

Not "can we forecast the game better" but "does the book map its efficient
primary price into a secondary market correctly".

For each transformation, four questions:

  1 RECOVER    regress the derived price on the primary price. High R^2 means a
               formula; the residual is the book's discretionary adjustment.
  2 CALIBRATE  Mincer-Zarnowitz on the ALLOCATION itself:
                   actual_share = a + b * market_share
               b = 1 means the book's variation is correctly sized. b > 1 means
               it under-varies (too rigid); b < 1 means it over-varies, adding
               noise it should shrink away.
  3 INFORM     is the book's DEVIATION from its own formula informative? If the
               book departs from c x FG and those departures do not predict the
               actual allocation, the deviation is noise -- and the pure rule
               would beat the posted line. That is a mispricing in the opposite
               direction from the usual hypothesis.
  4 OMIT       does any pre-specified observable predict the allocation error?

Pre-specified candidates for step 4, fixed before looking: |spread|, total
level, and the two teams' recent pace. No searching.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"


def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + list(X))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    dof = len(y) - X.shape[1]
    s2 = ((y - yhat) ** 2).sum() / dof
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    for n, b, s in zip(["intercept"] + names, beta, se):
        print(f"      {n:22} {b:+.5f}  se {s:.5f}  t={b/s:+.2f}")
    print(f"      R^2 = {r2:.4f}   residual sd = {np.sqrt(s2):.4f}")
    return beta, yhat, r2


def fg_to_h1():
    from halves import period_scores
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    o["actual_full"] = o["PTS_H"] + o["PTS_R"]
    o["spread"] = pd.to_numeric(o["CLOSING SPREAD_H"], errors="coerce")
    ps = period_scores("RegularSeason")
    o = o.merge(ps[["gid", "q1", "q2"]], on="gid", how="inner")
    o["actual_h1"] = o["q1"] + o["q2"]
    tm = pd.read_csv("team_mapping.csv")
    ab = dict(zip(tm["bigdataball_name"], tm["abbr"]))
    o["key"] = (o["date"].dt.strftime("%Y-%m-%d") + "_" + o["TEAM_R"].map(ab)
                + "_" + o["TEAM_H"].map(ab))

    dk = pd.read_csv(DK)
    dk["key"] = dk["game_date_et"] + "_" + dk["away_abbr"] + "_" + dk["home_abbr"]
    dk = dk.dropna(subset=["h1_total_close", "full_game_total_close"])
    j = o.merge(dk[["key", "full_game_total_close", "h1_total_close"]],
                on="key", how="inner")
    j["mkt_share"] = j["h1_total_close"] / j["full_game_total_close"]
    j["act_share"] = j["actual_h1"] / j["actual_full"]
    j["abs_spread"] = j["spread"].abs()

    print("=" * 92)
    print(f"TRANSFORMATION 1 — FG TOTAL -> H1 TOTAL   (n={len(j)})")
    print("=" * 92)
    print("\n  1 RECOVER the rule:")
    beta, yhat, r2 = ols(j["h1_total_close"].values,
                         [j["full_game_total_close"].values], ["full_game_total"])
    j["rule_dev"] = j["h1_total_close"] - yhat
    print(f"\n      implied constant share {beta[1]:.4f}; the book's H1 line sits "
          f"{np.sqrt(((j['h1_total_close']-yhat)**2).mean()):.3f} pts from the "
          f"pure rule on average")
    print(f"      sd(market share) {j['mkt_share'].std():.4f}   "
          f"sd(actual share) {j['act_share'].std():.4f}")

    print("\n  2 CALIBRATE the allocation (actual_share ~ market_share):")
    ols(j["act_share"].values, [j["mkt_share"].values], ["market_share"])
    b = np.polyfit(j["mkt_share"], j["act_share"], 1)[0]
    print(f"      b = {b:+.3f}.  b>1 -> book under-varies;  b<1 -> over-varies")

    print("\n  3 INFORM — are the book's deviations from its own rule useful?")
    j["share_err"] = j["act_share"] - j["mkt_share"]
    r = np.corrcoef(j["rule_dev"], j["actual_h1"] - beta[0]
                    - beta[1] * j["full_game_total_close"])[0, 1]
    t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    print(f"      corr(book deviation, actual deviation from the rule) "
          f"{r:+.4f}  t={t:+.2f}")
    print("      if ~0, the book's discretionary H1 adjustment is noise")

    print("\n  4 OMIT — pre-specified predictors of the allocation error:")
    for c, lab in (("abs_spread", "|spread|"),
                   ("full_game_total_close", "total level")):
        r = np.corrcoef(j[c], j["share_err"])[0, 1]
        t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
        print(f"      share_err ~ {lab:14} corr {r:+.4f}  t={t:+.2f}")
    return j


def spread_to_ml():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["home_win"] = (d["PTS_H"] > d["PTS_R"]).astype(float)
    d = d.dropna(subset=["spread", "mlh", "mla", "home_win"])
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p_home"] = ph / (ph + pa)
    d = d[(d["p_home"] > 0.02) & (d["p_home"] < 0.98)]
    d["logit"] = np.log(d["p_home"] / (1 - d["p_home"]))

    print("\n" + "=" * 92)
    print(f"TRANSFORMATION 2 — SPREAD -> MONEYLINE   (n={len(d):,})")
    print("=" * 92)
    print("\n  1 RECOVER the rule (devigged logit on the spread):")
    beta, yhat, r2 = ols(d["logit"].values, [-d["spread"].values],
                         ["-spread"])
    d["ml_dev"] = d["logit"] - yhat
    print(f"      residual sd in logit units: {d['ml_dev'].std():.4f}")

    print("\n  3 INFORM — do the book's ML deviations from the spread-rule "
          "predict outcomes?")
    # does the deviation add anything beyond the spread itself?
    from sklearn.linear_model import LogisticRegression
    X1 = (-d["spread"].values).reshape(-1, 1)
    X2 = np.column_stack([-d["spread"].values, d["ml_dev"].values])
    y = d["home_win"].values
    m1 = LogisticRegression(max_iter=1000).fit(X1, y)
    m2 = LogisticRegression(max_iter=1000).fit(X2, y)
    ll1 = -np.mean(y * np.log(m1.predict_proba(X1)[:, 1])
                   + (1 - y) * np.log(1 - m1.predict_proba(X1)[:, 1]))
    ll2 = -np.mean(y * np.log(m2.predict_proba(X2)[:, 1])
                   + (1 - y) * np.log(1 - m2.predict_proba(X2)[:, 1]))
    print(f"      log-loss, spread only      {ll1:.5f}")
    print(f"      log-loss, + book deviation {ll2:.5f}   "
          f"improvement {ll1-ll2:+.5f}")
    print(f"      coefficient on the deviation: {m2.coef_[0][1]:+.4f}")
    print("      a positive coefficient means the book's departure from the")
    print("      spread-rule is informative; ~0 means it is noise")

    print("\n  2 CALIBRATE — actual win rate vs the book's implied probability:")
    d["bin"] = pd.cut(d["p_home"], np.arange(0.1, 0.95, 0.1))
    t = d.groupby("bin", observed=True).apply(lambda s: pd.Series({
        "n": len(s), "implied": round(s["p_home"].mean(), 4),
        "actual": round(s["home_win"].mean(), 4),
        "gap pp": round(100 * (s["home_win"].mean() - s["p_home"].mean()), 2)}),
        include_groups=False)
    print(t.to_string())


def main():
    fg_to_h1()
    spread_to_ml()


if __name__ == "__main__":
    main()
