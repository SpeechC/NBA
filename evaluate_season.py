"""Season-level evaluation of the 2026-27 prospective log. RUN ONCE.

Implements Amendment 6: every wager settles against `open_total`, the line it was
struck at. Never `close_total`.

D3 of the prereg forbids interim looks at wagering performance, so this module is
DELIBERATELY SEPARATE from the daily pipeline. Nothing in capture/settle/health
imports it, and it refuses to run before EVAL_NOT_BEFORE without an explicit,
logged override. Importing it does not compute anything.
"""
import os, csv, sys, datetime as dt
import numpy as np

LOG = os.path.expanduser("~/data/nba_2026_27_prospective_log.csv")
EVAL_NOT_BEFORE = "2027-04-15"     # after the 2026-27 regular season ends
BREAK_EVEN = 1.0 / 1.90909090909   # -110


def grade(row):
    """+1 win, 0 push, -1 loss, None if not gradeable.

    AMENDMENT 6 -- settles against OPEN_TOTAL, the line the wager was struck at.

    Settling against close_total would silently convert this from a wager result
    into a CLV measurement. Those two can point opposite ways: injury Hypothesis B
    scored CLV +0.775 pts (t=+7.93) while its P&L was -8.04%. Consistent with
    frozen items 5 (`Actual == Open` is a PUSH) and 7 (`Actual - Open`).
    """
    if not row.get("actual_total") or not row.get("open_total"):
        return None
    side = int(row["side"])
    if side == 0:
        return None
    diff = float(row["actual_total"]) - float(row["open_total"])
    if diff == 0:
        return 0                      # push: out of the hit-rate denominator
    return 1 if side * diff > 0 else -1


def evaluate(log=LOG, threshold_field="bet_flag", allow_early=False):
    """The six C2 metrics. Returns a dict; prints nothing on its own."""
    today = dt.date.today().isoformat()
    if today < EVAL_NOT_BEFORE and not allow_early:
        raise RuntimeError(
            f"D3 forbids interim looks at wagering performance. Today {today} < "
            f"{EVAL_NOT_BEFORE}. Pass allow_early=True only for a plumbing test on "
            f"NON-2026-27 data, and record that you did.")
    with open(log) as f:
        rows = list(csv.DictReader(f))

    eligible = [r for r in rows if grade(r) is not None]
    sel = [r for r in eligible if int(r[threshold_field]) == 1]
    graded = [grade(r) for r in sel]
    bets = [g for g in graded if g != 0]
    pushes = len(graded) - len(bets)
    n = len(bets)
    if n == 0:
        return {"N_eligible": len(eligible), "N_bets": 0, "pushes": pushes}

    wins = sum(1 for g in bets if g > 0)
    hit = wins / n
    roi = 1.90909090909 * hit - 1
    se = np.sqrt(hit * (1 - hit) / n)
    # $100 flat -- the prereg's reporting unit, not a funded position.
    profit = n * 100.0 * roi
    return {
        "N_eligible": len(eligible), "N_bets": n, "pushes": pushes,
        "HitRate": hit, "se_hit": se, "BreakEven": BREAK_EVEN,
        "z_vs_BE": (hit - BREAK_EVEN) / se,
        "ROI": roi, "ProfitPerBet": 100.0 * roi,
        "TotalPL": profit,
        "ProfitPerAllEligibleGames": profit / len(eligible),
    }


if __name__ == "__main__":
    early = "--allow-early" in sys.argv
    r = evaluate(allow_early=early)
    for k, v in r.items():
        print(f"  {k:<28}{v:.4f}" if isinstance(v, float) else f"  {k:<28}{v}")
