#!/usr/bin/env python3
"""
$10,000 AI Macro Portfolio Tracker
Run anytime: python portfolio_tracker.py
Shows live prices, P&L, zone status, and alerts for all 25 positions.
"""

import sys
from datetime import datetime
from typing import Optional

try:
    import yfinance as yf
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.text import Text
    from rich import box
except ImportError:
    print("Run: pip install yfinance rich")
    sys.exit(1)

console = Console(width=160)

# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO DEFINITION  (edit these if positions change)
# ─────────────────────────────────────────────────────────────────────────────

CASH = 500.00

PORTFOLIO = [
    # ── TIER 1 · HOLD FOREVER · No sell points ───────────────────────────────
    dict(
        tier=1, n=1, symbol="CEG", theme="AI Power · Nuclear",
        cost_basis=267.21, shares=3.0,  allocated=800,
        buy_lo=240,  buy_hi=270,  add_at=245,
        sell_1=None, sell_2=None, stop=None,
        target_3y=550, target_5y=900,
        catalyst="Nuclear PPAs + data center offtake contracts",
    ),
    dict(
        tier=1, n=2, symbol="VEEV", theme="Biotech SaaS · L4",
        cost_basis=154.87, shares=4.5, allocated=700,
        buy_lo=148,  buy_hi=165,  add_at=140,
        sell_1=None, sell_2=None, stop=None,
        target_3y=300, target_5y=450,
        catalyst="Vault CRM monopoly in life sciences",
    ),
    dict(
        tier=1, n=3, symbol="DHR", theme="Biotech Instruments · L3",
        cost_basis=177.87, shares=3.9, allocated=700,
        buy_lo=160,  buy_hi=185,  add_at=160,
        sell_1=None, sell_2=None, stop=None,
        target_3y=310, target_5y=420,
        catalyst="Lab instrument supercycle + bioprocessing",
    ),
    dict(
        tier=1, n=4, symbol="ISRG", theme="Physical AI · Surgical",
        cost_basis=402.18, shares=1.5, allocated=600,
        buy_lo=396,  buy_hi=420,  add_at=380,
        sell_1=None, sell_2=None, stop=None,
        target_3y=700, target_5y=1000,
        catalyst="da Vinci 5 adoption + procedure volume +15%/yr",
    ),
    dict(
        tier=1, n=5, symbol="IBM", theme="Sovereign AI · Quantum",
        cost_basis=262.38, shares=2.3, allocated=600,
        buy_lo=240,  buy_hi=275,  add_at=230,
        sell_1=None, sell_2=None, stop=None,
        target_3y=400, target_5y=550,
        catalyst="Quantum advantage + enterprise AI consulting",
    ),
    dict(
        tier=1, n=6, symbol="MSFT", theme="Quantum · AI Agents · L4/5",
        cost_basis=378.85, shares=1.6, allocated=600,
        buy_lo=363,  buy_hi=395,  add_at=355,
        sell_1=None, sell_2=None, stop=None,
        target_3y=600, target_5y=800,
        catalyst="Azure AI + Copilot enterprise + quantum cloud",
    ),

    # ── TIER 2 · SET PRICE TARGETS ────────────────────────────────────────────
    dict(
        tier=2, n=7, symbol="REGN", theme="Biotech · L6",
        cost_basis=607.73, shares=0.8, allocated=500,
        buy_lo=580,  buy_hi=625,  add_at=560,
        sell_1=820,  sell_2=1000, stop=520,
        target_3y=900, target_5y=None,
        catalyst="Dupixent expansion + obesity pipeline",
    ),
    dict(
        tier=2, n=8, symbol="TMO", theme="Biotech Infrastructure · L3",
        cost_basis=461.70, shares=1.1, allocated=500,
        buy_lo=440,  buy_hi=475,  add_at=420,
        sell_1=650,  sell_2=800,  stop=390,
        target_3y=720, target_5y=None,
        catalyst="GLP-1 manufacturing + cell therapy buildout",
    ),
    dict(
        tier=2, n=9, symbol="BAH", theme="Sovereign AI · L5",
        cost_basis=71.10, shares=5.6, allocated=400,
        buy_lo=68,   buy_hi=75,   add_at=68,
        sell_1=110,  sell_2=140,  stop=60,
        target_3y=130, target_5y=None,
        catalyst="DoD AI contracts + JADC2 modernization",
    ),
    dict(
        tier=2, n=10, symbol="ACN", theme="Sovereign AI · L5/6",
        cost_basis=156.19, shares=2.6, allocated=400,
        buy_lo=155,  buy_hi=165,  add_at=148,
        sell_1=230,  sell_2=290,  stop=135,
        target_3y=270, target_5y=None,
        catalyst="AI consulting monopoly + government IT modernization",
    ),
    dict(
        tier=2, n=11, symbol="LDOS", theme="Sovereign AI · L5",
        cost_basis=108.72, shares=3.7, allocated=400,
        buy_lo=108,  buy_hi=115,  add_at=100,
        sell_1=165,  sell_2=200,  stop=90,
        target_3y=190, target_5y=None,
        catalyst="$15B+ DoD AI/IT backlog",
    ),
    dict(
        tier=2, n=12, symbol="ILMN", theme="Biotech · L2",
        cost_basis=159.03, shares=2.5, allocated=400,
        buy_lo=150,  buy_hi=168,  add_at=140,
        sell_1=240,  sell_2=300,  stop=130,
        target_3y=280, target_5y=None,
        catalyst="Cancer genomics + GRAIL spinoff clarity",
    ),
    dict(
        tier=2, n=13, symbol="VST", theme="AI Power · Nuclear/Gas",
        cost_basis=158.81, shares=2.5, allocated=400,
        buy_lo=150,  buy_hi=165,  add_at=145,
        sell_1=220,  sell_2=280,  stop=130,
        target_3y=260, target_5y=None,
        catalyst="Data center power contracts + nuclear fleet",
    ),
    dict(
        tier=2, n=14, symbol="CCJ", theme="AI Power · Uranium",
        cost_basis=105.64, shares=2.8, allocated=300,
        buy_lo=100,  buy_hi=112,  add_at=95,
        sell_1=160,  sell_2=200,  stop=85,
        target_3y=190, target_5y=None,
        catalyst="Uranium supply deficit + nuclear renaissance",
    ),
    dict(
        tier=2, n=15, symbol="CRWD", theme="Sovereign Security · L4",
        cost_basis=682.70, shares=0.4, allocated=300,
        buy_lo=660,  buy_hi=700,  add_at=630,
        sell_1=900,  sell_2=1100, stop=580,
        target_3y=1000, target_5y=None,
        catalyst="AI-native cybersecurity platform monopoly",
    ),
    dict(
        tier=2, n=16, symbol="CSCO", theme="Sovereign Networking · L3/6",
        cost_basis=117.41, shares=2.6, allocated=300,
        buy_lo=112,  buy_hi=122,  add_at=108,
        sell_1=160,  sell_2=190,  stop=98,
        target_3y=175, target_5y=None,
        catalyst="AI data center networking + SASE security",
    ),

    # ── TIER 3 · TACTICAL ─────────────────────────────────────────────────────
    dict(
        tier=3, n=17, symbol="MRNA", theme="Biotech · mRNA · L5",
        cost_basis=61.78, shares=4.9, allocated=300,
        buy_lo=58,   buy_hi=65,   add_at=None,
        sell_1=110,  sell_2=None, stop=45,
        target_3y=120, target_5y=None,
        catalyst="Cancer vaccine Phase 3 data 2026–2027",
    ),
    dict(
        tier=3, n=18, symbol="FANUY", theme="Physical AI · Robots · L3",
        cost_basis=23.19, shares=12.9, allocated=300,
        buy_lo=21,   buy_hi=25,   add_at=None,
        sell_1=38,   sell_2=None, stop=18,
        target_3y=45, target_5y=None,
        catalyst="Humanoid robot factory order wave",
    ),
    dict(
        tier=3, n=19, symbol="EMR", theme="Physical AI · Automation · L3",
        cost_basis=149.00, shares=2.0, allocated=300,
        buy_lo=145,  buy_hi=155,  add_at=None,
        sell_1=210,  sell_2=None, stop=125,
        target_3y=220, target_5y=None,
        catalyst="Process automation + robot factory orders",
    ),
    dict(
        tier=3, n=20, symbol="ICLR", theme="Biotech CRO · L4",
        cost_basis=143.23, shares=2.1, allocated=300,
        buy_lo=138,  buy_hi=150,  add_at=None,
        sell_1=220,  sell_2=None, stop=115,
        target_3y=230, target_5y=None,
        catalyst="CRO backlog expansion + GLP-1 trials",
    ),
    dict(
        tier=3, n=21, symbol="QCOM", theme="AI+Physical AI · L1",
        cost_basis=212.98, shares=1.4, allocated=300,
        buy_lo=205,  buy_hi=220,  add_at=None,
        sell_1=300,  sell_2=None, stop=175,
        target_3y=310, target_5y=None,
        catalyst="Edge AI design wins in robotics + auto",
    ),

    # ── TIER 4 · SPECULATIVE ──────────────────────────────────────────────────
    dict(
        tier=4, n=22, symbol="IONQ", theme="Quantum · L1",
        cost_basis=54.72, shares=5.5, allocated=300,
        buy_lo=48,   buy_hi=58,   add_at=None,
        sell_1=120,  sell_2=None, stop=30,
        target_3y=120, target_5y=None,
        catalyst="DoD quantum contracts + error correction milestone",
    ),
    dict(
        tier=4, n=23, symbol="CRSP", theme="Biotech · Gene Editing · L5",
        cost_basis=53.11, shares=5.7, allocated=300,
        buy_lo=48,   buy_hi=56,   add_at=None,
        sell_1=100,  sell_2=None, stop=35,
        target_3y=100, target_5y=None,
        catalyst="Casgevy commercial launch + next indication",
    ),
    dict(
        tier=4, n=24, symbol="BWXT", theme="AI Power · SMR",
        cost_basis=203.04, shares=1.0, allocated=200,
        buy_lo=195,  buy_hi=210,  add_at=None,
        sell_1=320,  sell_2=None, stop=155,
        target_3y=320, target_5y=None,
        catalyst="Naval reactor → commercial SMR pivot",
    ),
    dict(
        tier=4, n=25, symbol="GFS", theme="Sovereign Foundry · L1",
        cost_basis=80.63, shares=2.5, allocated=200,
        buy_lo=76,   buy_hi=85,   add_at=None,
        sell_1=130,  sell_2=None, stop=60,
        target_3y=130, target_5y=None,
        catalyst="CHIPS Act + US sovereign semiconductor capacity",
    ),
]

