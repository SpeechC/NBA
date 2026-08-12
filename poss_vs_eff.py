"""Possessions or efficiency? The test that decides the bench mechanism.

The visitor's prior-season road orientation predicts BOTH teams' Q3-Q1 splits
out of sample (home t=+5.38, away t=+5.06, 5/5 seasons). Two mechanisms explain
that equally well, because both are properties of the GAME rather than a team:

  COURT ORIENTATION   shooting toward one's own bench aids scoring -> the effect
                      runs through EFFICIENCY (points per possession)
  PACE ALLOCATION     a team's style yields a slow Q1 and fast Q3, and
                      possessions are shared -> the effect runs through
                      POSSESSIONS

⚠ POSSESSION COUNT, CORRECTED. A first version counted non-null STARTTYPE, which
is populated on EVERY event inside a possession, not once per possession -- it
returned 47 possessions per team-quarter against a true ~24. STARTTIME/ENDTIME
delimit a possession and every event within it carries the same pair, so
COUNT(DISTINCT STARTTIME||ENDTIME) per game-period is the correct count. Points
come from period_scores(), which reads the authoritative SCORE column rather than
parsing event text.

Points decompose as  pts = poss x ppp, so

    d(pts) ~ d(poss) * ppp_bar  +  poss_bar * d(ppp)

and the two channels can be attributed separately. Possessions are counted from
STARTTYPE, which marks a possession start in the play-by-play, rather than from
the FGA/FTA/TOV/ORB formula -- no estimation error, and quarter-level counts are
what we need.

If the effect is in efficiency, the physical mechanism is credible. If it is in
possessions, this is a pace trait and should be described as such.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
TEAM_LO, TEAM_HI = 1610612737, 1610612766
MIN_PRIOR = 60


def quarter_poss():
    """Possessions per GAME-period: distinct (STARTTIME, ENDTIME) pairs."""
    con = duckdb.connect()
    q = f"""
    SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
           PERIOD AS p,
           count(DISTINCT (CAST(STARTTIME AS VARCHAR) || '|'
                           || CAST(ENDTIME AS VARCHAR))) AS poss
    FROM read_parquet('{PBP}')
    WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
      AND STARTTIME IS NOT NULL AND ENDTIME IS NOT NULL
    GROUP BY gid, p
    """
    return con.execute(q).fetchdf()


def main():
    qp = quarter_poss()
    from halves import period_scores
    ps = period_scores("RegularSeason")
    pts = ps.melt(id_vars="gid", value_vars=["q1", "q2", "q3", "q4"],
                  var_name="p", value_name="pts")
    pts["p"] = pts["p"].str[1].astype(int)
    g = qp.merge(pts, on=["gid", "p"], how="inner")
    print(f"{len(g):,} game-quarter rows")
    print(f"  mean possessions per GAME-quarter: {g['poss'].mean():.2f} "
          f"(~{g['poss'].mean()/2:.1f} per team)")
    print(f"  mean points per GAME-quarter:      {g['pts'].mean():.2f}")
    print(f"  implied points per possession:     {(g['pts']/g['poss']).mean():.4f}")

    w = g.pivot(index="gid", columns="p", values=["poss", "pts"])
    w.columns = [f"{a}{b}" for a, b in w.columns]
    w = w.reset_index().dropna()
    w = w[(w["poss1"] > 30) & (w["poss3"] > 30) & (w["poss1"] < 80)
          & (w["poss3"] < 80)]
    w["d_poss"] = w["poss3"] - w["poss1"]
    w["d_pts"] = w["pts3"] - w["pts1"]
    w["ppp1"] = w["pts1"] / w["poss1"]
    w["ppp3"] = w["pts3"] / w["poss3"]
    w["d_ppp"] = w["ppp3"] - w["ppp1"]
    print(f"\n  {len(w):,} games with clean Q1/Q3 possession data")
    print(f"  Q1 poss {w['poss1'].mean():.2f}  Q3 poss {w['poss3'].mean():.2f}"
          f"   d {w['d_poss'].mean():+.3f}")
    print(f"  Q1 ppp  {w['ppp1'].mean():.4f}  Q3 ppp  {w['ppp3'].mean():.4f}"
          f"   d {w['d_ppp'].mean():+.4f}")

    # the out-of-sample visitor signal, exactly as in bench_oos.py
    from bench_oos import build as bench_build
    gg, L = bench_build()
    road = L[L["road"]]
    out = []
    for yr in sorted(gg["yr"].unique()):
        prior = road[road["yr"] < yr]
        if prior["yr"].nunique() < 1:
            continue
        sig = prior.groupby("team").agg(B=("q31", "mean"),
                                        n=("q31", "size")).reset_index()
        sig = sig[sig["n"] >= MIN_PRIOR]
        cur = gg[gg["yr"] == yr].merge(sig.rename(columns={"team": "TEAM_R"}),
                                       on="TEAM_R", how="inner")
        out.append(cur)
    O = pd.concat(out).merge(w, on="gid", how="inner")
    print(f"  {len(O):,} games with both the OOS signal and possession data\n")

    print("=" * 96)
    print("WHICH CHANNEL? regressing each on the visitor's prior road signal")
    print("=" * 96)
    res = {}
    for col, lab in (("d_pts", "Q3-Q1 POINTS  (game)"),
                     ("d_poss", "Q3-Q1 POSSESSIONS"),
                     ("d_ppp", "Q3-Q1 EFFICIENCY (ppp)")):
        r = np.corrcoef(O["B"], O[col])[0, 1]
        b = np.polyfit(O["B"], O[col], 1)[0]
        t = r * np.sqrt(len(O) - 2) / np.sqrt(1 - r * r)
        signs = [np.corrcoef(s["B"], s[col])[0, 1]
                 for _, s in O.groupby("yr") if len(s) > 100]
        res[col] = b
        print(f"  {lab:26} corr {r:+.4f}  slope {b:+.5f}  t={t:+.2f}  "
              f"seasons +ve {sum(1 for x in signs if x > 0)}/{len(signs)}")

    print("\n" + "=" * 96)
    print("ATTRIBUTION — d(pts) = d(poss)*ppp_bar + poss_bar*d(ppp)")
    print("=" * 96)
    ppp_bar, poss_bar = O[["ppp1", "ppp3"]].mean().mean(), \
        O[["poss1", "poss3"]].mean().mean()
    via_poss = res["d_poss"] * ppp_bar
    via_eff = poss_bar * res["d_ppp"]
    tot = via_poss + via_eff
    print(f"  mean ppp {ppp_bar:.4f}   mean possessions per quarter {poss_bar:.2f}")
    print(f"  points per unit of signal via POSSESSIONS : {via_poss:+.4f}")
    print(f"  points per unit of signal via EFFICIENCY  : {via_eff:+.4f}")
    print(f"  sum {tot:+.4f}   vs directly measured points slope "
          f"{res['d_pts']:+.4f}")
    if abs(tot) > 1e-6:
        print(f"\n  share via possessions: {100*via_poss/tot:5.1f}%")
        print(f"  share via efficiency : {100*via_eff/tot:5.1f}%")

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    if abs(via_eff) > abs(via_poss) * 1.5:
        print("  EFFICIENCY dominates -> consistent with a physical shooting")
        print("  mechanism (court orientation). Bench story stays credible.")
    elif abs(via_poss) > abs(via_eff) * 1.5:
        print("  POSSESSIONS dominate -> this is a PACE-ALLOCATION trait, not a")
        print("  shooting effect. Describe it as scoring allocation, not bench.")
    else:
        print("  Both channels contribute comparably; the data does not separate")
        print("  the two mechanisms.")


if __name__ == "__main__":
    main()
