@echo off
REM NBA auto trader - Windows entry point.
REM Usage:  nba_trader.bat preflight
REM         nba_trader.bat early --arm
REM         nba_trader.bat late --arm
REM         nba_trader.bat cancel --arm
REM         nba_trader.bat dashboard
REM
REM Runs the WSL script; -u dpope pins the user so cron and manual runs share
REM the same HOME, logs and Kalshi credentials.
setlocal
if "%~1"=="" (
  echo Usage: nba_trader.bat {preflight^|early^|late^|cancel^|dashboard} [--arm] [--date YYYY-MM-DD]
  exit /b 1
)
wsl.exe -d Ubuntu -u dpope /mnt/d/Kalshi/nba/run_nba_trader.sh %*
exit /b %ERRORLEVEL%
