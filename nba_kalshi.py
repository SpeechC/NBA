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
import os, sys, math, uuid, json, datetime as dt

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
        self._shard = None

    # ---------------- read ----------------
    def whoami(self):
        """Authenticated GET. Proves signing BEFORE any order is contemplated."""
        try:
            return 200, self.c.get("/portfolio/balance")
        except Exception as e:
            return None, {"error": str(e)}

    def shard(self):
        """exchange_index for this series, resolved once and cached.

        *** EVERY PORTFOLIO READ IS SHARD-SCOPED. *** Verified 2026-10-07: after
        a real NBA fill, /portfolio/fills and /portfolio/positions on shard 0
        returned ZERO NBA rows; only exchange_index=3 showed them. The parameter
        defaults to 0, so without it the dashboard would report an empty NBA book
        all season and cancel_stale() would never see an NBA order to pull --
        which matters because NBA totals trade IN-PLAY and an uncancelled resting
        bid is a free option.

        Note -1 auto-routes ORDERS but is REJECTED on reads
        ("ExchangeIndex failed on the 'gte' tag"), so reads need a concrete index.
        """
        if self._shard is None:
            try:
                idx = self.series_shard()
            except Exception:
                idx = None
            if idx is None:
                idx = int(os.environ.get("NBA_EXCHANGE_INDEX", "3"))
            self._shard = int(idx)
        return self._shard

    def shard_balance(self):
        """{exchange_index: dollars} from /portfolio/balance.

        KALSHI SHARDS ITS EXCHANGE AND FUNDS DO NOT CROSS. Discovered
        2026-10-07 when a 1-contract NBA probe returned

            404 insufficient_shard_balance -- "Exchange user not found"

        which looks like a bad order but is an account-routing error. The shards
        are 0 Default, 1 Combos, 2 Crypto & Commodities, 3 Tennis/Baseball/
        Basketball. EVERY NBA series is on shard 3; the mention markets this
        account has traded are on shard 0. A balance on 0 buys nothing on 3.
        """
        d = self.c.get("/portfolio/balance") or {}
        out = {}
        for x in d.get("balance_breakdown", []) or []:
            try:
                out[int(x["exchange_index"])] = float(x["balance"])
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def series_shard(self, series=None):
        """exchange_index the series trades on, read from an open event. None if
        no open event. Do not hardcode: NBA is 3 today, but it is a property of
        the venue, not of us."""
        d = self.c.get("/events", {"series_ticker": series or SERIES,
                                   "status": "open", "limit": 1}) or {}
        ev = (d.get("events") or [None])[0]
        return None if ev is None else ev.get("exchange_index")

    def open_events(self, limit=200):
        d = self.c.get("/events", {"series_ticker": SERIES, "status": "open",
                                   "limit": limit}) or {}
        return d.get("events", [])

    def ladder(self, ev_ticker):
        """Per-rung quotes, ascending by strike, BOTH sides.

        FIELD NAMES: the API returns `yes_ask_dollars` as a STRING IN DOLLARS
        ('0.2500'), not `yes_ask` in cents. Reading the obvious name yields None
        for every market and silently trades nothing. `yes_ask_size_fp` is the
        contracts available AT that ask -- the capacity constraint this whole
        programme keeps hitting, and it is free here.

        NO SIDE: prices come from the exchange's own `no_bid_dollars` /
        `no_ask_dollars`. SIZES DO NOT EXIST for the NO side -- the API ships
        only `yes_bid_size_fp` and `yes_ask_size_fp` -- so they are MIRRORED:
        a NO buy consumes the YES BID book, hence

            no_ask_size = yes_bid_size      no_bid_size = yes_ask_size

        which is the depth correction already on record from the weather work;
        the mirrored side is routinely 10-40x thinner than the quoted one.

        `no_complement_ok` is False if the exchange ever stops being an exact
        complement (no_bid == 1-yes_ask and no_ask == 1-yes_bid). That identity
        is verified on 470 live markets across 4 series with 0 violations, and
        nba_live_trader._quote() DERIVES the NO side from it rather than reading
        these fields -- so a divergence must be surfaced, not silently absorbed.
        """
        d = self.c.get("/markets", {"event_ticker": ev_ticker, "limit": 200}) or {}
        out = []
        for m in d.get("markets", []):
            fs = m.get("floor_strike")
            if fs is None:
                continue
            g = lambda k: (lambda v: None if v is None else float(v))(m.get(k))
            yb, ya = g("yes_bid_dollars"), g("yes_ask_dollars")
            nb, na = g("no_bid_dollars"), g("no_ask_dollars")
            ok = (None not in (yb, ya, nb, na)
                  and abs(nb - (1.0 - ya)) < 1e-9 and abs(na - (1.0 - yb)) < 1e-9)
            out.append(dict(strike=float(fs), ticker=m["ticker"],
                            yes_ask=ya, yes_ask_size=g("yes_ask_size_fp"),
                            yes_bid=yb, yes_bid_size=g("yes_bid_size_fp"),
                            no_ask=na, no_ask_size=g("yes_bid_size_fp"),
                            no_bid=nb, no_bid_size=g("yes_ask_size_fp"),
                            no_complement_ok=ok,
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
        # exchange_index = -1 AUTO-ROUTES to the shard that lists the ticker.
        # Omitting it defaults to shard 0, which is NOT where NBA trades (NBA is
        # shard 3, "Tennis, Baseball, Basketball"). Documented at
        # docs.kalshi.com/getting_started/exchange_sharding: "If exchange_index
        # is -1, auto-routes using the required market_ticker."
        # Routing alone is NOT sufficient -- Kalshi runs collateral checks inside
        # each matching engine, so funds must ALSO be preallocated on that shard
        # (see transfer_shard() and shard_balance()).
        body = {"ticker": ticker, "side": side, "count": str(int(count)),
                "price": f"{float(limit_dollars):.4f}",
                "time_in_force": "good_till_canceled",
                "self_trade_prevention_type": "taker_at_cross",
                "exchange_index": -1,
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

    def transfer_shard(self, amount_dollars, dest_shard, src_shard=0, dry=True):
        """Move funds between exchange shards. POST /portfolio/intra_exchange_instance_transfer.

        Kalshi runs collateral checks inside each matching engine, so a
        programmatic trader must PREALLOCATE on the shard it intends to trade.
        A balance on shard 0 buys nothing on shard 3.

        *** `amount` IS IN CENTICENTS. *** $1 = 100 cents = 10,000 centicents.
        Getting that wrong by a factor of 100 is the obvious way to move far more
        or far less than intended, so the dollar figure is converted here and the
        computed body is printed before anything is sent.

        `source` / `destination` are the exchange INSTANCE (`event_contract` or
        `margined`), which is a different axis from the SHARD index. A
        shard-to-shard move within event contracts keeps both as
        `event_contract`.

        dry=True by default: returns the exact body without sending it.
        """
        cc = int(round(float(amount_dollars) * 10000))
        body = {"source": "event_contract", "destination": "event_contract",
                "amount": cc,
                "source_exchange_shard": int(src_shard),
                "destination_exchange_shard": int(dest_shard),
                "source_subaccount": 0, "destination_subaccount": 0}
        print(f"transfer ${float(amount_dollars):.2f} = {cc:,} centicents  "
              f"shard {src_shard} -> {dest_shard}")
        print(f"  body: {json.dumps(body)}")
        if dry:
            print("  DRY RUN -- nothing sent.")
            return None, body
        path = "/portfolio/intra_exchange_instance_transfer"
        url = f"{self.c.base_url}{path}"
        h = dict(self.c._auth_headers("POST", url)); h["Content-Type"] = "application/json"
        r = self.c.session.post(url, headers=h, json=body, timeout=15)
        try:
            out = r.json() if r.content else {}
        except Exception:
            out = {"raw": r.text[:300]}
        return r.status_code, out

    def resting_orders(self, status="resting"):
        d = self.c.get("/portfolio/orders", {"limit": 200, "status": status,
                                     "exchange_index": self.shard()}) or {}
        return d.get("orders", [])

    def cancel(self, order_id, ticker=None):
        """DELETE /portfolio/events/orders/{id} -- the V2 path. MANDATORY before tip.

        *** THE V1 PATH IS DEAD AND SILENTLY BROKE CANCELLATION. *** Until
        2026-10-07 this used `DELETE /portfolio/orders/{id}`, which now returns

            410 deprecated_v1_order_endpoint -- "Please switch to the V2 endpoints"

        so cancel_stale() could never cancel anything. It had been reporting
        "0/0 of our resting orders cancelled" twice an hour, which reads as
        "nothing to do" and is indistinguishable from success. Found only by
        leaving a real resting order and trying to pull it.

        That mattered: NBA totals do NOT close at tipoff, they trade IN-PLAY. A
        resting pregame order left open is a free option sold to anyone watching
        the game -- it fills precisely when the score has moved against it.
        Cancelling is not tidying up, it is the position limit.

        `market_ticker` is required when exchange_index is -1 (auto-routing),
        and NBA is not on the default shard, so the ticker is passed through.
        """
        url = f"{self.c.base_url}/portfolio/events/orders/{order_id}"
        params = {"exchange_index": -1}
        if ticker:
            params["market_ticker"] = ticker
        q = "&".join(f"{k}={v}" for k, v in params.items())
        full = f"{url}?{q}"
        h = self.c._auth_headers("DELETE", full)
        r = self.c.session.delete(full, headers=h, timeout=10)
        try:
            return r.status_code, (r.json() if r.content else {})
        except Exception:
            return r.status_code, {"raw": r.text[:200]}

    def positions(self):
        d = self.c.get("/portfolio/positions", {"limit": 200,
                                        "exchange_index": self.shard()}) or {}
        return d.get("market_positions", [])

    def fills(self, limit=200):
        d = self.c.get("/portfolio/fills", {"limit": limit,
                                    "exchange_index": self.shard()}) or {}
        return d.get("fills", [])

    def settlements(self, limit=200):
        """Settled positions -- the ONLY authoritative P&L.

        A fill is not a result and a position mark is not a result. Kalshi
        settles NBA totals on the official final score, so `settlements` is what
        the dashboard reports; anything computed from marks would be an estimate
        wearing a P&L's clothes.
        """
        d = self.c.get("/portfolio/settlements", {"limit": limit,
                                          "exchange_index": self.shard()}) or {}
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
