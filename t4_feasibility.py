"""
===============================================================================
 T4 FEASIBILITY + POWER SCREEN — calendar/assignment shocks on the pregame line
===============================================================================
 The pre-filter says the pregame full-game board is cheap: 1.0c spread, a
 2.2c round trip = 0.9 POINTS of total. So an effect must move the true total
 by more than ~0.9 points to be worth trading.

 Before preregistering anything, answer the question the CBB Phase-2 post
 mortem made binding ("power-check every bar, including the positive
 control's, BEFORE setting it"):

   Can ONE WNBA season detect an effect as small as 0.9 points?

 Structure of the edge, stated so it can fail:
   (a) the factor must actually move scoring   -> realized coefficient != 0
   (b) the market must NOT price it            -> line coefficient ~ 0
   edge = (a) - (b), and it must clear 0.9 points.

 Factors buildable from data already in hand (no new sources):
   MATINEE     tip before 17:00 ET (ESPN true tip times)
   B2B         either team playing on 0 days rest
   REST_DIFF   home rest days minus away rest days
   ROADTRIP    away team's consecutive road games
 Referee crews are NOT included: no WNBA assignment feed is in the repo. That
 is a data-acquisition question, reported separately.

 RESULTS (2026-08-25) — T4 CANNOT BE RESOLVED ON WNBA DATA.

 A. POWER. Minimum detectable effect at 80% power vs the 0.9-pt bar:
      matinee    n=43 vs 240   MDE  9.7 pts  = 11x the bar
      b2b        n=17 vs 266   MDE 14.7 pts  = 16x
      rest_diff  continuous    MDE 2.12 p/sd =  2x
      roadtrip   continuous    MDE 3.05 p/sd =  3x
    Every design is underpowered by 2-16x. An effect large enough for this
    season to SEE would be far too large to be plausible; an effect small
    enough to be plausible cannot be distinguished from zero.

 B. EFFECTS (only 59 games carry a Kalshi pregame line -- the real binding
    constraint). realized / market-line / gap, in points:
      matinee   -0.03 (4.64) / -0.56 (2.63) / +0.53
      b2b      +10.03 (6.37) / -2.25 (3.67) / +12.29
      rest_diff -0.59 (1.16) / -0.20 (0.66) / -0.39
      roadtrip  +1.37 (1.55) / +1.08 (0.86) / +0.29
    The b2b gap is eye-catching and meaningless: its own MDE is 14.7 pts, so
    a +10 point estimate sits BELOW the detection floor. Exactly the shape of
    thing that has died all day.

 C. WHERE IT COULD BE ANSWERED (NBA master, 9,489 games, 8 seasons):
      rare binary @2%    MDE 4.27p = 4.7x bar
      binary @10%        MDE 1.99p = 2.2x
      binary @30%        MDE 1.30p = 1.4x
      CONTINUOUS per sd  MDE 0.60p = 0.7x  <- the only powered design
    So even 8 NBA seasons cannot resolve rare "spot" factors. Only CONTINUOUS
    calendar variables (rest differential, travel distance, density) on the
    full panel clear the bar -- and that is an NBA-thread question.

 D. REFEREE CREWS: no WNBA assignment feed exists in this repo (crew_* is
    NBA-only). Acquisition question, unscreenable until a feed exists.

 VERDICT: do NOT preregister a WNBA calendar test. It would be the CBB
 Phase-2 error repeated -- a bar that was never attainable.

 Read-only.
===============================================================================
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402

COST_PTS = 0.9          # round-trip cost on the pregame board, in points


def build():
    b = pd.read_csv(R.BREF)
    b["date"] = pd.to_datetime(b.date.astype(str), format="%Y%m%d")
    b["total"] = b.a_final + b.h_final
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ck["date"] = pd.to_datetime(ck.date.astype(str), format="%Y%m%d")
    # WNBA season is entirely within EDT, so a fixed -4h offset is exact
    # (and avoids a tzdata dependency this env lacks).
    _t = pd.to_datetime(ck.tip_utc, utc=True) - pd.Timedelta(hours=4)
    ck["tip_et_h"] = _t.dt.hour + _t.dt.minute / 60

    def code(n):
        for city, cs in R.CITY_CODES.items():
            if str(n).startswith(city):
                return cs[0]
        return None
    b["ac"], b["hc"] = b.away.map(code), b.home.map(code)
    ck["ac2"] = ck.ac.map(lambda x: next((c[0] for c in R.CITY_CODES.values()
                                          if x in c), x))
    ck["hc2"] = ck.hc.map(lambda x: next((c[0] for c in R.CITY_CODES.values()
                                          if x in c), x))
    b["key"] = b.date.dt.strftime("%Y%m%d") + b.ac + b.hc
    ck["key"] = ck.date.dt.strftime("%Y%m%d") + ck.ac2 + ck.hc2
    d = b.merge(ck[["key", "tip_et_h"]], on="key", how="left")

    # per-team game log -> rest days and road-trip length
    logs = []
    for _, r in d.iterrows():
        logs.append({"team": r.ac, "date": r.date, "key": r.key, "home": 0})
        logs.append({"team": r.hc, "date": r.date, "key": r.key, "home": 1})
    lg = pd.DataFrame(logs).dropna(subset=["team"]).sort_values(["team", "date"])
    lg["rest"] = lg.groupby("team").date.diff().dt.days
    lg["trip"] = 0
    for t, g in lg.groupby("team"):
        run, out = 0, []
        for h in g.home.values:
            run = 0 if h == 1 else run + 1
            out.append(run)
        lg.loc[g.index, "trip"] = out
    aw = lg[lg.home == 0].set_index("key")[["rest", "trip"]]
    hm = lg[lg.home == 1].set_index("key")[["rest"]]
    d = d.join(aw.rename(columns={"rest": "a_rest", "trip": "a_trip"}), on="key")
    d = d.join(hm.rename(columns={"rest": "h_rest"}), on="key")
    d["matinee"] = (d.tip_et_h < 17).astype(float)
    d["b2b"] = ((d.a_rest <= 1) | (d.h_rest <= 1)).astype(float)
    d["rest_diff"] = d.h_rest - d.a_rest
    d["roadtrip"] = d.a_trip
    return d


def mde(sd, n1, n0):
    """Minimum detectable effect at 80% power, 5% two-sided."""
    if n1 < 2 or n0 < 2:
        return np.nan
    return 2.8 * sd * np.sqrt(1 / n1 + 1 / n0)


def main():
    d = build()
    print(f"games {len(d)}, with a true tip time {d.tip_et_h.notna().sum()}, "
          f"with rest data {d.a_rest.notna().sum()}")
    print(f"sd(total) = {d.total.std():.1f} pts     economic bar = "
          f"{COST_PTS} pts round trip\n")
    print("A. CAN ONE WNBA SEASON EVEN SEE A 0.9-POINT EFFECT?")
    print(f"  {'factor':>10} {'n=1':>6} {'n=0':>6} {'MDE(80%)':>10} "
          f"{'vs 0.9pt bar':>14}")
    for f in ["matinee", "b2b"]:
        s = d.dropna(subset=[f, "total"])
        n1, n0 = int(s[f].sum()), int((1 - s[f]).sum())
        m = mde(s.total.std(), n1, n0)
        print(f"  {f:>10} {n1:>6} {n0:>6} {m:>9.1f}p {m/COST_PTS:>12.0f}x")
    for f in ["rest_diff", "roadtrip"]:
        s = d.dropna(subset=[f, "total"])
        sd_x = s[f].std()
        m = 2.8 * s.total.std() / (np.sqrt(len(s)) * sd_x) if sd_x else np.nan
        print(f"  {f:>10} {'cont':>6} {len(s):>6} {m:>9.2f}p/sd "
              f"{m/COST_PTS:>12.0f}x")
    print("  MDE = smallest effect an 80%-power test could find. A ratio above")
    print("  1x means the season cannot resolve effects that would still pay.\n")

    print("B. DOES THE FACTOR MOVE SCORING, AND DOES THE LINE PRICE IT?")
    panel = pd.read_csv(A.PANEL)
    pre_by = {}
    for e, p in zip(panel.event_ticker, panel.L_pre):
        dt = R.event_date(e)
        if dt:
            pre_by[dt.strftime("%Y%m%d") + e.rsplit("-", 1)[-1][7:]] = p
    d["pre"] = [pre_by.get(k) for k in d.key]
    s = d.dropna(subset=["pre", "total"])
    print(f"  games with a Kalshi pregame line: {len(s)}")
    print(f"  {'factor':>10} {'realized':>20} {'market line':>20} {'gap':>8}")
    for f in ["matinee", "b2b", "rest_diff", "roadtrip"]:
        t = s.dropna(subset=[f])
        if len(t) < 30 or t[f].std() == 0:
            continue
        br, ser = A.ols(t.total.values, [t.pre.values, t[f].values], ["pre", f])
        bm, sem = A.ols(t.pre.values, [t[f].values], [f])
        print(f"  {f:>10} {br[f]:>+11.2f} ({ser[f]:.2f}) "
              f"{bm[f]:>+11.2f} ({sem[f]:.2f}) {br[f]-bm[f]:>+8.2f}")
    print("  realized = effect on the TRUE total, holding the line fixed.")
    print("  market   = how much the LINE already moves with the factor.")
    print("  gap      = the unpriced remainder; must exceed 0.9 pts to trade.")

    print("\nC. REFEREE CREWS")
    print("  No WNBA crew-assignment source exists in this repo (the crew_*")
    print("  machinery is NBA-only). That is an acquisition question, not an")
    print("  analysis one, and it cannot be screened until a feed exists.")


if __name__ == "__main__":
    main()
