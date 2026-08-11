"""Acceptance gate for newly acquired odds data. Run BEFORE the holdout test.

A holdout is only as good as the data behind it, and this project has already
been bitten once: an overtime-stripped file silently dragged the over rate to
47.95% and would have manufactured a fake under bias in every totals result.
That file looked completely normal until specifically checked.

Nine checks. The first is the one that matters most.

    python accept_new_data.py --odds /path/to/new.csv [--season 2024-2025]

Exit status is non-zero if any CRITICAL check fails, so this can gate a pipeline.
"""

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats

CRITICAL = []
WARNINGS = []


def check(name, ok, detail, critical=True):
    tag = "PASS" if ok else ("FAIL" if critical else "WARN")
    print(f"  [{tag}] {name}: {detail}")
    if not ok:
        (CRITICAL if critical else WARNINGS).append(name)
    return ok


def load(path):
    df = pd.read_csv(path, low_memory=False)
    cols = df.columns
    a = "DATASET_H" if "DATASET_H" in cols else None
    b = "BIGDATABALL\nDATASET_H" if "BIGDATABALL\nDATASET_H" in cols else None
    if a and b:
        df["season"] = df[a].fillna(df[b])
    elif a:
        df["season"] = df[a]
    elif b:
        df["season"] = df[b]
    else:
        raise SystemExit("no season label column found (DATASET_H / BIGDATABALL DATASET_H)")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", required=True)
    ap.add_argument("--season", help="restrict checks to one season label fragment")
    a = ap.parse_args()

    df = load(a.odds)
    r = df[df["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    if a.season:
        r = r[r["season"].str.contains(a.season, na=False)]
    print(f"\nfile: {a.odds}")
    print(f"rows: {len(df):,}   regular-season rows checked: {len(r):,}")
    print(f"seasons present: {sorted(r['season'].dropna().unique())}\n")
    if len(r) == 0:
        raise SystemExit("no matching rows — check the season label")

    for c in ("PTS_H", "PTS_R", "CLOSING TOTAL_H", "OPENING TOTAL_H",
              "CLOSING SPREAD_H", "OPENING SPREAD_H"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["total"] = r["PTS_H"] + r["PTS_R"]
    r["margin"] = r["PTS_H"] - r["PTS_R"]

    # ---- 1. OVERTIME GAMES PRESENT -- the trap that already caught us --------
    ot = r["OT1_H"].notna() if "OT1_H" in r.columns else pd.Series(False, index=r.index)
    rate = ot.mean()
    check("overtime games present",
          0.03 <= rate <= 0.09,
          f"{ot.sum():,} of {len(r):,} = {100*rate:.2f}% (expect 5-7%; "
          f"0% means OT games were stripped and totals results will be poisoned)")

    # ---- 2. over/under balance ----------------------------------------------
    d = (r["total"] - r["CLOSING TOTAL_H"]).dropna()
    nz = d[d != 0]
    over = (nz > 0).mean()
    z = (over - .5) / np.sqrt(.25 / len(nz))
    check("over rate near 50%", abs(z) < 3.5,
          f"{100*over:.2f}% on n={len(nz):,} (z={z:+.2f}); "
          f"a value near 48% is the OT-stripping signature")

    # ---- 3. closing must beat opening ----------------------------------------
    m = r[["CLOSING TOTAL_H", "OPENING TOTAL_H", "total"]].dropna()
    rc = np.sqrt(np.mean((m["CLOSING TOTAL_H"] - m["total"]) ** 2))
    ro = np.sqrt(np.mean((m["OPENING TOTAL_H"] - m["total"]) ** 2))
    check("closing total beats opening", rc < ro,
          f"close RMSE {rc:.3f} vs open {ro:.3f}")

    ms = r[["CLOSING SPREAD_H", "OPENING SPREAD_H", "margin"]].dropna()
    ms = ms[ms["CLOSING SPREAD_H"].abs() <= 25]
    rcs = np.sqrt(np.mean((-ms["CLOSING SPREAD_H"] - ms["margin"]) ** 2))
    ros = np.sqrt(np.mean((-ms["OPENING SPREAD_H"] - ms["margin"]) ** 2))
    check("closing spread beats opening", rcs < ros,
          f"close RMSE {rcs:.3f} vs open {ros:.3f}")

    # ---- 4. ATS balance ------------------------------------------------------
    ats = (r["margin"] + r["CLOSING SPREAD_H"]).dropna()
    nz = ats[ats != 0]
    cov = (nz > 0).mean()
    z = (cov - .5) / np.sqrt(.25 / len(nz))
    check("home ATS cover near 50%", abs(z) < 3.5,
          f"{100*cov:.2f}% on n={len(nz):,} (z={z:+.2f})")

    # ---- 5. half-point ticks / contamination --------------------------------
    for c, lim in (("CLOSING SPREAD_H", 25), ("OPENING SPREAD_H", 25)):
        v = r[c].dropna()
        bad = (v.abs() > lim).sum()
        check(f"{c} free of contamination", bad == 0,
              f"{bad} rows outside +/-{lim} (range {v.min():.1f}..{v.max():.1f})",
              critical=False)
    for c in ("CLOSING TOTAL_H", "OPENING TOTAL_H"):
        v = r[c].dropna()
        off = (np.abs(v * 2 - np.round(v * 2)) > 1e-6).sum()
        oor = (~v.between(150, 300)).sum()
        check(f"{c} on half-point ticks", off == 0 and oor <= 2,
              f"{off} off-tick, {oor} out of range", critical=False)

    # ---- 6. game id format ---------------------------------------------------
    g = df["GAME-ID"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(10)
    check("game ids resolve to 10 chars", set(g.str.len()) == {10},
          f"lengths {sorted(set(g.str.len()))}, prefixes {sorted(set(g.str[:2]))}")

    # ---- 7. duplicates -------------------------------------------------------
    check("no duplicate game ids", df["GAME-ID"].duplicated().sum() == 0,
          f"{df['GAME-ID'].duplicated().sum()} duplicates")

    # ---- 8. moneyline coherence ---------------------------------------------
    if "MONEYLINE_H" in r.columns:
        mh = pd.to_numeric(r["MONEYLINE_H"], errors="coerce")
        mr = pd.to_numeric(r["MONEYLINE_R"], errors="coerce")
        f = lambda x: np.where(x < 0, -x / (-x + 100), 100 / (x + 100))
        ph, pa = f(mh.values), f(mr.values)
        hold = np.nanmean(ph + pa) - 1
        check("moneyline hold plausible", 0.02 < hold < 0.08,
              f"{100*hold:.2f}% (retail ~4-5%)", critical=False)

    # ---- 9. season completeness ---------------------------------------------
    for s, n in r.groupby("season").size().items():
        check(f"season size: {s}", 900 <= n <= 1300, f"{n} games", critical=False)

    print()
    if CRITICAL:
        print(f"REJECTED — {len(CRITICAL)} critical failure(s): {CRITICAL}")
        print("Do not run the holdout on this file.")
        sys.exit(1)
    print("ACCEPTED" + (f" with {len(WARNINGS)} warning(s): {WARNINGS}" if WARNINGS else ""))
    print("Safe to run: python run_holdout_2425.py --odds " + a.odds)


if __name__ == "__main__":
    main()
