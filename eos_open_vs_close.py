"""When does the market price the late-season Over regime? Opener vs close.

The anomaly is established. This asks WHERE in price discovery it lives, which
is an execution question, not another search. The window is FIXED at the final
7 days -- no re-optimisation.

    R_open  = actual - opening_total
    R_close = actual - closing_total
    Move    = closing_total - opening_total

and the identity that attributes the opening-line error:

    (actual - open) = (actual - close) + (close - open)
     opening error  =  remaining error  + market correction

Three readings, all different:

  over@open >> over@close, with Move > 0
      the market partially learns it intraday -> bet earlier
  over@open ~= over@close, with Move ~= 0
      the market does not adjust for the regime at all
  over@close > over@open
      intraday information moves totals in a direction that IMPROVES the over

Then buckets by Move, looking at CLOSING-line performance inside each. If games
that moved sharply UP still go over, the market sees the pressure, adjusts, and
still under-adjusts. If only the flat/down games retain the edge, market
behaviour itself is a game-level selector -- which would be a genuinely new
information source, given that every feature-based ranking model failed.

Pushes are handled separately at each price: the opening and closing numbers
differ, so a game can push at one and not the other. Win rates exclude pushes.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

WINDOW = 7
BE = 110 / 210


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300) & d["open"].between(150, 300)]
    d["r_open"] = d["actual"] - d["open"]
    d["r_close"] = d["actual"] - d["close"]
    d["move"] = d["close"] - d["open"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d["late"] = d["days_left"] <= WINDOW
    return d.reset_index(drop=True)


def stats_at(s, col):
    n = len(s)
    push = (s[col] == 0).sum()
    live = s[s[col] != 0]
    ov = (live[col] > 0).mean()
    se = np.sqrt(ov * (1 - ov) / len(live))
    roi = ov * (100 / 110) - (1 - ov)
    return {"n": n, "push": push, "push %": round(100 * push / n, 2),
            "mean": round(s[col].mean(), 3),
            "median": round(s[col].median(), 2),
            "over %": round(100 * ov, 2),
            "95% CI": f"[{100*(ov-1.96*se):.2f}, {100*(ov+1.96*se):.2f}]",
            "ROI110": round(100 * roi, 2)}


def main():
    d = load()
    late, rest = d[d["late"]], d[~d["late"]]
    print(f"{len(d):,} games with both an opening and closing total")
    print(f"  final {WINDOW} days: {len(late):,}   rest: {len(rest):,}\n")

    print("=" * 104)
    print(f"OPENER vs CLOSE — same games, final {WINDOW} days")
    print("=" * 104)
    rows = [{"price": "OPENING total", **stats_at(late, "r_open")},
            {"price": "CLOSING total", **stats_at(late, "r_close")}]
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  break-even {100*BE:.2f}%")

    print("\n  same table, rest of season (control):")
    rows = [{"price": "OPENING total", **stats_at(rest, "r_open")},
            {"price": "CLOSING total", **stats_at(rest, "r_close")}]
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 104)
    print("LINE MOVEMENT — does the market move late-season totals up?")
    print("=" * 104)
    for lab, s in (("final 7 days", late), ("rest of season", rest)):
        m = s["move"]
        se = m.std() / np.sqrt(len(m))
        print(f"  {lab:16} n={len(s):5,}  E[close-open] {m.mean():+.3f} "
              f"± {1.96*se:.3f}   median {m.median():+.2f}   "
              f"up {100*(m>0).mean():4.1f}%  flat {100*(m==0).mean():4.1f}%  "
              f"down {100*(m<0).mean():4.1f}%")
    diff = late["move"].mean() - rest["move"].mean()
    print(f"\n  late minus rest: {diff:+.3f} points of extra upward movement")

    print("\n" + "=" * 104)
    print("ATTRIBUTION — where the opening error goes")
    print("=" * 104)
    for lab, s in (("final 7 days", late), ("rest of season", rest)):
        ao, ac, co = s["r_open"].mean(), s["r_close"].mean(), s["move"].mean()
        share = 100 * co / ao if ao else np.nan
        print(f"  {lab}:")
        print(f"    opening error (actual-open)   {ao:+.3f}")
        print(f"    market correction (close-open) {co:+.3f}   "
              f"= {share:.1f}% of the opening error")
        print(f"    remaining error (actual-close) {ac:+.3f}   "
              f"= {100-share:.1f}% left at the close")

    print("\n" + "=" * 104)
    print("MOVEMENT BUCKETS — closing-line over performance inside each")
    print("=" * 104)
    late = late.copy()
    late["bucket"] = pd.cut(late["move"], [-99, -0.51, 0.49, 1.51, 99],
                            labels=["moved DOWN", "flat (0)", "+0.5 to +1.5",
                                    "+2 or more"])
    rows = []
    for b, s in late.groupby("bucket", observed=True):
        if len(s) < 30:
            continue
        r = {"move bucket": b, "mean move": round(s["move"].mean(), 2)}
        r.update({f"close {k}": v for k, v in stats_at(s, "r_close").items()
                  if k in ("n", "over %", "95% CI", "ROI110")})
        r["open over %"] = stats_at(s, "r_open")["over %"]
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  If the '+2 or more' bucket still goes over at a high rate, the")
    print("  market sees the pressure, adjusts, and still under-adjusts.")

    print("\n--- by season, over% at OPEN vs CLOSE (final 7 days) ---")
    r = []
    for s in sorted(late["season"].unique()):
        x = late[late["season"] == s]
        r.append({"season": s[4:13], "n": len(x),
                  "open over %": stats_at(x, "r_open")["over %"],
                  "close over %": stats_at(x, "r_close")["over %"],
                  "mean move": round(x["move"].mean(), 2)})
    print(pd.DataFrame(r).to_string(index=False))


if __name__ == "__main__":
    main()