TIER_LABELS = {
    1: ("TIER 1", "HOLD FOREVER",       "cyan",    "$4,000"),
    2: ("TIER 2", "TAKE PROFITS",       "green",   "$3,500"),
    3: ("TIER 3", "TACTICAL",           "yellow",  "$1,500"),
    4: ("TIER 4", "SPECULATIVE",        "red",     "$1,000"),
}

# ─────────────────────────────────────────────────────────────────────────────
# PRICE FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def fetch_prices(symbols: list[str]) -> dict[str, Optional[float]]:
    prices = {}
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                prices[sym] = round(float(info.last_price), 2)
            except Exception:
                try:
                    hist = yf.Ticker(sym).history(period="1d")
                    prices[sym] = round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else None
                except Exception:
                    prices[sym] = None
    except Exception:
        for sym in symbols:
            prices[sym] = None
    return prices

# ─────────────────────────────────────────────────────────────────────────────
# ZONE CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

def zone_status(price: Optional[float], p: dict) -> tuple[str, str]:
    """Returns (label, color) describing where price sits relative to zones."""
    if price is None:
        return "NO DATA", "dim"

    lo, hi = p["buy_lo"], p["buy_hi"]
    stop = p.get("stop")
    sell_1 = p.get("sell_1")

    if stop and price <= stop:
        return "🔴 AT STOP", "bold red"
    if stop and price <= stop * 1.05:
        return "⚠️ NEAR STOP", "red"
    if price < lo:
        pct = (lo - price) / lo * 100
        return f"↓ BELOW ZONE ({pct:.0f}% to lo)", "yellow"
    if lo <= price <= hi:
        return "✅ IN BUY ZONE", "bold green"
    if sell_1 and price >= sell_1:
        return f"🎯 HIT SELL 1 (${sell_1})", "bold magenta"
    if sell_1 and price >= sell_1 * 0.92:
        return f"→ NEAR SELL 1", "magenta"
    pct = (price - hi) / hi * 100
    return f"↑ ABOVE ZONE (+{pct:.0f}%)", "white"


