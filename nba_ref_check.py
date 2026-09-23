"""Reconcile official.nba.com assignment names against our boxscore history.

    python nba_ref_check.py                      # today
    python nba_ref_check.py --days 14            # next 14 days
    python nba_ref_check.py --from 2026-10-20 --to 2026-11-05
    python nba_ref_check.py --roster             # every official in history

Exit 0 = every assignment name resolves. Exit 1 = at least one does not.

=============================================================================
WHY THIS EXISTS SEPARATELY FROM crewshock_live
=============================================================================
`resolve_officials()` already flags unmatched names and refuses to action those
games (`DATA_GAP`). That is the right runtime behaviour and it is REACTIVE: you
learn about the mismatch at 17:00 on game day, when the only available response
is to skip the game.

This is the PROACTIVE version. Point it at the assignment feed as soon as it
goes live and it tells you, before opening night, which names the history
cannot resolve -- while there is still time to reconcile them.

=============================================================================
THE FAILURE THIS CATCHES IS SILENT AND HAS HAPPENED
=============================================================================
official.nba.com writes `JT Orr`; BigDataBall writes `J.T. Orr`. Unmatched,
that official contributes 0 to the crew sum, which biases CrewShock toward zero
and can flip the call either way. It mis-scored a real slate by up to 6.8e-02
before canonical matching was added.

`_canon` already strips punctuation, case and whitespace, so `JT Orr` resolves
today. What it does NOT resolve is a genuinely different string: a new official
with no history, a name change, a nickname, an added middle initial. Those are
what this reports -- with the closest history names beside them, so the
judgement is a human one rather than a silent zero.

IMPORTANT: this imports `_canon`, `load_history` and `fetch_assignments` FROM
crewshock_live. It tests the matching logic that actually runs. A
reimplementation here could agree with itself and still disagree with the
estimator, which is the only thing that matters.
"""
import os, sys, argparse, difflib, datetime as dt
import pandas as pd

ROOT = os.environ.get("NBA_PROJECT_DIR", "/home/dpope/projects/nba_entropy_replication")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from crewshock_live import _canon, load_history, fetch_assignments, HIST, CURRENT


def history_names():
    """canonical key -> the spelling the history uses. Built from the SAME
    load_history() the estimator uses, so the key set is identical."""
    paths = tuple(p for p in (HIST, CURRENT) if os.path.exists(p))
    h = load_history(paths)
    key2name, counts = {}, {}
    for c in ("ref1", "ref2", "ref3"):
        for k, v in zip(_canon(h[c]), h[c]):
            if isinstance(k, str):
                key2name.setdefault(k, v)
                counts[k] = counts.get(k, 0) + 1
    return key2name, counts, h


def check(days=0, dfrom=None, dto=None, roster=False, quiet=False):
    key2name, counts, h = history_names()
    print(f"history: {len(h):,} completed games, {len(key2name)} distinct officials")
    print(f"  sources: {[os.path.basename(p) for p in (HIST, CURRENT) if os.path.exists(p)]}")
    if not os.path.exists(CURRENT):
        print(f"  note: {os.path.basename(CURRENT)} absent -- history is the frozen file only,")
        print(f"        which is correct before the season's first games are played.")

    if roster:
        print(f"\n{'official':<28}{'games in history':>18}")
        for k, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {key2name[k]:<26}{n:>18,}")
        return 0

    if dfrom:
        d0 = dt.date.fromisoformat(dfrom)
        d1 = dt.date.fromisoformat(dto) if dto else d0
    else:
        d0 = dt.date.today()
        d1 = d0 + dt.timedelta(days=max(0, days))
    dates = [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]

    slates, empty = [], []
    for d in dates:
        try:
            s = fetch_assignments(d)
        except Exception as e:
            print(f"  {d}: fetch failed {type(e).__name__}: {e}")
            continue
        (slates.append(s) if len(s) else empty.append(d))
    if not slates:
        print(f"\nno assignments published for {dates[0]}..{dates[-1]}")
        print("  A zero-row response is returned for a bad date format as readily as")
        print("  for an empty slate. Before the season this is expected; during it,")
        print("  confirm the date format is YYYY-MM-DD before believing 'no games'.")
        return 0
    S = pd.concat(slates, ignore_index=True)
    print(f"\nassignments: {len(S)} games over {len(dates)} date(s)"
          f"  ({len(empty)} date(s) with none)")

    seen, unresolved = {}, {}
    for c in ("ref1", "ref2", "ref3"):
        for nm, k in zip(S[c], _canon(S[c])):
            if not isinstance(k, str):
                continue
            seen[k] = nm
            if k not in key2name:
                unresolved[k] = nm
    ok = len(seen) - len(unresolved)
    print(f"distinct officials assigned: {len(seen)}   resolved {ok}   UNRESOLVED {len(unresolved)}")

    if not quiet and ok:
        ex = [(seen[k], key2name[k]) for k in seen if k in key2name and seen[k] != key2name[k]]
        if ex:
            print(f"\nresolved only BECAUSE of canonicalisation ({len(ex)}) -- these are the"
                  f"\n  JT Orr / J.T. Orr class, matched on punctuation+case:")
            for a, b in ex[:12]:
                print(f"    assignment {a!r}  ->  history {b!r}")

    if unresolved:
        hist_names = sorted(key2name.values())
        print(f"\n*** {len(unresolved)} UNRESOLVED -- every game they officiate is "
              f"flagged DATA_GAP and NEVER actioned ***")
        for k, nm in sorted(unresolved.items(), key=lambda kv: kv[1]):
            near = difflib.get_close_matches(nm, hist_names, n=3, cutoff=0.6)
            gms = int(((S.ref1 == nm) | (S.ref2 == nm) | (S.ref3 == nm)).sum())
            print(f"  {nm!r:<30} {gms:>3} game(s)   nearest in history: "
                  f"{near if near else 'NONE -- likely a new official'}")
        print("\n  A name with a near match is a spelling to reconcile. A name with none")
        print("  is probably a genuinely new official, who has no history and correctly")
        print("  contributes nothing until they accumulate one.")
        return 1

    print("\nALL ASSIGNMENT NAMES RESOLVE")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--from", dest="dfrom", default=None)
    ap.add_argument("--to", dest="dto", default=None)
    ap.add_argument("--roster", action="store_true", help="list every official in history")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    try:
        sys.exit(check(a.days, a.dfrom, a.dto, a.roster, a.quiet))
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}")
        sys.exit(2)
