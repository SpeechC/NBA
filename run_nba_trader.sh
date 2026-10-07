#!/usr/bin/env bash
# Manual + cron entry point for the NBA auto trader.
#
#   ./run_nba_trader.sh preflight        checks everything, trades nothing
#   ./run_nba_trader.sh early            DRY RUN of the 09:00 phase
#   ./run_nba_trader.sh early --arm      places real orders
#   ./run_nba_trader.sh late --arm       CrewShock (needs referee assignments)
#   ./run_nba_trader.sh dashboard        build + publish s3://kalshi-strat/nba.html
#
# flock: a slow morning run must never overlap the next invocation.
set -uo pipefail
NBA=/mnt/d/Kalshi/nba
PY=/home/dpope/nba_env/bin/python
LOG=${NBA_LOG:-$HOME/logs/nba_auto.log}

# AWS: point at the WINDOWS profile the earnings-mention publisher already uses
# (s3://kalshi-strat/dashboard.html). Referenced, not copied -- one source of
# truth, so a rotation on the Windows side propagates here with no edit, and no
# second copy of a secret exists to go stale or leak.
export AWS_SHARED_CREDENTIALS_FILE=${AWS_SHARED_CREDENTIALS_FILE:-/mnt/c/Users/rando/.aws/credentials}
export AWS_CONFIG_FILE=${AWS_CONFIG_FILE:-/mnt/c/Users/rando/.aws/config}
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
# NO side PROVEN 2026-10-07 against the live exchange: order 01a116d0-37f8,
# fill 07254d0c, outcome_side="no", no_price_dollars=0.4400 at our 0.44 limit,
# is_taker=true. side='ask' buys NO. UNDER is enabled.
export NBA_NO_SIDE_VERIFIED=${NBA_NO_SIDE_VERIFIED:-1}
export NBA_S3_BUCKET=${NBA_S3_BUCKET:-kalshi-strat}
export NBA_S3_KEY=${NBA_S3_KEY:-nba.html}
mkdir -p "$(dirname "$LOG")"
exec 9>/tmp/nba_auto_trader.lock
flock -n 9 || { echo "$(date -Is) another run holds the lock; skipping" >>"$LOG"; exit 0; }
cd "$NBA" || exit 1
echo "=== $(date -Is) run_nba_trader.sh $* ===" >>"$LOG"
"$PY" "$NBA/nba_auto_trader.py" "$@" 2>&1 | tee -a "$LOG"
exit "${PIPESTATUS[0]}"