def action_signal(price: Optional[float], p: dict) -> tuple[str, str]:
    if price is None:
        return "—", "dim"
    stop = p.get("stop")
    sell_1 = p.get("sell_1")
    add_at = p.get("add_at")
    lo, hi = p["buy_lo"], p["buy_hi"]

    if stop and price <= stop:
        return "SELL / EXIT", "bold red"
    if sell_1 and price >= sell_1:
        return "SELL HALF", "bold magenta"
    if lo <= price <= hi:
        return "BUY / ADD", "bold green"
    if add_at and price <= add_at:
        return "ADD MORE", "bold green"
    if stop and price <= stop * 1.08:
        return "WATCH STOP", "red"
    return "HOLD", "white"

# ─────────────────────────────────────────────────────────────────────────────
# RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def pnl_color(val: float) -> str:
    if val > 0:   return "green"
    if val < 0:   return "red"
    return "white"


def render_tier_table(positions: list[dict], prices: dict, tier: int) -> Table:
    label, subtitle, color, budget = TIER_LABELS[tier]
    is_t2 = (tier == 2)

    t = Table(
        title=f"[bold {color}]{label}[/bold {color}]  [dim]{subtitle} · {budget}[/dim]",
        show_header=True,
        header_style=f"bold {color}",
        border_style="dim",
        box=box.SIMPLE_HEAD,
        pad_edge=False,
    )
    t.add_column("#",        width=3,  justify="right")
    t.add_column("Ticker",   width=7,  style="bold white")
    t.add_column("Theme",    width=22)
    t.add_column("Cost",     width=8,  justify="right")
    t.add_column("Now",      width=8,  justify="right")
    t.add_column("Chg%",     width=7,  justify="right")
    t.add_column("P&L $",    width=9,  justify="right")
    t.add_column("P&L %",    width=7,  justify="right")
    t.add_column("Zone",     width=26)
    t.add_column("Action",   width=12)
    t.add_column("Stop",     width=7,  justify="right")
    if is_t2:
        t.add_column("Sell 1",   width=7,  justify="right")
        t.add_column("Sell 2",   width=7,  justify="right")
        t.add_column("→Sell1%",  width=8,  justify="right")
    t.add_column("3Y Tgt",   width=7,  justify="right")
    t.add_column("Upside",   width=7,  justify="right")

    for p in positions:
        price  = prices.get(p["symbol"])
        cost   = p["cost_basis"]
        shares = p["shares"]

        now_str   = f"${price:.2f}"  if price else "—"
        chg_pct   = (price - cost) / cost * 100 if price else None
        chg_str   = f"{chg_pct:+.1f}%" if chg_pct is not None else "—"
        chg_color = pnl_color(chg_pct or 0)

        pnl_dollar = (price - cost) * shares if price else None
        pnl_pct    = chg_pct

        pnl_d_str  = f"${pnl_dollar:+.0f}" if pnl_dollar is not None else "—"
        pnl_p_str  = f"{pnl_pct:+.1f}%"   if pnl_pct    is not None else "—"
        pl_color   = pnl_color(pnl_dollar or 0)

        zone_lbl, zone_col = zone_status(price, p)
        action_lbl, action_col = action_signal(price, p)

        stop_str = f"${p['stop']}" if p.get("stop") else "None"
        tgt_3y   = f"${p['target_3y']}" if p.get("target_3y") else "—"
        upside   = f"{(p['target_3y'] / cost - 1)*100:.0f}%" if p.get("target_3y") and price else "—"

        row = [
            str(p["n"]),
            p["symbol"],
            p["theme"][:22],
            f"${cost:.2f}",
            now_str,
            f"[{chg_color}]{chg_str}[/{chg_color}]",
            f"[{pl_color}]{pnl_d_str}[/{pl_color}]",
            f"[{pl_color}]{pnl_p_str}[/{pl_color}]",
            f"[{zone_col}]{zone_lbl}[/{zone_col}]",
            f"[{action_col}]{action_lbl}[/{action_col}]",
            stop_str,
        ]

        if is_t2:
            s1 = f"${p['sell_1']}" if p.get("sell_1") else "—"
            s2 = f"${p['sell_2']}" if p.get("sell_2") else "—"
            to_s1 = f"{(p['sell_1']/price - 1)*100:+.0f}%" if price and p.get("sell_1") else "—"
            to_s1_color = "green" if price and p.get("sell_1") and price < p["sell_1"] else "magenta"
            row += [s1, s2, f"[{to_s1_color}]{to_s1}[/{to_s1_color}]"]

        row += [tgt_3y, upside]
        t.add_row(*row)

    return t


