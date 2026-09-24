"""Capture KXNBAGAME / KXNBASPREAD / KXNBATOTAL boards before Kalshi purges them.

WHY THIS EXISTS
    Kalshi retains settled EVENTS but deletes their MARKETS. Verified
    2026-09-24: 1,448 settled KXNBAGAME and 1,324 settled KXNBASPREAD events
    for 2025-26 are all still listed, and /markets returns 0 for every one of
    them on every status filter. There is no historical Kalshi spread or
    moneyline board and none can be obtained. Everything this programme wants
    to ask about cross-market coherence is forward-collection or nothing.

WHY IT IS A DAILY JOB AND NOT A POLLER
    Candlesticks reconstruct the intraday path retroactively. A market listed
    on 2026-08-20 still serves 790 hourly bars covering its whole life. So the
    lead-lag work does NOT need high-frequency polling -- it needs to run often
    enough to beat the purge, which is a matter of weeks, not minutes.

    1-minute candles are available but the endpoint caps a request at 5,000
    candles, so the window is chunked at 3 days.

TWO THINGS THAT WILL BITE
    * Candles emit only on book CHANGE. A quiet market produces no rows; it
      does not produce flat rows. Forward-fill per ticker AT ANALYSIS TIME.
      Treating a gap as missing data fabricates illiquidity.
    * Prices are `*_dollars` STRINGS nested under yes_bid/yes_ask, and size is
      `volume_fp`. Reading `yes_bid` as a number yields None for every row.

KXNBAGAME is structured (one market per team, no floor_strike); KXNBASPREAD
and KXNBATOTAL are ladders with floor_strike. All three are stored in one
table and distinguished by series_ticker.
"""
import os, sys, json, sqlite3, argparse, datetime as dt

KALSHI_CLIENT_DIR = os.environ.get("KALSHI_CLIENT_DIR", "/mnt/d/Kalshi")
if KALSHI_CLIENT_DIR not in sys.path:
    sys.path.append(KALSHI_CLIENT_DIR)
from kalshi_client import KalshiClient

SERIES = ("KXNBAGAME", "KXNBASPREAD", "KXNBATOTAL")
DB = os.environ.get("NBA_XMARKET_DB",
                    os.path.expanduser("~/data/kalshi_local/kalshi_nba_xmarket.sqlite"))
