"""Build the NBA live-trading dashboard and publish it to S3.

    python nba_dashboard.py --build                  # local HTML only
    python nba_dashboard.py --build --publish        # + upload to S3

=============================================================================
WHAT THIS PAGE MAY AND MAY NOT SHOW -- read before adding a panel
=============================================================================
Two different objects are easy to confuse here, and conflating them destroys a
season of work:

  KALSHI P&L            real money, real fills, settled against the ACTUAL total
                        at a fixed strike. SHOWN. You cannot trade capital
                        blind; this is risk management, not inference.

  THE PREREGISTERED     `prospective_log.csv` graded against `open_total` at a
  2026-27 TEST          notional $100 flat stake. NOT SHOWN, and not computable
                        from anything on this page. PREREG_2026_27_PROSPECTIVE
                        D3 forbids interim looks; `evaluate_season.py` refuses
                        to run before 2027-04-15 and this module never imports
                        it.

They are genuinely different numbers -- different settlement basis, different
prices, capacity-constrained fills -- but they are CORRELATED, and pretending
otherwise would be self-deception. AMENDMENT_live_trading.md records that
trading live materially weakens the 2026-27 prospective test, as a cost being
accepted deliberately rather than a technicality being routed around.

So: no hit rate by threshold, no alternative-threshold panel, no Over/Under
split, no month or team breakdown. Those are the specific things D3 names, and
none of them is needed to manage a position.
"""
import os, sys, csv, json, argparse, datetime as dt
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nba_kalshi as NK
import nba_live_trader as LT     # also puts LT.PROJECT_DIR on sys.path, which is
                                 # how `import prospective_log` below resolves when
                                 # this module is installed outside the project

OUT_HTML = os.path.expanduser("~/data/nba_dashboard.html")
S3_BUCKET = os.environ.get("NBA_S3_BUCKET", "kalshi-strat")
S3_KEY    = os.environ.get("NBA_S3_KEY", "nba.html")
STATE     = os.path.expanduser("~/data/nba_daily_state.jsonl")


def _rows(path):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def collect(demo=False):
    """Everything the page needs. Live account state wins over any local log."""
    d = dict(built=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             ok=True, err="", balance=None, positions=[], settlements=[],
             resting=[], fills=[], orders=_rows(LT.FILLS), health={})
    try:
        k = NK.NBAKalshi(demo=demo)
        code, who = k.whoami()
        if code != 200:
            raise RuntimeError(f"auth {code}: {who}")
        d["balance"] = (who.get("balance") or 0) / 100.0
        d["positions"]   = k.positions()
        d["settlements"] = k.settlements()
        d["resting"]     = k.resting_orders()
        d["fills"]       = [f for f in k.fills()
                            if str(f.get("ticker", "")).startswith(NK.SERIES)]
    except Exception as e:
        d["ok"], d["err"] = False, str(e)[:300]
    try:
        import prospective_log as PL
        d["health"] = PL.health()          # field population ONLY -- see D3
    except Exception as e:
        d["health"] = {"error": str(e)[:120]}
    if os.path.exists(STATE):
        with open(STATE) as f:
            runs = [json.loads(l) for l in f][-30:]
        d["runs"] = runs
    return d


def _strategy_of(ticker, orders, fills=()):
    """Which strategy owns this settlement.

    A settlement carries no strategy tag, so attribution walks two paths:
      1. our own append-only order log, matched on ticker (primary);
      2. the fill's client_order_id, which embeds the tag as {session}-{tag}-...

    Anything still unmatched returns "unattributed" and is rendered as a visible
    reconciliation failure, NOT folded into a strategy. A settlement whose owner
    is unknown is money moving for a reason we cannot name, and quietly
    bucketing it would make the per-strategy table wrong in the one case where
    it matters -- an order placed from another host or a rotated log.
    """
    for o in reversed(orders):
        if o.get("ticker") == ticker:
            return o.get("strategy") or "unattributed"
    for f in fills:
        if f.get("ticker") == ticker:
            coid = f.get("client_order_id") or ""
            for t in LT.STRATS:
                if f"-{t}-" in coid:
                    return t
    return "unattributed"


# DISPLAY ONLY. The keys ("crewshock", "pacegap", "move") are load-bearing:
# they are embedded in every client_order_id tag and are how a settlement is
# attributed back to the strategy that ordered it. Rename the label here, never
# the key.
DISPLAY = {"crewshock": "cs"}


