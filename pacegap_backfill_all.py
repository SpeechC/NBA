"""Reconstruct PaceGap's 2025-26 signals by running the frozen engine walk-forward.

PaceGap was the one strategy that could not be replayed on Kalshi books: its
signal is E_pace from frozen_models and no per-game historical export exists
(verified -- no CSV in the repo carries an E_pace column and pace_signal.py
writes none). This rebuilds it.

EXACTLY the live path, which is capture_openers.py:
    g  = FM.load_history()
    st = FM.build_states(g, day)        # strictly < day, so point-in-time safe
    pr = FM.team_profiles(g, day)
    q  = FM.predict_game(st, pr, team_h, team_r, open_total, open_spread)
and then prospective_log.log_game's arithmetic:
    D       = P_hat - P_book
    E_pace  = D * EffSum / 100
    bet_flag= |E_pace| >= 4.77          (THRESHOLD, frozen)
    side    = +1 if E_pace > 0 else -1  (+1 = OVER)

`m_X` and `mu5` are computed but do NOT enter bet_flag, so the transition-state
staleness check that the live path performs is irrelevant here.

WRITES TO ITS OWN FILE. It does NOT call prospective_log.log_game, which appends
to the immutable 2026-27 prospective log and refuses duplicates. Nothing frozen
is touched: frozen_models.py and prospective_log.py are read-only here, and
verify_frozen.py should still pass afterwards.

States are rebuilt once per GAME DATE (8.5s each, ~170 dates), not per game.
"""
import sys, os, time, csv
import numpy as np, pandas as pd
sys.path.insert(0, '.')
import frozen_models as FM
import prospective_log as PL
from prepare_data import read_master, season_label

OUT = "pacegap_backfill_all.csv"
SEASON = None    # all seasons
COLS = ['season', 'game_date', 'TEAM_H', 'TEAM_R', 'open_total', 'open_spread', 'close_total',
        'actual_total', 'P_hat', 'P_book', 'D', 'EffSum', 'E_pace', 'bet_flag',
        'side', 'n_prior_games', 'ab_a', 'ab_b']

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['open_total'] = pd.to_numeric(d['OPENING TOTAL_H'], errors='coerce')
d['open_spread'] = pd.to_numeric(d['OPENING SPREAD_H'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
S = (d if SEASON is None else d[d.season == SEASON]).dropna(subset=['open_total', 'open_spread', 'actual']).copy()
days = sorted(S.ds.unique())
print(f"seasons {sorted(S.season.unique())}: {len(S)} games, {len(days)} dates",
      flush=True)
print(f"THRESHOLD {PL.THRESHOLD}  MODEL_VERSION {PL.MODEL_VERSION}", flush=True)

g = FM.load_history()
print(f"history rows {len(g)}", flush=True)

rows, n_skip_day, n_skip_game = [], 0, 0
t0 = time.time()
for i, day in enumerate(days, 1):
    try:
        st = FM.build_states(g, day)
        pr = FM.team_profiles(g, day)
    except Exception as e:
        print(f"  SKIP DAY {day}: {type(e).__name__}: {e}", flush=True)
        n_skip_day += 1
        continue
    if st.get('ab') is None:
        print(f"  SKIP DAY {day}: no a,b fit (needs >=400 prior-season games)",
              flush=True)
        n_skip_day += 1
        continue
    a_, b_ = st['ab']
    for r in S[S.ds == day].itertuples():
        try:
            q = FM.predict_game(st, pr, r.h, r.r, float(r.open_total),
                                float(r.open_spread))
        except KeyError:
            n_skip_game += 1
            continue
        if not np.isfinite(q['P_book']) or not np.isfinite(q['P_hat']):
            n_skip_game += 1
            continue
        D = q['P_hat'] - q['P_book']
        E = D * q['EffSum'] / 100.0
        rows.append(dict(season=int(r.season), game_date=day, TEAM_H=r.h, TEAM_R=r.r,
                         open_total=r.open_total, open_spread=r.open_spread,
                         close_total=r.close, actual_total=r.actual,
                         P_hat=round(q['P_hat'], 4), P_book=round(q['P_book'], 4),
                         D=round(D, 4), EffSum=round(q['EffSum'], 4),
                         E_pace=round(E, 4),
                         bet_flag=int(abs(E) >= PL.THRESHOLD),
                         side=(1 if E > 0 else (-1 if E < 0 else 0)),
                         n_prior_games=st['n_games'],
                         ab_a=round(a_, 4), ab_b=round(b_, 4)))
    if i % 20 == 0 or i == len(days):
        el = time.time() - t0
        print(f"  [{i}/{len(days)}] {day}  rows {len(rows)}  "
              f"{el:.0f}s elapsed, ~{el/i*(len(days)-i):.0f}s left", flush=True)

R = pd.DataFrame(rows)
R.to_csv(OUT, index=False, columns=COLS)
print(f"\nwrote {len(R)} rows -> {OUT}", flush=True)
print(f"  days skipped {n_skip_day}  games skipped {n_skip_game}", flush=True)
if len(R):
    b = R[R.bet_flag == 1]
    print(f"\n  E_pace: mean {R.E_pace.mean():+.3f}  sd {R.E_pace.std():.3f}  "
          f"|E|>=4.77 on {len(b)} of {len(R)} ({100*len(b)/len(R):.1f}% of slate)")
    print(f"  of those: OVER {int((b.side==1).sum())}  UNDER {int((b.side==-1).sum())}")
    # sportsbook grade vs the OPENER, which is what PaceGap settles against
    won = np.where(b.side == 1, b.actual_total > b.open_total,
                   b.actual_total < b.open_total)
    push = b.actual_total == b.open_total
    wn = won[~push]
    print(f"  hit rate vs the OPENER: {100*wn.mean():.2f}% on {len(wn)} graded "
          f"({int(push.sum())} pushes)")
    print(f"  PREREG reference: 30.3% of slate, hit 53.31% in discovery; "
          f"pooled 2023-25 52.59%")
