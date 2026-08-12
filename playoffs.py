"""Playoff regime tests: Game 1 and elimination games, pre-registered separately.

PRIMARY PREDICTIONS, frozen before running:

    state                    prediction
    Game 1 of a series       closing total too HIGH -> under
    elimination game         under, potentially weaker: defensive intensity cuts
                             scoring but late intentional fouling gives it back
    other playoff games      reference regime

The hypothesis is about MISPRICING, not about playoff scoring being low. The book
knows it is the playoffs; the test is actual minus the posted total.

BATTERY per state: mean / median / 10%-trimmed residual, under %, push %, ROI at
-110, season-by-season signs, the open/close attribution identity, and a
WITHIN-SERIES fixed-effect control:

    R_sg = a_s + b * State_sg + e_sg

which holds the matchup, the teams and most of the environment constant. If
b < 0, the state is unusually under even against the rest of that exact series.

TRANSITION TEST: for series reaching an elimination game, the change in residual
from the immediately preceding game to the first elimination game. Same matchup,
competitive state changes. E[dR] ~ 0 if the market handles the transition.

DECOMPOSITION: elimination games by half and quarter, to test whether an under
in H1 is offset by late fouling in Q4 -- which would explain a weak full-game
result without the intensity mechanism being wrong.

Elimination is defined on information known BEFORE tip-off: a team faces
elimination if it already has 3 losses in a best-of-7. Mutual elimination is
Game 7. Play-in games are excluded.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

BE = 110 / 210


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Playoffs", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300)].copy()
    d["r_close"] = d["actual"] - d["close"]
    d["r_open"] = d["actual"] - d["open"]
    d["move"] = d["close"] - d["open"]
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["pair"] = [tuple(sorted([a, b])) for a, b in zip(d["TEAM_H"], d["TEAM_R"])]
    d["series"] = d["yr"].astype(str) + "|" + d["pair"].astype(str)

    d = d.sort_values(["series", "date"]).reset_index(drop=True)
    d["gno"] = d.groupby("series").cumcount() + 1
    d["game1"] = d["gno"] == 1
    d["elim"] = False
    d["mutual"] = False
    for s, g in d.groupby("series"):
        w = {g["pair"].iloc[0][0]: 0, g["pair"].iloc[0][1]: 0}
        for idx, r in g.iterrows():
            if max(w.values()) == 3:
                d.at[idx, "elim"] = True
                if min(w.values()) == 3:
                    d.at[idx, "mutual"] = True
            win = r["TEAM_H"] if r["PTS_H"] > r["PTS_R"] else r["TEAM_R"]
            if win in w:
                w[win] += 1
    return d


def batt(s, lab, col="r_close"):
    live = s[s[col] != 0]
    if len(live) < 20:
        return None
    un = (live[col] < 0).mean()
    se = np.sqrt(un * (1 - un) / len(live))
    t, p = stats.ttest_1samp(s[col], 0.0)
    seas = s.groupby("yr")[col].mean()
    return {"state": lab, "n": len(s), "push": int((s[col] == 0).sum()),
            "mean": round(s[col].mean(), 3),
            "median": round(s[col].median(), 2),
            "trim10": round(stats.trim_mean(s[col], 0.1), 3),
            "UNDER %": round(100 * un, 2),
            "95% CI": f"[{100*(un-1.96*se):.1f}, {100*(un+1.96*se):.1f}]",
            "ROI110": round(100 * (un * (100 / 110) - (1 - un)), 2),
            "t": round(t, 2), "p": round(p, 4),
            "szn<0": f"{int((seas < 0).sum())}/{len(seas)}"}


def fe(d, flag, restrict=None):
    """Within-series fixed effect: demean both sides inside each series."""
    x = d if restrict is None else d[restrict]
    x = x.groupby("series").filter(lambda g: g[flag].nunique() == 2)
    y = x["r_close"] - x.groupby("series")["r_close"].transform("mean")
    t_ = x[flag].astype(float)
    t_ = t_ - x.groupby("series")[flag].transform("mean").astype(float)
    if t_.std() == 0:
        return None
    b = (t_ * y).sum() / (t_ ** 2).sum()
    resid = y - b * t_
    dof = len(x) - x["series"].nunique() - 1
    se = np.sqrt((resid ** 2).sum() / dof / (t_ ** 2).sum())
    return {"series used": x["series"].nunique(), "n": len(x),
            "beta": round(b, 3), "se": round(se, 3),
            "t": round(b / se, 2),
            "p": round(2 * (1 - stats.norm.cdf(abs(b / se))), 4)}


def main():
    d = load()
    print(f"{len(d):,} playoff games, {d['series'].nunique()} series, "
          f"{d['yr'].nunique()} postseasons\n")

    print("=" * 116)
    print("BATTERY — residual vs the CLOSING total (negative = under)")
    print("=" * 116)
    rows = [batt(d[d["game1"]], "GAME 1"),
            batt(d[d["elim"]], "ELIMINATION (all)"),
            batt(d[d["elim"] & ~d["mutual"]], "elimination, single-sided"),
            batt(d[d["mutual"]], "elimination, mutual (G7)"),
            batt(d[~d["game1"]], "games 2+ [reference]"),
            batt(d[~d["game1"] & ~d["elim"]], "neither G1 nor elim"),
            batt(d, "all playoff games")]
    print(pd.DataFrame([r for r in rows if r]).to_string(index=False))
    print(f"\n  break-even {100*BE:.2f}%")

    g1 = d[d["game1"]]["r_close"].mean()
    g2 = d[~d["game1"]]["r_close"].mean()
    t, p = stats.ttest_ind(d[d["game1"]]["r_close"],
                           d[~d["game1"]]["r_close"], equal_var=False)
    print(f"\n  Game 1 vs games 2+:  {g1:+.3f} vs {g2:+.3f}  "
          f"delta {g1-g2:+.3f}  t={t:+.2f}  p={p:.4f}")

    print("\n" + "=" * 116)
    print("WITHIN-SERIES FIXED EFFECTS (matchup held constant)")
    print("=" * 116)
    r = fe(d, "game1")
    print(f"  Game 1, all other games in series:   {r}")
    r = fe(d, "game1", d["gno"] <= 4)
    print(f"  Game 1 vs games 2-4 only:            {r}")
    r = fe(d, "elim")
    print(f"  Elimination, all other in series:    {fe(d, 'elim')}")

    print("\n" + "=" * 116)
    print("PRICE DISCOVERY — attribution identity")
    print("=" * 116)
    for lab, s in (("GAME 1", d[d["game1"]]), ("ELIMINATION", d[d["elim"]]),
                   ("games 2+", d[~d["game1"]])):
        ao, co, ac = s["r_open"].mean(), s["move"].mean(), s["r_close"].mean()
        uo = (s[s["r_open"] != 0]["r_open"] < 0).mean()
        uc = (s[s["r_close"] != 0]["r_close"] < 0).mean()
        print(f"  {lab:12} open err {ao:+.3f}  correction {co:+.3f} "
              f"({100*co/ao:5.1f}%)  remaining {ac:+.3f}   "
              f"under@open {100*uo:.1f}%  under@close {100*uc:.1f}%")

    print("\n" + "=" * 116)
    print("TRANSITION — first elimination game vs the game immediately before it")
    print("=" * 116)
    deltas = []
    for s, g in d.groupby("series"):
        g = g.sort_values("gno")
        e = g[g["elim"]]
        if e.empty:
            continue
        first = e["gno"].min()
        prev = g[g["gno"] == first - 1]
        if prev.empty:
            continue
        deltas.append({"series": s, "gno": first,
                       "prev R": prev["r_close"].iloc[0],
                       "elim R": e[e["gno"] == first]["r_close"].iloc[0]})
    T = pd.DataFrame(deltas)
    T["dR"] = T["elim R"] - T["prev R"]
    t, p = stats.ttest_1samp(T["dR"], 0.0)
    print(f"  {len(T)} series reached an elimination game")
    print(f"  mean prev-game residual {T['prev R'].mean():+.3f}   "
          f"mean elimination residual {T['elim R'].mean():+.3f}")
    print(f"  mean change dR {T['dR'].mean():+.3f}  median {T['dR'].median():+.2f}"
          f"  t={t:+.2f}  p={p:.4f}   negative in "
          f"{int((T['dR']<0).sum())}/{len(T)}")

    print("\n" + "=" * 116)
    print("DECOMPOSITION — is an H1 under offset by Q4 fouling?")
    print("=" * 116)
    try:
        from halves import period_scores
        w = period_scores("Playoffs")
        keep = ["gid", "q1", "q2", "q3", "q4", "h1", "h2"]
        m = d.merge(w[keep], on="gid", how="inner")
        print(f"  {len(m):,} playoff games with period scoring")
        base = m[~m["game1"] & ~m["elim"]]
        rows = []
        for lab, s in (("GAME 1", m[m["game1"]]),
                       ("ELIMINATION", m[m["elim"]]),
                       ("elim single-sided", m[m["elim"] & ~m["mutual"]]),
                       ("neither [ref] abs", base)):
            r = {"state": lab, "n": len(s)}
            for c in ("q1", "q2", "q3", "q4", "h1", "h2"):
                r[c] = (round(s[c].mean(), 2) if lab.endswith("abs")
                        else round(s[c].mean() - base[c].mean(), 2))
            rows.append(r)
        print("\n  points vs the 'neither' reference, by period"
              " (last row is the reference level):")
        print(pd.DataFrame(rows).to_string(index=False))
        from scipy import stats as st2
        print("\n  significance of the GAME 1 and ELIM period gaps vs reference:")
        for lab, s in (("GAME 1", m[m["game1"]]), ("ELIM", m[m["elim"]])):
            bits = []
            for c in ("h1", "h2", "q4"):
                t_, p_ = st2.ttest_ind(s[c], base[c], equal_var=False)
                bits.append(f"{c} {s[c].mean()-base[c].mean():+.2f} (p={p_:.3f})")
            print(f"    {lab:8} " + "   ".join(bits))
    except Exception as ex:
        print(f"  period decomposition unavailable: {ex}")


if __name__ == "__main__":
    main()
