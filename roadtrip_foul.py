"""ROAD-TRIP FATIGUE x LEAGUE FOUL ENVIRONMENT — executes PREREG_roadtrip_foul.md."""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side
from rest_travel import add_rest_travel

NPERM = 5000
RNG = np.random.default_rng(42)
TRIP_MIN, FOUL_Q = 2, 0.80          # FROZEN in the prereg


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; n, k = X.shape
    se = np.sqrt(np.diag((r @ r / (n - k)) * np.linalg.pinv(X.T @ X)))
    return b, b / se, int(n)


def build():
    raw = read_master(verbose=False)
    raw["season"] = season_label(raw).astype(str)
    raw = raw[raw.season.str.contains("Regular Season", na=False)].copy()
    panel = pd.concat([_side(raw, "H"), _side(raw, "R")], ignore_index=True)
    p = add_rest_travel(panel, raw)
    away = p[p.home == 0].copy(); away["gid"] = away.game_id.astype(str).str.strip()

    gid = raw["GAME-ID"].astype(str).str.strip()
    hp = _side(raw, "H")["Y"].values.astype(float)
    ap = _side(raw, "R")["Y"].values.astype(float)
    m = pd.DataFrame({"gid": gid.values, "season": raw.season.values,
                      "date": pd.to_datetime(raw["DATE"], errors="coerce").values,
                      "close": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce").values,
                      "home_pts": hp, "away_pts": ap,
                      "home_fta": pd.to_numeric(raw.get("TEAM_FTA_H"), errors="coerce").values})
    rf = pd.read_csv("ref_features.csv"); rf["gid"] = rf.gid.astype(str).str.strip()
    d = m.merge(rf[["gid", "LeagueFoulState", "yr"]], on="gid").merge(
        away[["gid", "road_trip_game"]], on="gid")
    d = d.dropna(subset=["LeagueFoulState", "close", "home_pts", "away_pts"])
    d = d[d.close.between(150, 300)]
    d["dev"] = d.home_pts + d.away_pts - d.close
    q = d.LeagueFoulState.quantile(FOUL_Q)
    d["hifoul"] = (d.LeagueFoulState >= q).astype(float)
    d["trip2"] = (d.road_trip_game >= TRIP_MIN).astype(float)
    d["inter"] = d.trip2 * d.hifoul
    d = d.sort_values("date").reset_index(drop=True)
    d["block"] = (d.hifoul != d.hifoul.shift()).cumsum()   # contiguous regimes
    for s in sorted(d.season.unique())[:-1]:
        d[f"S_{s[:8]}"] = (d.season == s).astype(float)
    if len(d) < 6000:
        raise RuntimeError(f"JOIN FAILURE: {len(d)} rows")
    return d, q


def block_perm(d, key, ctl, one_sided=True):
    """Permute the control-residualised target across CONTIGUOUS foul blocks."""
    Z = np.column_stack([np.ones(len(d))] + [d[c].values for c in ctl])
    bz, *_ = np.linalg.lstsq(Z, d.dev.values, rcond=None)
    resid = d.dev.values - Z @ bz
    b, t, n = ols_t(d.dev.values, [d[key].values] + [d[c].values for c in ctl])
    obs = b[1]
    blocks = [np.where(d.block.values == u)[0] for u in d.block.unique()]
    null = np.empty(NPERM)
    for i in range(NPERM):
        order = RNG.permutation(len(blocks))
        r = np.concatenate([resid[blocks[j]] for j in order])
        r = r[:len(resid)] if len(r) >= len(resid) else np.pad(r, (0, len(resid)-len(r)))
        bb, _, _ = ols_t(Z @ bz + r, [d[key].values] + [d[c].values for c in ctl])
        null[i] = bb[1]
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"    {key:14} beta {obs:+.4f} (naive t={t[1]:+.2f})  block-null sd "
          f"{null.std():.4f}  {'p1='+format(p1,'.4f') if one_sided else 'p2='+format(p2,'.4f')}")
    return obs, null.std()


d, q = build()
S = [c for c in d.columns if c.startswith("S_")]
print(f"built {len(d):,} games   foul cutoff {q:+.4f}   "
      f"gate cell {int(d.inter.sum()):,}   blocks {d.block.nunique()}")

print("\n=== P3 POSITIVE CONTROL — does a deep road trip degrade the visitor's D? ===")
for tgt, lab in (("home_pts", "home points"), ("home_fta", "home FTA")):
    x = d.dropna(subset=[tgt])
    b, t, n = ols_t(x[tgt].values, [x.road_trip_game.values, x.close.values]
                    + [x[c].values for c in S])
    print(f"    {lab:12} ~ road_trip_game   beta {b[1]:+.4f} (t={t[1]:+.2f})  n={n:,}"
          f"   {'PASS' if t[1] > 1.96 else 'FAIL (predicted > 0)'}")

print("\n=== P1 PRIMARY — the interaction (predicted > 0) ===")
CTRL = ["trip2", "hifoul", "close"] + S
obs, nsd = block_perm(d, "inter", CTRL)

print("\n=== P2 SECONDARY — gate cell vs matched controls (same season, close +/-3) ===")
g = d[d.inter == 1]; ctrls = d[d.inter == 0]
diffs = []
for _, r in g.iterrows():
    c = ctrls[(ctrls.season == r.season) & (ctrls.close.sub(r.close).abs() <= 3)]
    if len(c) >= 10:
        diffs.append(r.dev - c.dev.mean())
diffs = np.array(diffs)
print(f"    matched pairs {len(diffs):,}   mean diff {diffs.mean():+.4f} pts")

print("\n=== SEASON-BY-SEASON (a pooled figure here is largely about 2021) ===")
print(f"    {'season':<8}{'gate n':>8}{'mean dev|gate':>15}{'mean dev|rest':>15}{'diff':>9}")
for yr, x in d.groupby("yr"):
    gg = x[x.inter == 1]
    if len(gg) < 20: continue
    print(f"    {yr:<8}{len(gg):>8,}{gg.dev.mean():>+15.3f}"
          f"{x[x.inter==0].dev.mean():>+15.3f}{gg.dev.mean()-x[x.inter==0].dev.mean():>+9.3f}")

print("\n=== DETECTION BURDEN (block se, not game-level) ===")
sd = float(d.dev.std()); dens = 0.3989 / sd
print(f"    block-null sd of beta {nsd:.4f}   MDE(95%) {1.96*nsd:.4f} pts")
print(f"    observed {obs:+.4f} pts -> {100*abs(obs)*dens:.2f}pp   "
      f"(sd dev {sd:.2f}, density {100*dens:.2f}pp/pt)")
