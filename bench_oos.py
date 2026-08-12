"""Strict OOS test of the bench-orientation mechanism.

Two refinements over the first pass:

  Q3 - Q1 INSTEAD OF H2 - H1. Q1 and Q3 both open a half, are starter-heavy, and
  avoid intentional fouling, garbage time and endgame rotation. H2-H1 carries all
  of those. Q3-Q1 isolates the orientation effect far better.

  THE DISCRIMINATING TEST. Benches sit at opposite ends of the same sideline, so
  when the away team attacks the basket by its own bench, the home team is
  simultaneously attacking the basket by ITS bench. The mechanism therefore
  predicts the effect is SAME-SIGNED for both teams in a given half. So the
  visitor's historical orientation must predict the HOME team's split in that
  same game. If only the visitor's own scoring persists and nothing appears on
  the home side, this is a persistent road-team scoring-allocation effect and
  should not be called a bench effect.

Signal is strictly out of sample: for a game in season t, the visitor's
orientation B_j is estimated from that team's ROAD games in seasons BEFORE t.
Nothing from the current game or season enters it.

Tests, all in season t:
    corr(B_away, away Q3-Q1)     does the signal reproduce out of sample
    corr(B_away, HOME  Q3-Q1)    the discriminating test
    corr(B_away, GAME  Q3-Q1)    the betting-relevant quantity
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

MIN_PRIOR = 60          # prior road games required to form a signal


def build():
    from halves import period_scores
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    w = period_scores("RegularSeason")
    keep = ["gid"] + [f"{s}_p{q}" for s in ("home", "vis") for q in (1, 2, 3, 4)]
    g = d[["gid", "yr", "date", "TEAM_H", "TEAM_R"]].merge(w[keep], on="gid")

    for s, tag in (("home", "H"), ("vis", "A")):
        g[f"q31_{tag}"] = g[f"{s}_p3"] - g[f"{s}_p1"]
        g[f"h21_{tag}"] = ((g[f"{s}_p3"] + g[f"{s}_p4"])
                           - (g[f"{s}_p1"] + g[f"{s}_p2"]))
    g["q31_G"] = g["q31_H"] + g["q31_A"]
    g["h21_G"] = g["h21_H"] + g["h21_A"]
    g = g[(g["home_p1"] > 5) & (g["vis_p1"] > 5)]

    # long panel for variance / persistence work
    rows = []
    for s, tag in (("home", False), ("vis", True)):
        rows.append(pd.DataFrame({
            "yr": g["yr"], "date": g["date"],
            "team": g["TEAM_H"] if s == "home" else g["TEAM_R"],
            "road": tag,
            "q31": g[f"{s}_p3"] - g[f"{s}_p1"],
            "h21": ((g[f"{s}_p3"] + g[f"{s}_p4"])
                    - (g[f"{s}_p1"] + g[f"{s}_p2"]))}))
    return g, pd.concat(rows, ignore_index=True)


def decompose(df, col, lab):
    rows = []
    for t, s in df.groupby("team"):
        if len(s) < 100:
            continue
        rows.append({"team": t, "d": s[col].mean(),
                     "sv": s[col].var(ddof=1) / len(s)})
    t = pd.DataFrame(rows)
    vo, vs = t["d"].var(ddof=1), t["sv"].mean()
    vt = max(0.0, vo - vs)
    lam = vt / (vt + vs) if vt + vs > 0 else 0.0
    print(f"  {lab:26} mean {t['d'].mean():+.3f}  Var_obs {vo:.4f}  "
          f"Var_samp {vs:.4f}  Var_true {vt:.4f} (sd {np.sqrt(vt):.3f})  "
          f"lambda {lam:.3f}")
    return t


def persistence(df, col, lab):
    ts = df[df["road"]].groupby(["yr", "team"])[col].agg(["mean", "size"])
    ts = ts.reset_index()
    ts = ts[ts["size"] >= 25]
    piv = ts.pivot(index="team", columns="yr", values="mean")
    yrs = sorted(piv.columns)
    cs = []
    for i in range(len(yrs) - 1):
        p = piv[[yrs[i], yrs[i + 1]]].dropna()
        if len(p) >= 20:
            cs.append(np.corrcoef(p.iloc[:, 0], p.iloc[:, 1])[0, 1])
    print(f"  {lab:26} year-over-year corr {np.mean(cs):+.3f}   "
          f"({', '.join(f'{c:+.2f}' for c in cs)})")


def main():
    g, L = build()
    print(f"{len(g):,} games, {L['team'].nunique()} teams, "
          f"{g['yr'].nunique()} seasons\n")

    print("=" * 100)
    print("VARIANCE AND PERSISTENCE — Q3-Q1 versus H2-H1, road games")
    print("=" * 100)
    road = L[L["road"]]
    home = L[~L["road"]]
    for col, lab in (("h21", "H2-H1"), ("q31", "Q3-Q1")):
        decompose(road, col, f"ROAD {lab}")
        decompose(home, col, f"HOME {lab}")
    print()
    for col, lab in (("h21", "H2-H1"), ("q31", "Q3-Q1")):
        persistence(L, col, f"road {lab}")

    print("\n" + "=" * 100)
    print("STRICT OOS — visitor signal from PRIOR SEASONS ONLY")
    print("=" * 100)
    out = []
    for yr in sorted(g["yr"].unique()):
        prior = road[road["yr"] < yr]
        if prior["yr"].nunique() < 1:
            continue
        sig = prior.groupby("team").agg(B_q31=("q31", "mean"),
                                        B_h21=("h21", "mean"),
                                        n=("q31", "size")).reset_index()
        sig = sig[sig["n"] >= MIN_PRIOR]
        cur = g[g["yr"] == yr].merge(
            sig.rename(columns={"team": "TEAM_R"}), on="TEAM_R", how="inner")
        out.append(cur)
    O = pd.concat(out)
    print(f"  {len(O):,} games with an out-of-sample visitor signal "
          f"(seasons {sorted(O['yr'].unique())})")
    print(f"  B_q31: mean {O['B_q31'].mean():+.3f}  sd {O['B_q31'].std():.3f}\n")

    for sig_col, tgt_pre, lab in (("B_q31", "q31", "Q3-Q1"),
                                  ("B_h21", "h21", "H2-H1")):
        print(f"  --- signal = prior road {lab} ---")
        for tgt, tl in ((f"{tgt_pre}_A", "AWAY team (validation)"),
                        (f"{tgt_pre}_H", "HOME team (DISCRIMINATING)"),
                        (f"{tgt_pre}_G", "GAME total (betting)")):
            r = np.corrcoef(O[sig_col], O[tgt])[0, 1]
            b = np.polyfit(O[sig_col], O[tgt], 1)[0]
            t = r * np.sqrt(len(O) - 2) / np.sqrt(1 - r * r)
            signs = []
            for yr, s in O.groupby("yr"):
                if len(s) > 100:
                    signs.append(np.corrcoef(s[sig_col], s[tgt])[0, 1])
            print(f"    {tl:28} corr {r:+.4f}  slope {b:+.4f}  t={t:+.2f}  "
                  f"seasons +ve {sum(1 for x in signs if x > 0)}/{len(signs)}")
        print()

    print("=" * 100)
    print("VERDICT on the mechanism")
    print("=" * 100)
    ra = np.corrcoef(O["B_q31"], O["q31_A"])[0, 1]
    rh = np.corrcoef(O["B_q31"], O["q31_H"])[0, 1]
    th = rh * np.sqrt(len(O) - 2) / np.sqrt(1 - rh * rh)
    print(f"  visitor signal -> visitor Q3-Q1 : {ra:+.4f}")
    print(f"  visitor signal -> HOME    Q3-Q1 : {rh:+.4f}  (t={th:+.2f})")
    if rh > 0 and abs(th) > 2:
        print("  -> both teams move together: consistent with COURT ORIENTATION")
    else:
        print("  -> no home-side effect: this is a persistent ROAD-TEAM")
        print("     scoring-allocation effect, not a demonstrated bench effect")


if __name__ == "__main__":
    main()