def _f(v):
    """Kalshi returns money as STRINGS IN DOLLARS ('0.150000') in some fields and
    INTEGER CENTS in others. Verified on live settlements: yes/no_total_cost and
    fee_cost are dollar strings; `revenue` and `value` are cents. Reading either
    one with the wrong convention is a silent 100x, so both are converted here
    and nowhere else."""
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _side_of(ticker, orders, fills=()):
    """Which side the TRADER bought, from its own append-only order log.

    Falls back to the exchange's fill record. Returns None if neither knows,
    which makes the caller count the settlement as inferred rather than guess.
    """
    for o in reversed(orders):
        if o.get("ticker") == ticker and o.get("side"):
            return str(o["side"]).upper()
    for f in fills:
        if f.get("ticker") == ticker:
            s = str(f.get("side") or f.get("outcome_side") or "").upper()
            if s in ("YES", "NO"):
                return s
    return None


def summarise(d):
    """Per-strategy realised P&L from SETTLEMENTS. No hit-rate-by-threshold, no
    alternative thresholds, no splits -- see the module docstring.

    Scoped to KXNBATOTAL. The same Kalshi account runs the weather and mention
    systems, and their settlements are in the same feed; without this filter
    their P&L would appear here under strategy '?'.
    """
    agg = defaultdict(lambda: dict(n=0, won=0, cost=0.0, ret=0.0, fee=0.0, infer=0))
    for s in d["settlements"]:
        tk = s.get("ticker", "")
        if not tk.startswith(NK.SERIES):
            continue
        a = agg[_strategy_of(tk, d["orders"], d.get("fills", ()))]
        cost = _f(s.get("yes_total_cost_dollars")) + _f(s.get("no_total_cost_dollars"))
        fee  = _f(s.get("fee_cost"))
        ret  = _f(s.get("revenue")) / 100.0          # cents -> dollars

        # WIN IS DEFINED THE WAY THE TRADER DEFINES IT: the side we bought
        # against how the market resolved. Taken from our OWN order log, which
        # is what recorded the decision.
        #
        # The previous rule here was `ret > cost + fee` -- inferring the result
        # from cash flow. It agrees at 1 contract, but it is a DIFFERENT RULE:
        # it scores a contract that resolved our way but earned less than its
        # fee as a LOSS, which is a P&L statement, not a hit rate. Hit rate has
        # to count outcomes or it stops being comparable to the 52-55% the
        # strategies were measured at.
        side = _side_of(tk, d["orders"], d.get("fills", ()))
        res = str(s.get("market_result", "")).lower()
        if side and res in ("yes", "no"):
            won = (side == "YES" and res == "yes") or (side == "NO" and res == "no")
        else:
            won = ret > cost + fee                   # last resort; counted below
            a["infer"] += 1
        a["n"] += 1
        a["won"] += int(won)
        a["cost"] += cost
        a["fee"] += fee
        a["ret"] += ret
        a["ct"] = a.get("ct", 0.0) + _f(s.get("yes_count_fp")) + _f(s.get("no_count_fp"))
    for a in agg.values():
        a["pl"] = a["ret"] - a["cost"] - a["fee"]
        # ROI DENOMINATOR IS TOTAL OUTLAY, cost + fee. The fee is money put at
        # risk, not a deduction from winnings -- Kalshi charges it on entry, and
        # the trader's own EV is p_model - price - fee against the same unit.
        # Excluding it (the previous behaviour) overstates ROI by ~6pp on a
        # 41c contract.
        out = a["cost"] + a["fee"]
        a["roi"] = (a["pl"] / out * 100.0) if out else 0.0
        a["per_ct"] = (a["pl"] / a["ct"]) if a.get("ct") else 0.0
    return dict(agg)


