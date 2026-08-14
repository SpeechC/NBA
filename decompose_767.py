"""Accounting check on the +0.767 allocation error.

    AllocationError = (actualH2 - actualH1) - (FGline - 2*H1line)
                    = (actualFG - FGline) - 2*(actualH1 - H1line)
                    =  FGresidual          - 2*H1residual

So the +0.767 can be full-game totals running low, H1 totals running high, or a
mix. Reporting the three means side by side settles which, and the identity is
verified numerically rather than assumed.

Interpretation:
    FG +0.8, H1 ~0    -> the sample simply had low full-game totals; there is no
                         half-allocation anomaly at all
    FG ~0,  H1 -0.38  -> DK's H1 total really is high by ~0.4 points
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def main():
    from team_market_error import build
    j, _ = build()

    j["fg_resid"] = j["actual_full"] - j["full_game_total_close"]
    j["h1_resid"] = j["actual_h1"] - j["h1_total_close"]
    j["alloc_chk"] = j["fg_resid"] - 2 * j["h1_resid"]

    print("\n" + "=" * 92)
    print("THE THREE MEANS")
    print("=" * 92)
    rows = []
    for c, lab in (("fg_resid", "FG residual   (actual - FG line)"),
                   ("h1_resid", "H1 residual   (actual - H1 line)"),
                   ("E", "allocation error (measured)"),
                   ("alloc_chk", "allocation error (identity)")):
        s = j[c]
        se = s.std() / np.sqrt(len(s))
        rows.append({"quantity": lab, "n": len(s), "mean": round(s.mean(), 4),
                     "se": round(se, 4), "t": round(s.mean() / se, 2),
                     "median": round(s.median(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    lhs, rhs = j["E"].mean(), j["fg_resid"].mean() - 2 * j["h1_resid"].mean()
    print(f"\n  identity: {lhs:+.4f}  vs  FG - 2*H1 = "
          f"{j['fg_resid'].mean():+.4f} - 2*({j['h1_resid'].mean():+.4f}) "
          f"= {rhs:+.4f}   max abs game-level gap "
          f"{(j['E']-j['alloc_chk']).abs().max():.2e}")

    fg, h1 = j["fg_resid"].mean(), j["h1_resid"].mean()
    print(f"\n  contribution to the {lhs:+.3f}:")
    print(f"    from FG totals running low : {fg:+.3f}  "
          f"({100*fg/lhs:5.1f}%)")
    print(f"    from H1 totals running high: {-2*h1:+.3f}  "
          f"({100*(-2*h1)/lhs:5.1f}%)")

    print("\n" + "=" * 92)
    print("SIDE BY SIDE — over rates, to see whether either is payoff-relevant")
    print("=" * 92)
    for c, lab in (("fg_resid", "full-game total"), ("h1_resid", "H1 total")):
        live = j[j[c] != 0]
        ov = (live[c] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(live))
        print(f"  {lab:16} over {100*ov:5.2f}%  95% CI "
              f"[{100*(ov-1.96*se):.2f}, {100*(ov+1.96*se):.2f}]  "
              f"(break-even ~52.4%)  mean {j[c].mean():+.3f}  "
              f"median {j[c].median():+.2f}")

    print("\n--- by month ---")
    j["m"] = j["date"].dt.to_period("M")
    t = j.groupby("m").agg(n=("E", "size"), FG=("fg_resid", "mean"),
                           H1=("h1_resid", "mean"), E=("E", "mean")).round(2)
    print(t.to_string())


if __name__ == "__main__":
    main()