def render_summary(positions: list[dict], prices: dict) -> None:
    total_cost  = sum(p["allocated"] for p in positions) + CASH
    total_value = CASH
    total_pnl   = 0.0
    alerts      = []

    for p in positions:
        price = prices.get(p["symbol"])
        if price:
            value     = price * p["shares"]
            pnl       = (price - p["cost_basis"]) * p["shares"]
            total_value += value
            total_pnl   += pnl

            # Collect alerts
            stop = p.get("stop")
            sell_1 = p.get("sell_1")
            lo, hi = p["buy_lo"], p["buy_hi"]

            if stop and price <= stop:
                alerts.append(f"[bold red]🔴 STOP HIT   {p['symbol']:6s} @ ${price:.2f}  (stop ${stop})[/bold red]")
            elif stop and price <= stop * 1.06:
                alerts.append(f"[red]⚠️  NEAR STOP  {p['symbol']:6s} @ ${price:.2f}  (stop ${stop}, -{((price-stop)/stop*100):.0f}% away)[/red]")
            elif sell_1 and price >= sell_1:
                alerts.append(f"[bold magenta]🎯 SELL 1 HIT {p['symbol']:6s} @ ${price:.2f}  (target ${sell_1}) → SELL HALF[/bold magenta]")
            elif sell_1 and price >= sell_1 * 0.92:
                alerts.append(f"[magenta]→  NEAR SELL1  {p['symbol']:6s} @ ${price:.2f}  ({((sell_1/price-1)*100):.0f}% to ${sell_1})[/magenta]")
            elif lo <= price <= hi:
                add_note = f"  add more @ ${p['add_at']}" if p.get("add_at") else ""
                alerts.append(f"[bold green]✅ IN BUY ZONE {p['symbol']:6s} @ ${price:.2f}  (zone ${lo}–${hi}){add_note}[/bold green]")
        else:
            alerts.append(f"[dim]?  NO PRICE    {p['symbol']}[/dim]")

    total_return = (total_value - total_cost) / total_cost * 100
    pnl_color_str = "green" if total_pnl >= 0 else "red"

    # Header summary panel
    now = datetime.now().strftime("%B %d, %Y  %H:%M")
    summary_text = (
        f"[bold white]Portfolio Value:[/bold white]  [bold {'green' if total_value >= total_cost else 'red'}]${total_value:,.2f}[/bold {'green' if total_value >= total_cost else 'red'}]"
        f"   [dim]|[/dim]   "
        f"[bold white]Total P&L:[/bold white]  [{pnl_color_str}]${total_pnl:+,.2f}  ({total_return:+.1f}%)[/{pnl_color_str}]"
        f"   [dim]|[/dim]   "
        f"[bold white]Cash Reserve:[/bold white]  [cyan]${CASH:.0f}[/cyan]"
        f"   [dim]|[/dim]   "
        f"[dim]{now}[/dim]"
    )
    console.print(Panel(summary_text, title="[bold cyan]$10,000 AI MACRO PORTFOLIO[/bold cyan]", border_style="cyan"))

    # Alerts panel
    if alerts:
        alert_text = "\n".join(alerts)
        console.print(Panel(alert_text, title="[bold yellow]⚡ ALERTS & SIGNALS[/bold yellow]", border_style="yellow"))


