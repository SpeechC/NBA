"""QUOTE-PATH STRUCTURE CHECKS — run BEFORE the prereg is finalised.

Market columns only. No score, no actual total, no dev. Nothing here can
reveal an outcome; these checks establish whether the path is parseable,
era-stable and in range, which the prereg needs to state its gates.
"""
import re
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, MARKET_GATES

LM = [f"LINE \nMOVEMENT #{i}" for i in (1, 2, 3)]
NUM = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")


def lead(s):
    """First signed decimal token: '-4.5 -09'->-4.5, ' 215.5o15'->215.5."""
    m = NUM.match(str(s))
    return float(m.group(1)) if m else np.nan


def classify(v, kind):
    """Magnitude recovery (DATA_DICTIONARY sec.1). 30<|v|<=60 is ambiguous."""
    a = np.abs(v)
    if kind == "spread":
        return np.where(a <= 30, v, np.nan)
    return np.where((a > 60) & (a >= 150) & (a <= 300), v, np.nan)


raw = read_master(verbose=False)
raw["season"] = season_label(raw)
reg = raw["season"].astype(str).str.contains("Regular Season|In-Season", na=False)
raw = raw[reg].copy()
print(f"regular-season rows: {len(raw):,}")

out = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip(),
                    "season": raw["season"].astype(str)})

# endpoints come from the ALREADY-GATED columns
out["sp_open"] = pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce")
out["sp_close"] = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
out["to_open"] = pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce")
out["to_close"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")

# intermediate quotes: try both sides, keep whichever magnitude-classifies
for i, c in enumerate(LM, start=1):
    h = raw[f"{c}_H"].map(lead).values
    r = raw[f"{c}_R"].map(lead).values
    sp_h, sp_r = classify(h, "spread"), classify(r, "spread")
    to_h, to_r = classify(h, "total"), classify(r, "total")
    # _R carries the AWAY side of the spread: OPENING SPREAD_H -4.0 <-> _R +4.0.
    # Negate before falling back to it, or the path lands on the wrong team.
    out[f"sp_q{i}"] = np.where(~np.isnan(sp_h), sp_h, -sp_r)
    out[f"to_q{i}"] = np.where(~np.isnan(to_h), to_h, to_r)

print("\n=== GATE 1 CONTENT — are these repricings of the same market? ===")
print("  mean |quote - close|, must fall monotonically open->q3")
for kind, o, c in (("spread", "sp_open", "sp_close"), ("total", "to_open", "to_close")):
    d = [np.nanmean(np.abs(out[o] - out[c]))]
    d += [np.nanmean(np.abs(out[f"{kind[:2]}_q{i}"] - out[c])) for i in (1, 2, 3)]
    corr = [out[o].corr(out[c])] + [out[f"{kind[:2]}_q{i}"].corr(out[c]) for i in (1, 2, 3)]
    print(f"  {kind:7} dist  open {d[0]:.2f} -> q1 {d[1]:.2f} -> q2 {d[2]:.2f} -> q3 {d[3]:.2f}"
          f"   monotone={'YES' if d[0] > d[1] >= d[2] >= d[3] else 'NO'}")
    print(f"  {kind:7} corr  open {corr[0]:.3f} -> q1 {corr[1]:.3f} -> q2 {corr[2]:.3f} -> q3 {corr[3]:.3f}")

print("\n=== GATE 2 RANGE — parsed quotes inside physical bounds ===")
for kind, lo, hi in (("sp", -30, 30), ("to", 150, 300)):
    for i in (1, 2, 3):
        v = out[f"{kind}_q{i}"].dropna()
        bad = int(((v < lo) | (v > hi)).sum())
        print(f"  {kind}_q{i}: n={len(v):6,}  outside[{lo},{hi}]={bad}"
              f"  min {v.min():8.1f}  max {v.max():8.1f}")

print("\n=== GATE 3 ERA STABILITY — quote coverage by season ===")
print(f"  {'season':<26}{'games':>7}{'sp_q1':>8}{'sp_q3':>8}{'to_q1':>8}{'to_q3':>8}")
cov = []
for s, g in out.groupby("season"):
    row = [g[f"{k}_q{i}"].notna().mean() for k, i in
           (("sp", 1), ("sp", 3), ("to", 1), ("to", 3))]
    cov.append((s, len(g), *row))
    print(f"  {s[:26]:<26}{len(g):>7,}" + "".join(f"{x:>8.3f}" for x in row))
c = np.array([r[2:] for r in cov])
print("  max/min coverage ratio per column:",
      "  ".join(f"{n}={c[:, j].max()/max(c[:, j].min(), 1e-9):.2f}x"
               for j, n in enumerate(["sp_q1", "sp_q3", "to_q1", "to_q3"])))

print("\n=== STRUCTURE — how many DISTINCT quotes per game? ===")
for kind in ("sp", "to"):
    q = out[[f"{kind}_q{i}" for i in (1, 2, 3)]]
    npres = q.notna().sum(axis=1)
    ndist = q.apply(lambda r: r.dropna().nunique(), axis=1)
    print(f"  {kind}: quotes present  " +
          "  ".join(f"{k}:{int((npres == k).sum()):,}" for k in (0, 1, 2, 3)))
    print(f"  {kind}: DISTINCT values " +
          "  ".join(f"{k}:{int((ndist == k).sum()):,}" for k in (0, 1, 2, 3)))

print("\n=== STRUCTURE — is q3 just a copy of the close? ===")
for kind, c in (("sp", "sp_close"), ("to", "to_close")):
    for i in (1, 2, 3):
        eq = (out[f"{kind}_q{i}"] == out[c])
        n = out[[f"{kind}_q{i}", c]].dropna().shape[0]
        print(f"  {kind}_q{i} == close on {eq.sum():,}/{n:,} ({100*eq.sum()/max(n,1):.1f}%)")

out.to_csv("quote_path_raw.csv", index=False)
print(f"\nwrote quote_path_raw.csv  ({len(out):,} rows)")