CHUNK_DAYS = 3                    # 4,320 one-minute candles < the 5,000 cap
MAX_CANDLES_PER_REQ = 5000

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_ticker  TEXT PRIMARY KEY,
    series_ticker TEXT, game_date TEXT, away_team TEXT, home_team TEXT,
    title TEXT, sub_title TEXT, status TEXT, first_seen TEXT, last_seen TEXT
);
CREATE TABLE IF NOT EXISTS markets (
    ticker TEXT PRIMARY KEY,
    event_ticker TEXT, series_ticker TEXT, game_date TEXT,
    yes_sub_title TEXT, strike_type TEXT, floor_strike REAL, cap_strike REAL,
    status TEXT, result TEXT, open_time TEXT, close_time TEXT,
    open_ts INTEGER, close_ts INTEGER, last_seen TEXT, raw TEXT
);
CREATE TABLE IF NOT EXISTS candles (
    ticker TEXT NOT NULL, period_interval INTEGER NOT NULL,
    end_period_ts INTEGER NOT NULL, end_period_utc TEXT,
    event_ticker TEXT, series_ticker TEXT, game_date TEXT, floor_strike REAL,
    yes_bid_open REAL, yes_bid_high REAL, yes_bid_low REAL, yes_bid_close REAL,
    yes_ask_open REAL, yes_ask_high REAL, yes_ask_low REAL, yes_ask_close REAL,
    price_previous REAL, volume REAL, open_interest REAL,
    PRIMARY KEY (ticker, period_interval, end_period_ts)
);
CREATE INDEX IF NOT EXISTS ix_candles_event ON candles(event_ticker, end_period_ts);
CREATE INDEX IF NOT EXISTS ix_candles_date  ON candles(game_date, series_ticker);
CREATE TABLE IF NOT EXISTS fetch_log (
    ticker TEXT NOT NULL, period_interval INTEGER NOT NULL,
    high_water_ts INTEGER, n_candles INTEGER, fetched_at TEXT,
    PRIMARY KEY (ticker, period_interval)
);
CREATE TABLE IF NOT EXISTS run_log (
    run_at TEXT, series TEXT, n_events INTEGER, n_markets INTEGER,
    n_candles_new INTEGER, note TEXT
);
"""
_MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def parse_event(t):
    """('2026-10-20','BOS','DET') from KXNBAGAME-26OCT20BOSDET."""
    try:
        tail = t.split("-", 1)[1]
        yy, mon, dd = int(tail[:2]), tail[2:5], int(tail[5:7])
        teams = tail[7:]
        d = dt.date(2000 + yy, _MON.index(mon) + 1, dd)
        n = len(teams)
        return d.isoformat(), teams[:n // 2], teams[n // 2:]
    except Exception:
        return None, None, None


def fnum(v):
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=60)
    c.executescript(SCHEMA)
    return c


def collect_events(k, series, statuses):
    out = []
    for st in statuses:
        cur = None
        while True:
            p = {"series_ticker": series, "status": st, "limit": 200}
            if cur:
                p["cursor"] = cur
            d = k.get("/events", p) or {}
            b = d.get("events", [])
            out += b
            cur = d.get("cursor")
            if not cur or not b:
                break
    return out


def candles(k, series, ticker, start_ts, end_ts, interval):
    """Chunked candle pull. 404/400 on a purged or too-new market is not fatal."""
    rows, t = [], start_ts
    step = CHUNK_DAYS * 86400 if interval == 1 else MAX_CANDLES_PER_REQ * interval * 60
    while t < end_ts:
        hi = min(t + step, end_ts)
        try:
            d = k.get(f"/series/{series}/markets/{ticker}/candlesticks",
                      {"start_ts": int(t), "end_ts": int(hi),
                       "period_interval": interval}) or {}
            rows += d.get("candlesticks", [])
        except Exception as e:
            if "404" not in str(e) and "400" not in str(e):
                raise
        t = hi
    return rows


def run(days_back, interval, series_list, verbose=True):
    k = KalshiClient()
    k.base_url = k.probe_base_urls()
    con = connect()
    now = int(now_utc().timestamp())
    floor_ts = now - days_back * 86400
    stamp = now_utc().isoformat()
    totals = {}

    for series in series_list:
        evs = collect_events(k, series, ("open", "closed", "settled"))
        keep = []
        for e in evs:
            et = e.get("event_ticker", "")
            gd, away, home = parse_event(et)
            if gd is None:
                continue
            # Only events whose game is inside the capture window.
            if dt.date.fromisoformat(gd) < dt.date.fromtimestamp(floor_ts):
                continue
            keep.append((e, et, gd, away, home))
            con.execute(
                """INSERT INTO events(event_ticker,series_ticker,game_date,away_team,
                     home_team,title,sub_title,status,first_seen,last_seen)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(event_ticker) DO UPDATE SET
                     status=excluded.status, last_seen=excluded.last_seen""",
                (et, series, gd, away, home, e.get("title"), e.get("sub_title"),
                 e.get("status"), stamp, stamp))
        con.commit()

        n_mkt = n_new = 0
        for e, et, gd, away, home in keep:
            ms = (k.get("/markets", {"event_ticker": et, "limit": 200}) or {}).get("markets", [])
            for m in ms:
                tk = m["ticker"]
                n_mkt += 1
                ot, ct = m.get("open_time"), m.get("close_time")
                to_ts = lambda s: int(dt.datetime.fromisoformat(
                    s.replace("Z", "+00:00")).timestamp()) if s else None
                ots, cts = to_ts(ot), to_ts(ct)
                con.execute(
                    """INSERT INTO markets(ticker,event_ticker,series_ticker,game_date,
                         yes_sub_title,strike_type,floor_strike,cap_strike,status,result,
                         open_time,close_time,open_ts,close_ts,last_seen,raw)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(ticker) DO UPDATE SET
                         status=excluded.status, result=excluded.result,
                         last_seen=excluded.last_seen""",
                    (tk, et, series, gd, m.get("yes_sub_title"), m.get("strike_type"),
                     fnum(m.get("floor_strike")), fnum(m.get("cap_strike")),
                     m.get("status"), m.get("result"), ot, ct, ots, cts, stamp,
                     json.dumps(m)[:4000]))

                hw = con.execute(
                    "SELECT high_water_ts FROM fetch_log WHERE ticker=? AND period_interval=?",
                    (tk, interval)).fetchone()
                start = max(hw[0], ots or floor_ts) if hw and hw[0] else (ots or floor_ts)
                start = max(start, floor_ts)
                end = min(now, (cts + 6 * 3600) if cts else now)
                if end <= start:
                    continue

                cs = candles(k, series, tk, start, end, interval)
                fs = fnum(m.get("floor_strike"))
                rows = []
                for r in cs:
                    ts = r.get("end_period_ts")
                    if ts is None:
                        continue
                    b, a = r.get("yes_bid") or {}, r.get("yes_ask") or {}
                    rows.append((
                        tk, interval, int(ts),
                        dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(),
                        et, series, gd, fs,
                        fnum(b.get("open_dollars")), fnum(b.get("high_dollars")),
                        fnum(b.get("low_dollars")), fnum(b.get("close_dollars")),
                        fnum(a.get("open_dollars")), fnum(a.get("high_dollars")),
                        fnum(a.get("low_dollars")), fnum(a.get("close_dollars")),
                        fnum((r.get("price") or {}).get("previous_dollars")),
                        fnum(r.get("volume_fp")), fnum(r.get("open_interest_fp"))))
                if rows:
                    before = con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
                    con.executemany(
                        "INSERT OR IGNORE INTO candles VALUES(" + ",".join(["?"] * 19) + ")",
                        rows)
                    n_new += con.execute("SELECT COUNT(*) FROM candles").fetchone()[0] - before
                    hwm = max(r[2] for r in rows)
                else:
                    hwm = end
                con.execute(
                    """INSERT INTO fetch_log(ticker,period_interval,high_water_ts,n_candles,fetched_at)
                       VALUES(?,?,?,?,?) ON CONFLICT(ticker,period_interval) DO UPDATE SET
                         high_water_ts=excluded.high_water_ts,
                         n_candles=fetch_log.n_candles+excluded.n_candles,
                         fetched_at=excluded.fetched_at""",
                    (tk, interval, hwm, len(cs), stamp))
            con.commit()

        totals[series] = (len(keep), n_mkt, n_new)
        con.execute("INSERT INTO run_log VALUES(?,?,?,?,?,?)",
                    (stamp, series, len(keep), n_mkt, n_new, f"interval={interval}"))
        con.commit()
        if verbose:
            print(f"  {series:14s} events {len(keep):4d}  markets {n_mkt:5d}  "
                  f"new candles {n_new:7d}")

    if verbose:
        tot = con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
        print(f"  DB {DB}  total candles {tot:,}")
    con.close()
    return totals


def probe():
    """Report what is visible right now. Writes nothing."""
    k = KalshiClient()
    k.base_url = k.probe_base_urls()
    print(f"as of {now_utc().isoformat()}  base {k.base_url}")
    for s in SERIES:
        line = []
        for st in ("open", "settled"):
            d = k.get("/events", {"series_ticker": s, "status": st, "limit": 200}) or {}
            line.append(f"{st}={len(d.get('events', []))}{'+' if d.get('cursor') else ''}")
        d = k.get("/markets", {"series_ticker": s, "status": "open", "limit": 200}) or {}
        ms = d.get("markets", [])
        print(f"  {s:14s} events {' '.join(line):22s} open markets {len(ms)}")
        if ms:
            m = ms[0]
            print(f"      e.g. {m['ticker']} {m.get('yes_sub_title')!r} "
                  f"bid={m.get('yes_bid_dollars')} ask={m.get('yes_ask_dollars')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--days-back", type=int, default=10,
                    help="capture games within this many days (both directions)")
    ap.add_argument("--interval", type=int, default=1, choices=(1, 60),
                    help="candle period in minutes")
    ap.add_argument("--series", default=",".join(SERIES))
    a = ap.parse_args()
    if a.probe:
        probe()
    else:
        print(f"collect  days_back={a.days_back}  interval={a.interval}m")
        run(a.days_back, a.interval, [s for s in a.series.split(",") if s])
