"""TEST 3 — where do the extra ~3 points come from?

The last 7 days of a regular season score 3.0 points above the closing total,
as a central shift (median +3.00, not a tail artefact). This asks WHICH
mechanical component moves, because the answer determines which market to attack.

  if it is PACE (more possessions)        -> full-game totals are the right market
  if it is DEFENSIVE efficiency           -> team totals, and the effect should be
                                             visible on both sides
  if it is concentrated in Q4 or H2       -> quarter/half totals, where the same
                                             absolute change is a larger share of
                                             a smaller number
  if it is GARBAGE TIME                   -> the effect is conditional on blowouts
                                             and should vanish in close games

The comparison is raw last-7-days versus rest-of-season, and that is the FAIR
comparison here rather than a matched one: mean closing totals are 224.53 and
224.04: the market considers these games equivalent. Same price, different
outcome, so any difference in components is the market's error.

Components from the odds file's box score (FGA/FTA/3PA/Reb/Assist_Turn/OEFF/DEF)
and from play-by-play for period scoring. Everything is per game, both teams
combined unless labelled.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["close_total"] = num("CLOSING TOTAL_H")
    d["spread"] = num("CLOSING SPREAD_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["resid"] = d["actual"] - d["close_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days

    for s in ("H", "R"):
        d[f"fga_{s}"], d[f"fta_{s}"] = num(f"TEAM_FGA_{s}"), num(f"TEAM_FTA_{s}")
        d[f"tpa_{s}"], d[f"reb_{s}"] = num(f"TEAM_3PA_{s}"), num(f"TEAM_Reb_{s}")
        d[f"oeff_{s}"], d[f"deff_{s}"] = num(f"TEAM_OEFF_{s}"), num(f"TEAM_DEF_{s}")
        d[f"efg_{s}"] = num(f"TEAM_eFGP_{s}")
        d[f"ft_{s}"], d[f"fg_{s}"] = num(f"TEAM_FT_{s}"), num(f"TEAM_FG_{s}")
    # possessions: FGA + 0.44*FTA - ORB proxy. Reb here is total, so use the
    # league-standard estimate without ORB and note it is an approximation.
    d["poss"] = ((d["fga_H"] + 0.44 * d["fta_H"]) +
                 (d["fga_R"] + 0.44 * d["fta_R"])) / 2
    d["fga"] = d["fga_H"] + d["fga_R"]
    d["fta"] = d["fta_H"] + d["fta_R"]
    d["tpa"] = d["tpa_H"] + d["tpa_R"]
    d["tpa_rate"] = d["tpa"] / d["fga"]
    d["ft_rate"] = d["fta"] / d["fga"]
    d["oeff"] = (d["oeff_H"] + d["oeff_R"]) / 2
    d["deff"] = (d["deff_H"] + d["deff_R"]) / 2
    d["efg"] = (d["efg_H"] + d["efg_R"]) / 2
    d["pts_per_poss"] = d["actual"] / (2 * d["poss"])
    # favourite / underdog scoring
    d["fav_pts"] = np.where(d["spread"] < 0, d["PTS_H"], d["PTS_R"])
    d["dog_pts"] = np.where(d["spread"] < 0, d["PTS_R"], d["PTS_H"])
    return d.dropna(subset=["close_total", "actual", "date"])


def periods():
    con = duckdb.connect()
    q = f"""
    WITH s AS (
      SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid, PERIOD, SCORE,
             row_number() OVER (PARTITION BY GAME_ID, PERIOD
                 ORDER BY CAST(PCTIMESTRING AS INTEGER) DESC) AS rn
      FROM read_parquet('{PBP}')
      WHERE SEASON_TYPE='RegularSeason' AND SCORE IS NOT NULL AND PERIOD<=4)
    SELECT gid, PERIOD, SCORE FROM s WHERE rn=1"""
    d = con.execute(q).fetchdf()
    p = d["SCORE"].str.split("-", expand=True)
    d["tot"] = (pd.to_numeric(p[0].str.strip(), errors="coerce")
                + pd.to_numeric(p[1].str.strip(), errors="coerce"))
    w = d.pivot_table(index="gid", columns="PERIOD", values="tot",
                      aggfunc="first").dropna()
    w.columns = [f"c{c}" for c in w.columns]
    for q_ in (4, 3, 2):
        w[f"q{q_}"] = w[f"c{q_}"] - w[f"c{q_-1}"]
    w["q1"] = w["c1"]
    w["h1"] = w["q1"] + w["q2"]
    w["h2"] = w["q3"] + w["q4"]
    return w.reset_index()[["gid", "q1", "q2", "q3", "q4", "h1", "h2"]]


def cmp(d, cols):
    late = d[d["days_left"] <= 7]
    rest = d[d["days_left"] > 14]
    rows = []
    for c in cols:
        a, b = late[c].dropna(), rest[c].dropna()
        if len(a) < 50:
            continue
        t, p = stats.ttest_ind(a, b, equal_var=False)
        sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        rows.append({"component": c, "last 7d": round(a.mean(), 3),
                     "rest": round(b.mean(), 3),
                     "diff": round(a.mean() - b.mean(), 3),
                     "diff SD": round((a.mean() - b.mean()) / sd, 3),
                     "t": round(t, 2), "p": round(p, 4)})
    return pd.DataFrame(rows)


def main():
    d = load()
    d = d.merge(periods(), on="gid", how="left")
    print(f"{len(d):,} games   last-7 {int((d['days_left']<=7).sum()):,}   "
          f"rest {int((d['days_left']>14).sum()):,}\n")

    print("=" * 104)
    print("Same price, different outcome — where does the difference sit?")
    print("=" * 104)
    print(cmp(d, ["close_total", "actual", "resid"]).to_string(index=False))

    print("\n--- pace vs efficiency ---")
    print(cmp(d, ["poss", "pts_per_poss", "oeff", "deff", "efg",
                  "fga", "fta", "tpa", "tpa_rate", "ft_rate"]).to_string(index=False))

    print("\n--- by period ---")
    print(cmp(d, ["q1", "q2", "q3", "q4", "h1", "h2"]).to_string(index=False))

    print("\n--- favourite vs underdog scoring ---")
    print(cmp(d, ["fav_pts", "dog_pts"]).to_string(index=False))

    print("\n" + "=" * 104)
    print("Is it garbage time? residual by closing spread, last 7 days only")
    print("=" * 104)
    late = d[d["days_left"] <= 7].copy()
    late["band"] = pd.cut(late["spread"].abs(), [-1, 4, 8, 12, 99],
                          labels=["0-4", "5-8", "9-12", "13+"])
    rows = []
    for b, s in late.groupby("band", observed=True):
        if len(s) < 40:
            continue
        ov = (s["resid"] > 0).mean()
        rows.append({"|spread|": b, "n": len(s),
                     "residual": round(s["resid"].mean(), 3),
                     "median": round(s["resid"].median(), 2),
                     "over %": round(100 * ov, 2),
                     "ROI": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  If garbage time drove it, the effect would concentrate in")
    print("  large spreads and vanish in close games.")


if __name__ == "__main__":
    main()
