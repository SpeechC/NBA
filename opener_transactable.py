"""IS THE OPENER TRANSACTABLE? Part 1 — the PRICE.

Every ROI figure for MOVE_COMBINED assumes -110 at the opener. pre_asb.py
recorded that "real juice is unavailable and -110 is assumed". It is partly
available: OPENING ODDS_H/_R carry `<total><o|u> <juice>` on a large minority
of games (e.g. '232.5o -10', '218.5u -15'), where the two-digit token is the
American price with the leading 1 dropped.

This re-grades the frozen |m| >= 1.0 signal at the ACTUAL opening price where
it is recoverable, against the -110 assumption on the same games.
"""
import math, re, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master

STAKE = 100.0
PAT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([ou])\s*(-\d{2})\s*$")


def payout(american):
    """$ won per $100 staked at a negative American price."""
    return 10000.0 / abs(american)


raw = read_master(verbose=False)
raw["gid"] = raw["GAME-ID"].astype(str).str.strip()
rows = []
for col in ("OPENING ODDS_H", "OPENING ODDS_R"):
    s = raw[col].astype(str)
    m = s.str.extract(PAT)
    ok = m[0].notna()
    rows.append(pd.DataFrame({"gid": raw.gid[ok], "total": pd.to_numeric(m[0][ok]),
                              "side": m[1][ok],
                              "amer": -(100 + m[2][ok].str.lstrip("-").astype(int))}))
q = pd.concat(rows, ignore_index=True)
print(f"parsed opener price on {q.gid.nunique():,} distinct games "
      f"({len(q):,} side-quotes)")
print(f"  price distribution: "
      f"{q.amer.value_counts().head(8).sort_index(ascending=False).to_dict()}")
print(f"  mean {q.amer.mean():.2f}   median {q.amer.median():.0f}   "
      f"share at exactly -110: {100*(q.amer==-110).mean():.1f}%")

# STAGE-0 RANGE GATE
bad = int(((q.amer < -140) | (q.amer > -100)).sum())
print(f"  RANGE gate: {bad} quotes outside [-140,-100]  "
      f"{'PASS' if bad == 0 else 'FAIL'}")

over = q[q.side == "o"].set_index("gid")["amer"]
under = q[q.side == "u"].set_index("gid")["amer"]
over = over[~over.index.duplicated()]; under = under[~under.index.duplicated()]

# ---- the frozen signal ------------------------------------------------------
s = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
s["gid"] = s["GAME-ID"].astype(str).str.strip()
g = pd.read_csv("movement_full_games.csv"); g["gid"] = g.game_id.astype(str).str.strip()
d = s.merge(g[["gid", "actual_total", "open_total"]], on="gid").dropna(
    subset=["MOVE_COMBINED_OOS", "actual_total", "open_total"])
d = d[d.MOVE_COMBINED_OOS.abs() >= 1.0].copy()
d["bet_over"] = d.MOVE_COMBINED_OOS > 0
d["res"] = np.sign(d.MOVE_COMBINED_OOS) * np.sign(d.actual_total - d.open_total)

# price for the side we take; complement when only the other side is quoted
# (books pair totals juice to ~ -220 total, e.g. -115/-105)
def price(r):
    o = over.get(r.gid, np.nan); u = under.get(r.gid, np.nan)
    if r.bet_over:
        if not np.isnan(o): return o, "direct"
        if not np.isnan(u): return -(220 - abs(u)), "complement"
    else:
        if not np.isnan(u): return u, "direct"
        if not np.isnan(o): return -(220 - abs(o)), "complement"
    return np.nan, "none"


pr = d.apply(price, axis=1, result_type="expand")
d["amer"], d["src"] = pr[0], pr[1]
have = d[d.amer.notna() & (d.res != 0)].copy()
print(f"\nfrozen |m|>=1.0 bets: {int((d.res!=0).sum()):,};  "
      f"opener price recoverable on {len(have):,} "
      f"({100*len(have)/max(int((d.res!=0).sum()),1):.0f}%)  "
      f"[{(have.src=='direct').sum():,} direct, {(have.src=='complement').sum():,} complement]")

print(f"\n{'':22}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}")
for lab, use_real in (("assumed -110", False), ("ACTUAL opener price", True)):
    p = have.amer.values if use_real else np.full(len(have), -110.0)
    win = have.res.values > 0
    prof = np.where(win, payout(np.abs(p)) if use_real else 100/1.1, -STAKE)
    if use_real:
        prof = np.where(win, 10000.0/np.abs(p), -STAKE)
    tot = prof.sum(); n = len(have)
    print(f"  {lab:<20}{n:>7,}{100*win.mean():>8.2f}%{tot:>+12,.0f}"
          f"{100*tot/(n*STAKE):>+8.2f}%")
gap = None
p = have.amer.values; win = have.res.values > 0
real = np.where(win, 10000.0/np.abs(p), -STAKE).sum()/(len(have)*STAKE)
assumed = np.where(win, 100/1.1, -STAKE).sum()/(len(have)*STAKE)
print(f"\n  the -110 assumption OVERSTATES ROI by {100*(assumed-real):+.2f}pp "
      f"on the games where the real price is known")
print(f"  mean price actually paid: {have.amer.mean():.2f}  "
      f"(vs -110 assumed)   worse than -110 on "
      f"{100*(have.amer < -110).mean():.0f}% of bets")
