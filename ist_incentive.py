"""IN-SEASON TOURNAMENT POINT-DIFFERENTIAL INCENTIVE — pre-registered test.

Written BEFORE any outcome was inspected. Only the data-structure checks below
were run first (game counts, line coverage, date overlap); no target was touched.

THE RULE. NBA Cup group play seeds the knockout round by, in order: head-to-head
record, then POINT DIFFERENTIAL in group play, then total points scored. Every
team plays exactly 4 group games. So in a group game a leading team has an
explicit competitive reason NOT to empty its bench, and a trailing team has one
to keep pushing. In an ordinary regular-season game neither incentive exists.

This is the CrewShock template: a rules-based, pregame-known, exogenously
scheduled state with a mechanical scoring channel. It is NOT a dispersion test.

--------------------------------------------------------------------------
PRIMARY 1 — SPREAD (strongest mechanical derivation)
    Favourite ATS cover rate, IST group games vs control.
    PREDICTED: HIGHER in IST group games.
    Derivation: the leading team is usually the favourite, and the tiebreaker
    removes its reason to coast once the game is decided.

PRIMARY 2 — TOTAL (weaker prior, sign not airtight)
    Mean signed closing-total error  e = actual - closing total.
    PREDICTED: POSITIVE relative to control.
    Derivation: both sides keep starters on the floor longer. Stated as the
    weaker of the two because higher effort also raises defensive intensity,
    so the net sign on scoring is not guaranteed by the rule.

Family-wise inference across the two primaries by max-statistic permutation.

MECHANISM (not primaries, no inference claimed)
    |final margin|, actual total, closing total.

DOSE
    Group game index 1..4 per team; the tiebreaker is most salient in the last
    group game, when standings are known. PREDICTED: effect increasing in the
    minimum of the two teams' group-game indices.

FALSIFICATION
    a) Quarterfinal games (n=12): single elimination, NO differential
       tiebreaker. PREDICTED null. Reported DESCRIPTIVELY ONLY -- 12 games
       cannot support inference and no conclusion will be drawn from them.
    b) Opening -> closing line movement. If the market already prices the
       incentive, the residual is null even when the raw effect is real. A
       null here with a live mechanism is the EFFICIENT outcome, not a
       measurement failure.

CONTROL
    Primary: regular-season games in the SAME season inside the same group-play
    date window. Robustness: all regular-season games in the same season.

POWER, stated in advance
    n = 175 group games, sd(e) ~ 13.3  ->  SE ~ 1.0 points.
    Total:  t=2 needs ~2.0 points; 80% power at ~2.8 points.
    Spread: SE of the cover rate ~3.8pp, so t=2 needs ~7.5pp.
    This test can only detect a LARGE effect. A null is uninformative about
    small ones and will be reported as such.

DECISION RULE, fixed now
    One test. No variant quantiles, windows, subgroups or interactions will be
    run afterwards regardless of the result. Any positive finding is
    hypothesis-generating pending 2026-27, not actionable: 2023-24 group play
    is development, 2024-25 and 2025-26 are holdout, and n is tiny in both.

KNOWN LIMITATIONS
    - 2024-25 carries 55 group games, not 60; five are absent from the vendor.
    - IST games are labelled separately from "Regular Season" and so have been
      excluded from every other test in this project, including all CrewShock
      work. This is the first time they are used.
    - Group opponents are fixed by a draw stratified on prior-season record,
      which is close to exogenous but not random.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label

NPERM = 5000
RNG = np.random.default_rng(20261123)


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    raw["date"] = pd.to_datetime(raw["DATE"], errors="coerce")
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    d = pd.DataFrame({
        "gid": raw["GAME-ID"].astype(str).str.strip(),
        "lbl": raw["lbl"], "date": raw["date"],
        "team_h": raw["TEAM_H"], "team_r": raw["TEAM_R"],
        "total": n("CLOSING TOTAL_H"), "open_total": n("OPENING TOTAL_H"),
        "spread": n("CLOSING SPREAD_H"), "open_spread": n("OPENING SPREAD_H"),
        "pts_h": n("PTS_H"), "pts_r": n("PTS_R")})
    d["ist"] = d["lbl"].str.contains("In-Season", na=False)
    d["rs"] = d["lbl"].str.contains("Regular Season", na=False)
    d = d[d["ist"] | d["rs"]].copy()
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["actual"] = d["pts_h"] + d["pts_r"]
    d["margin"] = d["pts_h"] - d["pts_r"]
    d["e"] = d["actual"] - d["total"]                 # signed total error
    d["spread_resid"] = d["margin"] + d["spread"]     # >0 = home beat the line
    d["abs_margin"] = d["margin"].abs()

    # favourite covers: sign(spread_resid) opposite to sign(spread_H)
    fav = np.where(d["spread"] < 0, d["spread_resid"],
                   np.where(d["spread"] > 0, -d["spread_resid"], np.nan))
    d["fav_cover"] = np.where(fav > 0, 1.0, np.where(fav < 0, 0.0, np.nan))

    # split IST into group play and the knockout quarterfinals: the QFs are the
    # last two dates of each tournament, two games each
    d["stage"] = np.where(d["ist"], "group", "rs")
    for lbl, g in d[d["ist"]].groupby("lbl"):
        qf_dates = sorted(g["date"].unique())[-2:]
        d.loc[d["ist"] & d["lbl"].eq(lbl) & d["date"].isin(qf_dates),
              "stage"] = "qf"
    return d.dropna(subset=["total", "spread", "actual"])


def group_index(d):
    """Each team's 1..4 ordering of its own group games; the game carries the
    MINIMUM of the two teams' indices (the tiebreaker binds through whichever
    team has played fewer)."""
    g = d[d["stage"] == "group"]
    long = pd.concat([
        g[["gid", "lbl", "date", "team_h"]].rename(columns={"team_h": "team"}),
        g[["gid", "lbl", "date", "team_r"]].rename(columns={"team_r": "team"})])
    long = long.sort_values("date")
    long["idx"] = long.groupby(["lbl", "team"]).cumcount() + 1
    return long.groupby("gid")["idx"].min()


def cmp(a, b, col, binary=False):
    x, y = a[col].dropna(), b[col].dropna()
    diff = x.mean() - y.mean()
    if binary:
        se = np.sqrt(x.mean()*(1-x.mean())/len(x) + y.mean()*(1-y.mean())/len(y))
    else:
        se = np.sqrt(x.var(ddof=1)/len(x) + y.var(ddof=1)/len(y))
    return len(x), x.mean(), y.mean(), diff, diff/se


def main():
    d = build()
    grp = d[d["stage"] == "group"]
    qf = d[d["stage"] == "qf"]
    print(f"  IST group games {len(grp)}   quarterfinals {len(qf)}")
    print(f"  by season: " + "   ".join(
        f"{y}: {len(g)}" for y, g in grp.groupby("yr")))

    # control: same season, inside that season's group-play date window
    ctl = []
    for y, g in grp.groupby("yr"):
        lo, hi = g["date"].min(), g["date"].max()
        ctl.append(d[(d["yr"] == y) & (d["stage"] == "rs")
                     & d["date"].between(lo, hi)])
    ctl = pd.concat(ctl)
    ctl_all = d[(d["stage"] == "rs") & d["yr"].isin(grp["yr"].unique())]
    print(f"  control, same window {len(ctl)}   control, whole season "
          f"{len(ctl_all)}")
    print(f"  sd(e) = {d['e'].std():.2f}   implied SE at n={len(grp)}: "
          f"{d['e'].std()/np.sqrt(len(grp)):.2f} points")

    DEV = grp["yr"] <= 2023
    WIN = [("ALL 3 seasons", grp, ctl),
           ("2023-24 [dev]", grp[DEV], ctl[ctl["yr"] <= 2023]),
           ("2024-25 + 2025-26", grp[~DEV], ctl[ctl["yr"] > 2023])]

    print("\n" + "=" * 100)
    print("PRIMARY 1 — FAVOURITE ATS COVER RATE   (predicted HIGHER in IST)")
    print("=" * 100)
    print(f"  {'window':22}{'n':>7}{'IST':>10}{'control':>10}{'diff':>9}{'t':>8}")
    for lab, a, b in WIN:
        n_, m1, m0, dd, t_ = cmp(a, b, "fav_cover", binary=True)
        print(f"  {lab:22}{n_:7,}{100*m1:9.2f}%{100*m0:9.2f}%{100*dd:+8.2f}pp"
              f"{t_:8.2f}")

    print("\n" + "=" * 100)
    print("PRIMARY 2 — SIGNED CLOSING-TOTAL ERROR   (predicted POSITIVE)")
    print("=" * 100)
    print(f"  {'window':22}{'n':>7}{'IST e':>10}{'control e':>11}{'diff':>9}"
          f"{'t':>8}")
    for lab, a, b in WIN:
        n_, m1, m0, dd, t_ = cmp(a, b, "e")
        print(f"  {lab:22}{n_:7,}{m1:+10.3f}{m0:+11.3f}{dd:+9.3f}{t_:8.2f}")

    print("\n" + "=" * 100)
    print("MECHANISM — is anything actually different about these games?")
    print("=" * 100)
    print(f"  {'quantity':22}{'IST':>10}{'control':>10}{'diff':>9}{'t':>8}")
    for col, nm in (("abs_margin", "|final margin|"),
                    ("actual", "actual total"),
                    ("total", "CLOSING total"),
                    ("spread", "closing spread (H)")):
        _, m1, m0, dd, t_ = cmp(grp, ctl, col)
        print(f"  {nm:22}{m1:10.3f}{m0:10.3f}{dd:+9.3f}{t_:8.2f}")

    print("\n" + "=" * 100)
    print("DOSE — group-game index (min of the two teams), effect predicted "
          "to RISE")
    print("=" * 100)
    gi = group_index(d)
    g2 = grp.copy()
    g2["idx"] = g2["gid"].map(gi)
    print(f"  {'idx':>5}{'n':>7}{'fav cover':>12}{'signed e':>11}"
          f"{'|margin|':>11}")
    for k in (1, 2, 3, 4):
        s = g2[g2["idx"] == k]
        if not len(s):
            continue
        print(f"  {k:>5}{len(s):7,}{100*s['fav_cover'].mean():11.2f}%"
              f"{s['e'].mean():+11.3f}{s['abs_margin'].mean():11.3f}")
    print(f"  control{'':<0}{len(ctl):>5,}{100*ctl['fav_cover'].mean():10.2f}%"
          f"{ctl['e'].mean():+11.3f}{ctl['abs_margin'].mean():11.3f}")

    print("\n" + "=" * 100)
    print("FALSIFICATION (a) — QUARTERFINALS, no differential tiebreaker")
    print("  DESCRIPTIVE ONLY: n=12 supports no inference and none is drawn")
    print("=" * 100)
    print(f"  n={len(qf)}   fav cover {100*qf['fav_cover'].mean():.2f}%   "
          f"signed e {qf['e'].mean():+.3f}   |margin| {qf['abs_margin'].mean():.2f}")

    print("\n" + "=" * 100)
    print("FALSIFICATION (b) — does the market already move for these games?")
    print("=" * 100)
    for col, nm in (("open_total", "total"), ("open_spread", "spread")):
        a = (grp[col.replace("open_", "") if col != "open_total" else "total"]
             - grp[col])
        b = (ctl[col.replace("open_", "") if col != "open_total" else "total"]
             - ctl[col])
        a, b = a.dropna(), b.dropna()
        dd = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
        print(f"  open->close {nm:8} move: IST {a.mean():+.4f}   control "
              f"{b.mean():+.4f}   diff {dd:+.4f} (t={dd/se:+.2f})")

    print("\n" + "=" * 100)
    print(f"FAMILY-WISE PERMUTATION — IST flag reshuffled within season x week, "
          f"{NPERM} reps")
    print("=" * 100)
    pool = pd.concat([grp, ctl]).copy()
    pool["blk"] = (pool["yr"].astype(str) + "-"
                   + pool["date"].dt.isocalendar().week.astype(str))
    flag = pool["stage"].eq("group").values
    blocks = [np.where(pool["blk"].values == u)[0]
              for u in pool["blk"].unique()]
    obs, stats = {}, {}
    for col, binary in (("fav_cover", True), ("e", False)):
        v = pool[col].values.astype(float)
        ok = ~np.isnan(v)
        o = np.nanmean(v[flag & ok]) - np.nanmean(v[~flag & ok])
        sd = np.nanstd(v[ok])
        obs[col] = o
        null = np.empty(NPERM)
        for j in range(NPERM):
            f2 = flag.copy()
            for b_ in blocks:
                f2[b_] = flag[b_][RNG.permutation(len(b_))]
            null[j] = (np.nanmean(v[f2 & ok]) - np.nanmean(v[~f2 & ok]))
        stats[col] = (null, o / sd)
        p = (1 + np.sum(np.abs(null) >= abs(o))) / (NPERM + 1)
        u = "pp" if binary else "pts"
        sc = 100 if binary else 1
        print(f"  {col:12} observed {sc*o:+.3f}{u}   null {sc*null.mean():+.3f} "
              f"sd {sc*null.std():.3f}   marginal p={p:.4f}")
    # family-wise: max |standardised statistic| across the two primaries
    zs = np.column_stack([np.abs(stats[c][0] / np.nanstd(pool[c].values))
                          for c in ("fav_cover", "e")]).max(axis=1)
    for c in ("fav_cover", "e"):
        z = abs(stats[c][1])
        print(f"  {c:12} FAMILY-WISE p = "
              f"{(1 + np.sum(zs >= z)) / (NPERM + 1):.4f}")


if __name__ == "__main__":
    main()
