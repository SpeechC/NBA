#!/bin/bash
# Wait for the re-parse, then Stage-0 gates (now incl. Q4 era stability), then
# the PREREG_injury.md market tests -- but ONLY if every gate passes.
cd /home/dpope/projects/nba_entropy_replication
until grep -q "^wrote injury_status_panel.csv" injury_parse.log 2>/dev/null; do sleep 20; done
echo "=== PARSE DONE ==="; tail -5 injury_parse.log
echo; echo "=== STAGE-0 GATES ==="
/home/dpope/nba_env/bin/python -u injury_gates.py 2>&1 | tee injury_gates.out | tail -40
if grep -q "gates pass; the PREREG_injury.md market tests may proceed" injury_gates.out; then
  echo; echo "=== MARKET TESTS ==="
  /home/dpope/nba_env/bin/python -u injury_market.py 2>&1 | tee injury_market.out | tail -45
  echo; echo "=== HYPOTHESIS B DIAGNOSTICS ==="
  /home/dpope/nba_env/bin/python -u injury_market_diag.py 2>&1 | tee injury_diag.out | tail -22
else
  echo; echo "!!! A GATE FAILED -- market tests NOT run (prereg section 5) !!!"
fi