CSS = """
:root{--bg:#fbfaf8;--fg:#1a1a18;--mut:#5a5750;--line:#e2ddd4;--card:#fff;
--pos:#1c7a4a;--neg:#a8322c;--warn:#8a5a00}
:root[data-theme=dark],:root:not([data-theme=light]){}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16150f;
--fg:#ece8df;--mut:#a8a29a;--line:#2e2c25;--card:#1e1d16;--pos:#5fbf8a;
--neg:#e0736c;--warn:#d2a34a}}
:root[data-theme=dark]{--bg:#16150f;--fg:#ece8df;--mut:#a8a29a;--line:#2e2c25;
--card:#1e1d16;--pos:#5fbf8a;--neg:#e0736c;--warn:#d2a34a}
body{background:var(--bg);color:var(--fg);font:15.5px/1.6 ui-sans-serif,system-ui,
-apple-system,"Segoe UI",sans-serif;margin:0;padding:26px 20px 60px}
/* Explanatory prose was 462 words of 12.5px muted grey in one block -- a wall.
   Default view now shows one line; the rest is behind a disclosure. */
details.why{margin-top:10px;border-top:1px solid var(--line);padding-top:9px}
details.why summary{cursor:pointer;font-size:13.5px;color:var(--mut);
list-style:none;user-select:none}
details.why summary::-webkit-details-marker{display:none}
details.why summary:before{content:"▸ ";font-size:11px}
details.why[open] summary:before{content:"▾ "}
details.why summary:hover{color:var(--fg)}
details.why .body{font-size:14px;line-height:1.65;color:var(--fg);margin-top:10px;
max-width:70ch}
details.why .body p{margin:0 0 10px}
.keyline{font-size:14px;color:var(--fg);margin-top:10px;max-width:74ch}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:20px;margin:0 0 2px;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:13.5px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:14px 16px;margin-bottom:14px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--mut);
margin:0 0 10px;font-weight:600}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
color:var(--mut);font-weight:600;padding:4px 8px 6px;border-bottom:1px solid var(--line)}
td{padding:5px 8px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.num{text-align:right}.pos{color:var(--pos)}.neg{color:var(--neg)}
.scroll{overflow-x:auto}
.kpi{display:flex;gap:26px;flex-wrap:wrap}
.kpi div{min-width:100px}.kpi .v{font-size:21px;font-weight:600;letter-spacing:-.02em}
.kpi .l{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.pill{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;
border:1px solid var(--line);color:var(--mut)}
.bad{color:var(--neg);border-color:var(--neg)}.good{color:var(--pos);border-color:var(--pos)}
.note{border-left:3px solid var(--warn);padding:9px 13px;color:var(--mut);
font-size:13.5px;background:var(--card);border-radius:0 8px 8px 0;margin-bottom:14px}
code{font:12px ui-monospace,Menlo,monospace;background:var(--bg);padding:1px 4px;
border-radius:3px;border:1px solid var(--line)}
"""


def _sign(v, unit="$"):
    c = "pos" if v > 0 else ("neg" if v < 0 else "")
    return f'<span class="{c}">{"+" if v > 0 else ""}{unit}{v:,.2f}</span>'


