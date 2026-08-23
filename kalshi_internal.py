"""PREREG_kalshi_internal.md -- the SINGLE day-move estimate.

DAY_MOVE = L(last usable bar before tip) - L(first usable bar in the window),
regressed on the carryover-weighted late-OUT treatment frozen in
PREREG_injury_absorption.md s4. Same games as the JUMP measurement.

Run exactly once.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import injury_absorption as IA

NPERM = 5000
RNG = np.random.default_rng(20260823)


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se


def main():
    L = IA.implied_lines()
    E, allg = IA.events()
    import sqlite3
    ct = sqlite3.connect(IA.CURATED, uri=True)
    ev = pd.read_sql("SELECT event_ticker,game_date,home_team,away_team "
                     "FROM events", ct)
    ev["gk"] = ev.game_date + "|" + ev.away_team + "@" + ev.home_team
    tipmap = L.groupby("event_ticker")["tip"].first()

    # DAY_MOVE per game: first usable bar in the window -> last bar before tip
    rows = []
    for et, s in L.groupby("event_ticker"):
        tip = tipmap.get(et, pd.NaT)
        s = s.sort_values("t")
        pre = s[s.t < tip] if pd.notna(tip) else s
        if len(pre) < 2:
            continue
        rows.append({"event_ticker": et, "day_move": pre.L.iloc[-1] - pre.L.iloc[0],
                     "n_bars": len(pre),
                     "span_h": (pre.t.iloc[-1] - pre.t.iloc[0]).total_seconds()/3600})
    D = pd.DataFrame(rows).merge(
        ev[["event_ticker", "gk", "game_date"]], on="event_ticker", how="left")
    wt = E.set_index("gk")["weight"].to_dict()
    D["treatment"] = D.gk.map(wt).fillna(0.0)
    D["treated"] = D.gk.isin(set(E.gk))
    D = D.dropna(subset=["gk"])

    print(f"  games with a usable day-move: {len(D):,}")
    print(f"    median bars {D.n_bars.median():.0f}   median span "
          f"{D.span_h.median():.1f}h")
    print(f"    treated {int(D.treated.sum()):,}   control "
          f"{int((~D.treated).sum()):,}")
    print(f"    mean DAY_MOVE overall {D.day_move.mean():+.3f}")

    print("\n" + "=" * 84)
    print("THE SINGLE TEST:  DAY_MOVE ~ treatment")
    print("=" * 84)
    y = D.day_move.values
    b, t = ols(y, [D.treatment.values])
    print(f"  b(treatment) {b[1]:+.4f}  (t={t[1]:+.2f})   n={len(D):,}")

    a = D[D.treated].day_move
    c = D[~D.treated].day_move
    diff = a.mean() - c.mean()
    se = np.sqrt(a.var()/len(a) + c.var()/len(c))
    print(f"  treated mean {a.mean():+.3f} (n={len(a):,})   "
          f"control mean {c.mean():+.3f} (n={len(c):,})")
    print(f"  treated - control {diff:+.3f}  (t={diff/se if se else np.nan:+.2f})")

    # within-date block permutation of the treatment
    dates = D.game_date.values
    blocks = [np.where(dates == u)[0] for u in np.unique(dates)]
    v = D.treatment.values
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for bl in blocks:
            p[bl] = v[bl][RNG.permutation(len(bl))]
        bb, _ = ols(y, [p])
        null[i] = bb[1]
    pv = (1 + np.sum(np.abs(null) >= abs(b[1]))) / (NPERM + 1)
    print(f"  within-date permutation: observed {b[1]:+.4f}  "
          f"null {null.mean():+.4f} sd {null.std():.4f}   p={pv:.4f}")

    print("\n" + "=" * 84)
    print("VERDICT vs prereg s5")
    print("=" * 84)
    ok = (b[1] < 0) and (abs(t[1]) >= 2) and (pv < 0.05) and (diff < 0)
    print(f"  b<0 {b[1]<0}   |t|>=2 {abs(t[1])>=2}   perm p<0.05 {pv<0.05}   "
          f"treated-control<0 {diff<0}")
    print(f"  -> {'ESTABLISHED WITHIN-SAMPLE' if ok else 'NOT ESTABLISHED'}")
    print(f"  [JUMP, already measured on these games: +0.045 (t=+0.29)]")
    D.to_csv("kalshi_internal_rows.csv", index=False)


if __name__ == "__main__":
    main()
