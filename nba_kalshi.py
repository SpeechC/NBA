"""Kalshi NBA-totals market layer for the 2026-27 live test.

REUSES the proven signed client at /mnt/d/Kalshi (kalshi_client.py: credential
loading, RSA-PSS signing, rate limiting, retries, host fallback). That client is
GET-only; the POST path here is copied from kalshi_mentions/src/live_trader.py,
which has placed real orders, so the signing path stays the exercised one.

MARKET STRUCTURE (verified against kalshi_nba_totals.sqlite, 1,324 events)
  series        KXNBATOTAL
  event         KXNBATOTAL-25OCT21GSWLAL      YY MON DD AWAY HOME
  market        KXNBATOTAL-25OCT21GSWLAL-211  suffix = floor_strike truncated
  strike_type   'greater'   floor_strike 211.5   "Over 211.5 points scored"
  ~11 rungs per game at 3-point spacing

EVERY RUNG IS AN "OVER". Betting UNDER therefore requires a NO-side order, which
is the ONE thing in this file not already proven in production code. See buy_no().
"""
import os, sys, math, uuid, datetime as dt

KALSHI_CLIENT_DIR = os.environ.get("KALSHI_CLIENT_DIR", "/mnt/d/Kalshi")
if KALSHI_CLIENT_DIR not in sys.path:
    sys.path.append(KALSHI_CLIENT_DIR)
try:
    from kalshi_client import KalshiClient
except Exception:
    KalshiClient = None

SERIES   = "KXNBATOTAL"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"
_MON = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]


FEE_RATE = 0.07


def fee(p, contracts=1):
    """Total Kalshi fee in dollars for `contracts` at price `p`.

    MEASURED, not assumed, against 9 real settlements on this account: the
    implied rate is 0.0700-0.0707 (deviation is per-fill rounding), and the
    rounding is UP TO 0.001, not up to the cent.

        3.41 ct @ 0.870 -> 0.027000   ceil(.001) 0.0270   ceil(.01) 0.0300
       82.37 ct @ 0.590 -> 1.394800   ceil(.001) 1.3950   ceil(.01) 1.4000

    THE ROUNDING UNIT MATTERS AND IT IS CHARGED ON THE WHOLE ORDER. Rounding
    per-contract to the cent charges $0.50 on a 25-lot at 50c where Kalshi
    charges $0.438 -- 0.25c/contract, which is 18% of PaceGap's entire edge.
    Always pass the real order size.

    Peaks at 1.75c/contract near 50c and vanishes at the extremes, which is why
    cheap rungs look attractive on EV and are usually depth-starved.
    """
    return math.ceil(FEE_RATE * p * (1.0 - p) * contracts * 1000) / 1000.0


def price_ranges(m):
    """[(start, end, step)] for this market, read from the market itself.

    KXNBATOTAL is 'linear_cent' -- one band, step 0.0100, whole range -- but
    that is a per-series property, not an exchange-wide one: live multivariate
    markets already quote 'center_deci_edge_centi_cent', which is 0.0001 near
    the edges and 0.0010 in the middle. Hardcoding cents would silently post
    off-tick prices (HTTP 400) if NBA totals ever migrate, and would surrender
    nine ticks of queue position on every passive order meanwhile.

    THE STEP IS PRICE-DEPENDENT, so this returns the bands rather than a single
    number: taking the global minimum would quote 0.4315 on a grid whose middle
    band only accepts multiples of 0.0010, and the exchange would reject it.
    """
    out = []
    for r in (m.get("price_ranges") or []):
        try:
            s, e, st = float(r["start"]), float(r["end"]), float(r["step"])
        except (TypeError, ValueError, KeyError):
            continue
        if st > 0:
            out.append((s, e, st))
    return sorted(out) or [(0.0, 1.0, 0.01)]


def tick_at(ranges, price):
    """Increment applicable AT this price."""
    for s, e, st in ranges:
        if s <= price <= e:
            return st
    return ranges[-1][2] if ranges else 0.01