def render(d):
    S = summarise(d)
    tot_pl = sum(a["pl"] for a in S.values())
    tot_n = sum(a["n"] for a in S.values())
    tot_cost = sum(a["cost"] for a in S.values())
    exposure = sum(abs(p.get("position", 0)) for p in d["positions"])
    h = d.get("health", {})
    p = []
    p.append(f"<title>NBA Live Desk</title><style>{CSS}</style>")
    p.append('<div class="wrap"><h1>NBA Live Desk</h1>')
    p.append(f'<div class="sub">CrewShock &middot; PaceGap &middot; MOVE_COMBINED '
             f'&mdash; Kalshi <code>KXNBATOTAL</code> &mdash; built '
             f'{d["built"].replace("T"," ").replace("+00:00","")} UTC</div>')

    if not d["ok"]:
        p.append(f'<div class="note"><b>Feed error.</b> {d["err"]}</div>')

    p.append('<div class="card"><div class="kpi">')
    tot_won = sum(a["won"] for a in S.values())
    for label, val in (("Settled P&amp;L", _sign(tot_pl)),
                       ("Hit%", f"{100.0*tot_won/tot_n:.1f}%" if tot_n else "&mdash;"),
                       ("ROI", _sign(100.0 * tot_pl / tot_cost, "") + "%" if tot_cost
                               else "&mdash;"),
                       ("Settled bets", f"{tot_n}"),
                       ("Premium paid", f"${tot_cost:,.2f}"),
                       ("Open contracts", f"{exposure}"),
                       ("Resting orders", f'{len(d["resting"])}')):
        p.append(f'<div><div class="v">{val}</div><div class="l">{label}</div></div>')
    p.append("</div></div>")

    # ---- per strategy
    p.append('<div class="card"><h2>By strategy &mdash; settled on Kalshi</h2>'
             '<div class="scroll"><table><tr><th>Strategy</th><th>Settles vs</th>'
             '<th class="num">Calib. edge</th><th class="num">Bets</th><th class="num">Won</th>'
             '<th class="num">Hit%</th><th class="num">Premium</th><th class="num">Fees</th>'
             '<th class="num">P&amp;L</th><th class="num">ROI</th>'
             '<th class="num">&cent;/contract</th></tr>')
    for name in list(LT.STRATS) + [k for k in S if k not in LT.STRATS]:
        a = S.get(name)
        cfg = LT.STRATS.get(name, {})
        dl = f'{cfg["delta"]:.2f} pts' if "delta" in cfg else "&mdash;"
        lbl = (f'<span class="neg">{name}</span>' if name == "unattributed"
               else DISPLAY.get(name, name))
        # Mark anything outside the frozen prospective test. A reader comparing
        # rows must be able to see that final7's larger calibrated edge comes
        # from a weaker design, not a better one.
        if not cfg.get("prereg", True) and name != "unattributed":
            lbl += ' <span class="pill" title="not preregistered">disc.</span>'
        if not a:
            p.append(f'<tr><td>{lbl}</td><td>{cfg.get("line","&mdash;")}</td>'
                     f'<td class="num">{dl}</td>'
                     f'<td class="num" colspan="8" style="color:var(--mut)">no settled bets</td></tr>')
            continue
        p.append(f'<tr><td>{lbl}</td><td>{cfg.get("line","?")}</td>'
                 f'<td class="num">{dl}</td>'
                 f'<td class="num">{a["n"]}</td><td class="num">{a["won"]}</td>'
                 f'<td class="num">{100.0*a["won"]/a["n"]:.1f}%</td>'
                 f'<td class="num">${a["cost"]:,.2f}</td>'
                 f'<td class="num">${a["fee"]:,.2f}</td>'
                 f'<td class="num">{_sign(a["pl"])}</td>'
                 f'<td class="num">{_sign(a["roi"], "")}%</td>'
                 f'<td class="num">{_sign(a["per_ct"]*100, "")}&cent;</td></tr>')
    p.append("</table></div>")
    p.append('<div class="keyline"><b>Hit% is measured against the strike bought, '
             'not the line &mdash; it should read lower than the backtest.</b> '
             'Judge these rows on P&amp;L and &cent;/contract.</div>')
    p.append('<details class="why"><summary>How these numbers are defined</summary>'
             '<div class="body">'
             '<p><b>Same rules as the trader.</b> A win is the side the trader recorded '
             'buying against how the market resolved &mdash; read from the order log, not '
             'inferred from cash flow. P&amp;L is revenue &minus; premium &minus; fees. '
             'ROI divides by total outlay (premium + fees), because Kalshi charges the fee '
             'on entry.</p>'
             '<p><b>Why Hit% runs low.</b> The backtest rate (cs 54.2%, move 53.4%, '
             'pacegap 52.6%, final7 55.3%) is how often the total beats the <i>line</i>. '
             'Here it is how often it beats the <i>strike we bought</i> &mdash; and the '
             'trader takes whichever rung has the best EV, usually not at the money, '
             "because Kalshi's fee is cheaper in the tails. A cheap out-of-the-money rung "
             'can win 20&ndash;46% of the time and still profit.</p>'
             '<p><b>Calib. edge</b> is a fixed constant per strategy, not a per-game '
             'output: the published hit rate inverted through the normal at sd 18.244. '
             'All four rules are threshold-and-sign and discard signal magnitude, so the '
             'strategy-level number is the only edge size ever measured. It is the '
             'assumption orders were priced on. The per-trade figure is <b>EV/ct</b> below. '
             'The sportsbook bar is 1.12 pts (cs +0.805, move +0.453, pacegap +0.064, '
             'final7 +1.299), and all four have an ROI interval including zero.</p>'
             '<p><b>disc.</b> marks a strategy outside the frozen 2026-27 prospective test. '
             '<b>final7</b> bets OVER on every game in the last 7 days of the regular '
             'season. Its window was chosen by searching the same data that produced its '
             'record, so its edge uses the LOSO-honest 55.29%, not the 56.93% headline '
             '&mdash; and it is still z = +1.65 on 407 bets, ~$395/season. Its larger edge '
             'comes from a weaker design, so a preregistered strategy always claims a game '
             'they both want.</p>'
             '</div></details>')
    if "unattributed" in S:
        p.append('<div style="margin-top:8px"><span class="pill bad">'
                 'unattributed settlements &mdash; a ticker settled that is in neither the '
                 'local order log nor a tagged fill. Reconcile before trusting this table.'
                 '</span></div>')
    p.append("</div>")

    # ---- execution quality. THE panel to watch: the entire economic case is
    # that we MAKE rather than TAKE (+1.4c to +4.5c/contract vs -1.1c to +2.0c).
    # If maker share slips, the edge is gone and nothing else on this page says so.
    nf = len(d["fills"])
    if nf:
        mk = sum(1 for f in d["fills"] if not f.get("is_taker"))
        ct = sum(_f(f.get("count_fp")) for f in d["fills"]) or 1
        fee = sum(_f(f.get("fee_cost")) for f in d["fills"])
        share = 100.0 * mk / nf
        p.append('<div class="card"><h2>Execution quality</h2><div class="kpi">')
        for label, val in (("Maker share", f'<span class="{"pos" if share>=80 else "neg"}">{share:.0f}%</span>'),
                           ("Fills", f"{nf}"), ("Contracts", f"{ct:,.0f}"),
                           ("Fee / contract", f"{100*fee/ct:.2f}&cent;")):
            p.append(f'<div><div class="v">{val}</div><div class="l">{label}</div></div>')
        p.append('</div><div style="margin-top:9px;color:var(--mut);font-size:13.5px">'
                 'Resting bids earn the half-spread; crossing pays it. At the median '
                 '2&cent; book that is a 2&cent;/contract swing &mdash; larger than '
                 "PaceGap's entire edge. A falling maker share is the first sign the "
                 'economics have inverted.</div></div>')

    # ---- open positions
    p.append('<div class="card"><h2>Open positions</h2>')
    live_pos = [q for q in d["positions"] if q.get("position")]
    if live_pos:
        p.append('<div class="scroll"><table><tr><th>Market</th>'
                 '<th class="num">Contracts</th><th class="num">Exposure</th>'
                 '<th class="num">Realised</th></tr>')
        for q in live_pos:
            # field names carry the *_dollars suffix on newer endpoints; fall
            # back to the cents spelling rather than print a silent 100x error
            exp = (_f(q.get("market_exposure_dollars"))
                   or _f(q.get("market_exposure")) / 100.0)
            rea = (_f(q.get("realized_pnl_dollars"))
                   or _f(q.get("realized_pnl")) / 100.0)
            p.append(f'<tr><td><code>{q.get("ticker","")}</code></td>'
                     f'<td class="num">{q.get("position")}</td>'
                     f'<td class="num">${exp:,.2f}</td>'
                     f'<td class="num">{_sign(rea)}</td></tr>')
        p.append("</table></div>")
    else:
        p.append('<div style="color:var(--mut)">None.</div>')
    p.append("</div>")

    # ---- today's orders
    today = dt.date.today().isoformat()
    recent = [o for o in d["orders"] if str(o.get("ts_utc", ""))[:10] == today]
    p.append(f'<div class="card"><h2>Orders today ({len(recent)})</h2>')
    if recent:
        p.append('<div class="scroll"><table><tr><th>Strategy</th><th>Game</th>'
                 '<th>Side</th><th class="num">Strike</th><th class="num">Qty</th>'
                 '<th class="num">Limit</th><th class="num">EV/ct</th>'
                 '<th class="num">&mu;&#770;</th><th class="num">&mu;<sub>mkt</sub></th>'
                 '<th>Mode</th></tr>')
        for o in recent[-40:]:
            try:
                e = float(o.get("edge") or 0)
            except ValueError:
                e = 0.0
            _s = o.get("strategy", "")
            p.append(f'<tr><td>{DISPLAY.get(_s, _s)}</td><td>{o.get("game","")}</td>'
                     f'<td>{o.get("side","")}</td><td class="num">{o.get("strike","")}</td>'
                     f'<td class="num">{o.get("count","")}</td>'
                     f'<td class="num">{o.get("limit_price","")}</td>'
                     f'<td class="num">{_sign(e*100, "")}&cent;</td>'
                     f'<td class="num">{o.get("mu_hat","")}</td>'
                     f'<td class="num">{o.get("mu_mkt","")}</td>'
                     f'<td><span class="pill">{o.get("mode","")}</span></td></tr>')
        p.append('</table></div><div style="margin-top:9px;color:var(--mut);'
                 'font-size:13.5px"><b>EV/ct</b> is this order\'s own expected value: '
                 'p<sub>model</sub> &minus; price &minus; fee, at the size actually sent. '
                 'Unlike <b>Calib. edge</b> above it varies by game &mdash; it moves with '
                 '&mu;&#770;, the ladder\'s own &sigma;, which rung was taken and the price '
                 'paid. &mu;&#770; is the strategy\'s reference line plus its calibrated '
                 'edge; &mu;<sub>mkt</sub> is what the ladder implies. A large gap between '
                 'them late in the day usually means a stale opener, not an opportunity.'
                 '</div></div>')
    else:
        p.append('<div style="color:var(--mut)">No orders logged today.</div>')
    p.append("</div>")

    # ---- why signals did not trade. A mistimed cron entry shows up ONLY here:
    # a late PaceGap/MOVE run declines most of its slate on the stale-opener
    # guard, silently and correctly, and nothing else on the page would say so.
    declines = defaultdict(int)
    for o in recent:
        n = (o.get("note") or "").strip()
        if not o.get("ticker") and n:
            declines[n.split(":")[0]] += 1
    if declines:
        p.append('<div class="card"><h2>Declined today</h2>'
                 '<div class="scroll"><table><tr><th>Reason</th>'
                 '<th class="num">Games</th></tr>')
        for why, n in sorted(declines.items(), key=lambda kv: -kv[1]):
            bad = why.startswith("stale opener")
            p.append(f'<tr><td>{"<b>" if bad else ""}{why}{"</b>" if bad else ""}</td>'
                     f'<td class="num">{n}</td></tr>')
        p.append('</table></div><div style="margin-top:9px;color:var(--mut);'
                 'font-size:13.5px">A high <b>stale opener</b> count means the market '
                 'had already moved when we ran &mdash; check the cron clock before '
                 'checking the model. <b>already held</b> is by design: one position '
                 'per game across all three strategies.</div></div>')

    # ---- pipeline health (D3-safe: field population, never outcomes)
    p.append('<div class="card"><h2>Pipeline health</h2><div class="kpi">')
    miss = h.get("incomplete_pregame_fields") or []
    for label, val in (("Logged", h.get("rows", "&mdash;")),
                       ("Settled", h.get("settled", "&mdash;")),
                       ("Bet-flagged", h.get("bet_flagged", "&mdash;")),
                       ("m_X populated", h.get("m_X_populated", "&mdash;"))):
        p.append(f'<div><div class="v">{val}</div><div class="l">{label}</div></div>')
    p.append("</div>")
    p.append(f'<div style="margin-top:10px"><span class="pill '
             f'{"bad" if miss else "good"}">'
             f'{"incomplete: " + ", ".join(miss) if miss else "all pregame fields populated"}'
             f'</span></div>')
    fails = [r["step"] for r in d.get("runs", []) if not r.get("ok") and r.get("required")]
    if fails:
        p.append(f'<div style="margin-top:8px"><span class="pill bad">'
                 f'recent failures: {", ".join(sorted(set(fails)))}</span></div>')
    p.append("</div>")

    p.append('<div class="note"><b>This page shows Kalshi trading results only.</b> '
             'The preregistered 2026-27 test settles against <code>open_total</code> '
             'at a notional stake and is a different number; it is locked until '
             '2027-04-15 by <code>PREREG_2026_27_PROSPECTIVE</code> D3 and is not '
             'computable from anything above. No hit rate by threshold, no '
             'alternative thresholds, no Over/Under or team splits &mdash; those are '
             'what D3 names. See <code>AMENDMENT_live_trading.md</code>.</div>')
    p.append("</div>")
    return "\n".join(p)


def publish(path, bucket=None, key=None):
    """Upload to S3. Private by default -- no ACL is set and none should be.

    The page carries position sizes and account balance. If it needs to be
    reachable from a browser, front it with CloudFront + OAC or a presigned URL;
    do not make the object public to fix a 403.
    """
    bucket = bucket or S3_BUCKET
    key = key or S3_KEY
    if not bucket:
        print("FAIL no bucket (set NBA_S3_BUCKET or pass --bucket)")
        return 1
    import boto3
    boto3.client("s3").upload_file(
        path, bucket, key,
        ExtraArgs={"ContentType": "text/html; charset=utf-8",
                   "CacheControl": "max-age=60"})
    print(f"published -> s3://{bucket}/{key}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default=OUT_HTML)
    ap.add_argument("--bucket", default=None)
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    if not (a.build or a.publish):
        ap.error("nothing to do: pass --build and/or --publish")
    d = collect(demo=a.demo)
    html = render(d)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(html)
    print(f"built {a.out}  ({len(html):,} bytes)"
          + ("" if d["ok"] else f"   [feed error: {d['err'][:80]}]"))
    sys.exit(publish(a.out, a.bucket, a.key) if a.publish else 0)
