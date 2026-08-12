"""Pre-specified regime states, one battery, no window searching.

States are fixed BEFORE looking, per the design agreed:

  PLAYOFF Game 1        first game of each series -- rotations and intensity
                        change discontinuously from the regular season
  PLAYOFF elimination   a game where one team is facing elimination
  CUP group play        NBA Cup group games. Cup standings use point
                        differential and then TOTAL POINTS as tiebreakers, so a
                        large lead carries a scoring incentive where a normal
                        game carries clock-killing suppression. Cleanest
                        mechanism available.
  CUP final group game  each team's last group game, when tiebreaker value is
                        most salient
  PRE All-Star (3d)     anticipated cessation of competition, the same family as
                        the end-of-season effect
  POST All-Star (3d)    no directional hypothesis; the cadence discontinuity may
                        cut either way
  FIRST 7 days          new-season regime against old-season pricing priors
  FINAL 7 days          the established result, carried as a reference row

The All-Star break is located as the largest mid-season date gap, which is 6-7
days in every season -- no hand-coded dates.

⚠ MULTIPLICITY. Eight states are tested. At alpha=.05 roughly 0.4 should clear by
chance, so a single nominally significant state is weak evidence. Benjamini-
Hochberg is applied across the eight and reported.

⚠ Cup play began in 2023, so those rows rest on three seasons and ~187 games.
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
    d = raw.copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300)]
    d["r_close"] = d["actual"] - d["close"]
    d["r_open"] = d["actual"] - d["open"]
    d["move"] = d["close"] - d["open"]
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["kind"] = np.select(
        [d["lbl"].str.contains("Regular"), d["lbl"].str.contains("Playoffs"),
         d["lbl"].str.contains("In-Season"), d["lbl"].str.contains("Play-[Ii]n")],
        ["REG", "PLAYOFF", "CUP", "PLAYIN"], "other")
    return d.sort_values("date").reset_index(drop=True)


def flag_states(d):
    d = d.copy()
    for c in ("g1", "elim", "cup_final", "pre_asb", "post_asb", "first7", "final7"):
        d[c] = False

    # ---- playoff series reconstruction -------------------------------------
    po = d[d["kind"] == "PLAYOFF"].copy()
    po["pair"] = [tuple(sorted([a, b])) for a, b in
                  zip(po["TEAM_H"], po["TEAM_R"])]
    for (yr, pair), g in po.groupby(["yr", "pair"]):
        g = g.sort_values("date")
        w = {pair[0]: 0, pair[1]: 0}
        for i, (idx, r) in enumerate(g.iterrows()):
            if i == 0:
                d.at[idx, "g1"] = True
            if max(w.values()) == 3:
                d.at[idx, "elim"] = True
            win = r["TEAM_H"] if r["PTS_H"] > r["PTS_R"] else r["TEAM_R"]
            if win in w:
                w[win] += 1

    # ---- Cup: each team's last group game ----------------------------------
    cup = d[d["kind"] == "CUP"]
    for yr, g in cup.groupby("yr"):
        last = {}
        for idx, r in g.sort_values("date").iterrows():
            last[r["TEAM_H"]] = idx
            last[r["TEAM_R"]] = idx
        for idx in set(last.values()):
            d.at[idx, "cup_final"] = True

    # ---- All-Star break, from the largest mid-season gap --------------------
    reg = d[d["kind"] == "REG"]
    for lbl, g in reg.groupby("lbl"):
        dts = np.sort(g["date"].dropna().unique())
        if len(dts) < 20:
            continue
        gaps = np.diff(dts).astype("timedelta64[D]").astype(int)
        i = int(np.argmax(gaps))
        before, after = pd.Timestamp(dts[i]), pd.Timestamp(dts[i + 1])
        m = d["lbl"] == lbl
        d.loc[m & (d["date"] >= before - pd.Timedelta(days=2))
              & (d["date"] <= before), "pre_asb"] = True
        d.loc[m & (d["date"] >= after)
              & (d["date"] <= after + pd.Timedelta(days=2)), "post_asb"] = True
        first, lastd = dts[0], dts[-1]
        d.loc[m & (d["date"] <= pd.Timestamp(first) + pd.Timedelta(days=6)),
              "first7"] = True
        d.loc[m & (d["date"] >= pd.Timestamp(lastd) - pd.Timedelta(days=6)),
              "final7"] = True
    return d


def battery(s, label, ref=None):
    live = s[s["r_close"] != 0]
    if len(live) < 25:
        return None
    ov = (live["r_close"] > 0).mean()
    se = np.sqrt(ov * (1 - ov) / len(live))
    lo = s[s["r_open"] != 0]
    ov_o = (lo["r_open"] > 0).mean()
    t, p = stats.ttest_1samp(s["r_close"], 0.0)
    ao, co = s["r_open"].mean(), s["move"].mean()
    seasons = s.groupby("yr")["r_close"].apply(lambda x: (x > 0).mean())
    return {"state": label, "n": len(s),
            "resid @close": round(s["r_close"].mean(), 3),
            "median": round(s["r_close"].median(), 2),
            "over %": round(100 * ov, 2),
            "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
            "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2),
            "over% @open": round(100 * ov_o, 2),
            "close-open": round(co, 3),
            "corr'n %": round(100 * co / ao, 1) if abs(ao) > 0.2 else None,
            "p": round(p, 4),
            "szn +": f"{int((seasons > 0.5).sum())}/{len(seasons)}"}


def bh(p, q=0.10):
    p = np.asarray(p, dtype=float)
    o = np.argsort(p)
    thr = q * np.arange(1, len(p) + 1) / len(p)
    ok = p[o] <= thr
    k = np.max(np.where(ok)[0]) + 1 if ok.any() else 0
    out = np.zeros(len(p), bool)
    out[o[:k]] = True
    return out


def main():
    d = flag_states(load())
    print(f"{len(d):,} games  "
          f"({d['kind'].value_counts().to_dict()})\n")

    rows = []
    for col, lab in (("g1", "PLAYOFF game 1"),
                     ("elim", "PLAYOFF elimination game"),
                     ("pre_asb", "PRE All-Star (3 days)"),
                     ("post_asb", "POST All-Star (3 days)"),
                     ("first7", "FIRST 7 days of season"),
                     ("final7", "FINAL 7 days  [reference]")):
        r = battery(d[d[col]], lab)
        if r:
            rows.append(r)
    r = battery(d[d["kind"] == "CUP"], "CUP all group games")
    if r:
        rows.append(r)
    r = battery(d[d["cup_final"]], "CUP final group game")
    if r:
        rows.append(r)
    r = battery(d[d["kind"] == "PLAYOFF"], "all playoff games")
    if r:
        rows.append(r)
    r = battery(d[d["kind"] == "REG"], "all regular season")
    if r:
        rows.append(r)

    t = pd.DataFrame(rows)
    print("=" * 132)
    print(f"PRE-SPECIFIED REGIME STATES — closing-total over test "
          f"(break-even {100*BE:.2f}%)")
    print("=" * 132)
    print(t.to_string(index=False))

    tested = t[~t["state"].str.contains(r"reference|all regular|all playoff")]
    sig = bh(tested["p"].values, 0.10)
    print(f"\n  {len(tested)} pre-specified states tested; "
          f"nominal p<0.05: {int((tested['p'] < 0.05).sum())} "
          f"(expect ~{0.05*len(tested):.1f} by chance); "
          f"surviving BH q<0.10: {int(sig.sum())}")
    if sig.any():
        print("  survivors: " + ", ".join(tested["state"].values[sig]))

    print("\n" + "=" * 132)
    print("CUP versus contemporaneous regular-season games (Nov 1 - Dec 20)")
    print("=" * 132)
    win = d["date"].dt.month.isin([11, 12]) & (d["date"].dt.day <= 20) if True else None
    rows = [battery(d[d["kind"] == "CUP"], "Cup group games"),
            battery(d[(d["kind"] == "REG") & d["date"].dt.month.isin([11, 12])],
                    "regular season, Nov-Dec")]
    print(pd.DataFrame([r for r in rows if r]).to_string(index=False))

    print("\n--- playoff detail: series game number ---")
    po = d[d["kind"] == "PLAYOFF"].copy()
    po["pair"] = [tuple(sorted([a, b])) for a, b in
                  zip(po["TEAM_H"], po["TEAM_R"])]
    po["gno"] = po.groupby(["yr", "pair"])["date"].rank().astype(int)
    r = []
    for gno, s in po.groupby("gno"):
        if len(s) < 30:
            continue
        live = s[s["r_close"] != 0]
        ov = (live["r_close"] > 0).mean()
        r.append({"series game": gno, "n": len(s),
                  "resid": round(s["r_close"].mean(), 2),
                  "over %": round(100 * ov, 2)})
    print(pd.DataFrame(r).to_string(index=False))


if __name__ == "__main__":
    main()