def snap(price, ranges, up=False):
    """Round a price onto its own band's grid, then clamp inside (0, 1).

    `up=True` rounds toward a higher price, otherwise down -- never past the
    limit the caller intended. The tick is resolved at the rounded price, then
    re-resolved once, because rounding can cross a band boundary.
    """
    for _ in range(2):
        t = tick_at(ranges, price)
        n = math.ceil(price / t - 1e-9) if up else math.floor(price / t + 1e-9)
        p = round(n * t, 6)
        if tick_at(ranges, p) == t:
            break
        price = p
    lo = ranges[0][2]
    return min(max(p, lo), round(1.0 - lo, 6))


def event_ticker(game_date, away_abbr, home_abbr):
    """KXNBATOTAL-25OCT21GSWLAL from (date, 'GSW', 'LAL')."""
    d = dt.date.fromisoformat(str(game_date)[:10])
    return f"{SERIES}-{d:%y}{_MON[d.month-1]}{d:%d}{away_abbr}{home_abbr}"


class NBAKalshi:
    def __init__(self, demo=False):
        if KalshiClient is None:
            raise RuntimeError(f"kalshi_client.py not importable from {KALSHI_CLIENT_DIR}")
        self.c = KalshiClient()
        if demo:
            self.c.base_url = DEMO_BASE.rstrip("/")
        else:
            self.c.base_url = self.c.probe_base_urls()
        self.demo = demo
        self.session_id = uuid.uuid4().hex[:12]

    # ---------------- read ----------------
    def whoami(self):
        """Authenticated GET. Proves signing BEFORE any order is contemplated."""
        try:
            return 200, self.c.get("/portfolio/balance")
        except Exception as e:
            return None, {"error": str(e)}

    def open_events(self, limit=200):
        d = self.c.get("/events", {"series_ticker": SERIES, "status": "open",
                                   "limit": limit}) or {}
        return d.get("events", [])

    def ladder(self, ev_ticker):
        """[(strike, ticker, yes_ask, yes_ask_size, yes_bid, status)] ascending.

        FIELD NAMES: the API returns `yes_ask_dollars` as a STRING IN DOLLARS
        ('0.2500'), not `yes_ask` in cents. Reading the obvious name yields None
        for every market and silently trades nothing. `yes_ask_size_fp` is the
        contracts available AT that ask -- the capacity constraint this whole
        programme keeps hitting, and it is free here.
        """
        d = self.c.get("/markets", {"event_ticker": ev_ticker, "limit": 200}) or {}
        out = []
        for m in d.get("markets", []):
            fs = m.get("floor_strike")
            if fs is None:
                continue
            g = lambda k: (lambda v: None if v is None else float(v))(m.get(k))
            out.append(dict(strike=float(fs), ticker=m["ticker"],
                            yes_ask=g("yes_ask_dollars"), yes_ask_size=g("yes_ask_size_fp"),
                            yes_bid=g("yes_bid_dollars"), yes_bid_size=g("yes_bid_size_fp"),
                            ranges=price_ranges(m),
                            status=m.get("status"), title=m.get("yes_sub_title")))
        return sorted(out, key=lambda r: r["strike"])

    # ---------------- write ----------------
    def _coid(self, ticker, tag):
        """DETERMINISTIC per (session, ticker, strategy). Kalshi rejects a repeated
        client_order_id with 409, so the EXCHANGE refuses a duplicate even if every
        local guard in this file fails. It is the only guard that survives a bug here."""
        return f"{self.session_id}-{tag}-{ticker}"[:64]

    def _order(self, ticker, side, count, limit_dollars, tag):
        """POST /portfolio/events/orders.

        SCHEMA, each line a way a first implementation gets it wrong:
          * path is /portfolio/events/orders, NOT /portfolio/orders
          * price is a STRING in DOLLARS to 4dp ("0.6500"), not cents
          * count is a STRING
          * time_in_force and self_trade_prevention_type are required
          * SUCCESS IS 201, not 200
        """
        path = "/portfolio/events/orders"
        url = f"{self.c.base_url}{path}"
        coid = self._coid(ticker, tag)
        body = {"ticker": ticker, "side": side, "count": str(int(count)),
                "price": f"{float(limit_dollars):.4f}",
                "time_in_force": "good_till_canceled",
                "self_trade_prevention_type": "taker_at_cross",
                "client_order_id": coid}
        h = dict(self.c._auth_headers("POST", url)); h["Content-Type"] = "application/json"
        r = self.c.session.post(url, headers=h, json=body, timeout=10)
        try:
            out = r.json() if r.content else {}
        except Exception:
            out = {"raw": r.text[:300]}
        if r.status_code != 201:
            out["_hint"] = {401: "signature/key problem",
                            400: "bad params -- price must be 0.01-0.99",
                            409: "duplicate client_order_id (guard worked)",
                            429: "rate limited"}.get(r.status_code, "")
        out["_client_order_id"] = coid
        return r.status_code, out

    def buy_yes(self, ticker, count, limit_dollars, tag="nba"):
        """side='bid' BUYS YES. Proven in kalshi_mentions/src/live_trader.py."""
        return self._order(ticker, "bid", count, limit_dollars, tag)

    def buy_no(self, ticker, count, limit_dollars, tag="nba"):
        """Buy NO -- required because EVERY NBA totals rung is an 'Over'.

        *** NOT YET PROVEN AGAINST THE EXCHANGE. ***  The YES path above has
        placed real orders; this one has not. `side='ask'` is the documented
        counterpart to the 'bid'=BUY-YES convention, but it is inferred, not
        observed, and `limit_dollars` here is the NO price, not 1-minus-YES.

        DO NOT ARM THIS LIVE until a 1-contract fill has been confirmed in DEMO
        (NBAKalshi(demo=True)). nba_live_trader refuses UNDER orders unless
        NO_SIDE_VERIFIED is set, precisely so this cannot go out untested.
        """
        return self._order(ticker, "ask", count, limit_dollars, tag)

    def resting_orders(self, status="resting"):
        d = self.c.get("/portfolio/orders", {"limit": 200, "status": status}) or {}
        return d.get("orders", [])

    def cancel(self, order_id):
        """DELETE /portfolio/orders/{id}. MANDATORY before tip.

        NBA totals markets do NOT close at tipoff -- they trade in-play. A
        resting pregame bid left open is a free option sold to anyone watching
        the game: it fills precisely when the score has already moved against
        it. Cancelling is not tidying up, it is the position limit.
        """
        url = f"{self.c.base_url}/portfolio/orders/{order_id}"
        h = self.c._auth_headers("DELETE", url)
        r = self.c.session.delete(url, headers=h, timeout=10)
        try:
            return r.status_code, (r.json() if r.content else {})
        except Exception:
            return r.status_code, {"raw": r.text[:200]}

    def positions(self):
        d = self.c.get("/portfolio/positions", {"limit": 200}) or {}
        return d.get("market_positions", [])

    def fills(self, limit=200):
        d = self.c.get("/portfolio/fills", {"limit": limit}) or {}
        return d.get("fills", [])

    def settlements(self, limit=200):
        """Settled positions -- the ONLY authoritative P&L.

        A fill is not a result and a position mark is not a result. Kalshi
        settles NBA totals on the official final score, so `settlements` is what
        the dashboard reports; anything computed from marks would be an estimate
        wearing a P&L's clothes.
        """
        d = self.c.get("/portfolio/settlements", {"limit": limit}) or {}
        return d.get("settlements", [])


# ---------------- pricing ----------------
def ladder_prices(mu, sigma, strikes):
    """P(total > K) for each rung -- the Layer-1 engine, unchanged.

    sigma is EXPECTED TOTAL-SCORE DISPERSION, never a betting spread. The
    programme's own measurement: the normal holds to a ratio of 0.996 inside
    +/-1.1 sigma, which is exactly the span Kalshi quotes, and fails only
    beyond 2.5 sigma where no rung exists.
    """
    from scipy.stats import norm
    s = max(float(sigma), 1e-6)
    return {float(k): float(1.0 - norm.cdf((float(k) - mu) / s)) for k in strikes}


# Edge selection lives in nba_live_trader.candidates(), deliberately NOT here.
# Two implementations of "which rung is worth buying" would drift apart, and the
# one in the trader is the one with the direction gate and the maker pricing.