def render_cash_deploy(prices: dict) -> None:
    deploy_targets = [
        ("CEG",  245, "Add if drops to buy zone low"),
        ("VEEV", 140, "Add if drops to add-more level"),
        ("DHR",  160, "Add if drops to add-more level"),
        ("BAH",  68,  "Add if drops to buy zone low"),
        ("ACN",  148, "Add if drops to add-more level"),
    ]

    t = Table(
        title="[bold cyan]CASH RESERVE · $500 · Deploy On 15%+ Market Selloff[/bold cyan]",
        header_style="bold cyan", border_style="dim", box=box.SIMPLE_HEAD,
    )
    t.add_column("Priority", width=10)
    t.add_column("Ticker",   width=8, style="bold white")
    t.add_column("Deploy At", width=12)
    t.add_column("Current",  width=10, justify="right")
    t.add_column("% to Target", width=13, justify="right")
    t.add_column("Rule",     width=40)

    for i, (sym, target, rule) in enumerate(deploy_targets, 1):
        price = prices.get(sym)
        curr_str = f"${price:.2f}" if price else "—"
        if price:
            pct = (target - price) / price * 100
            pct_str = f"{pct:+.1f}%"
            pct_color = "green" if pct < 0 else "yellow"  # green = already there
        else:
            pct_str, pct_color = "—", "dim"

        t.add_row(
            f"#{i}",
            sym,
            f"${target}",
            curr_str,
            f"[{pct_color}]{pct_str}[/{pct_color}]",
            rule,
        )

    console.print(t)


def render_scenario_table() -> None:
    t = Table(
        title="[bold white]Scenario Returns[/bold white]",
        header_style="bold white", border_style="dim", box=box.SIMPLE_HEAD,
    )
    t.add_column("Scenario",   width=40)
    t.add_column("3yr Value",  width=12, justify="right")
    t.add_column("5yr Value",  width=12, justify="right")
    t.add_column("Return",     width=10, justify="right")
    rows = [
        ("Bear — half targets hit",           "$14,500", "$18,000", "[red]+80%[/red]"),
        ("Base — most targets hit",           "$18,000", "$26,000", "[yellow]+160%[/yellow]"),
        ("Bull — all targets + re-ratings",   "$24,000", "$40,000", "[green]+300%[/green]"),
        ("S&P 500 same period (benchmark)",   "$13,000", "$16,500", "[dim]+65%[/dim]"),
    ]
    for r in rows:
        t.add_row(*r)
    console.print(t)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    symbols = [p["symbol"] for p in PORTFOLIO]

    console.print(Rule("[dim]Fetching live prices...[/dim]"))
    prices = fetch_prices(symbols)

    fetched = sum(1 for v in prices.values() if v is not None)
    console.print(f"[dim]Got prices for {fetched}/{len(symbols)} symbols.[/dim]\n")

    # Summary + alerts first
    render_summary(PORTFOLIO, prices)
    console.print()

    # One table per tier
    for tier in [1, 2, 3, 4]:
        tier_positions = [p for p in PORTFOLIO if p["tier"] == tier]
        console.print(render_tier_table(tier_positions, prices, tier))
        console.print()

    # Cash deployment guide
    render_cash_deploy(prices)
    console.print()

    # Scenario table
    render_scenario_table()
    console.print()

    console.print(Panel(
        "[dim]Rule 1: Never check prices daily — quarterly reviews: Sep 17 · Dec 17 · Mar 17 · Jun 17\n"
        "Rule 2: Market crashes are your best friend — deploy $500 cash into Tier 1 on 15%+ drops\n"
        "Rule 3: Do not add new names — 25 positions is enough. Conviction over diversification.[/dim]",
        title="[dim]THE THREE RULES[/dim]",
        border_style="dim",
    ))


if __name__ == "__main__":
    main()
