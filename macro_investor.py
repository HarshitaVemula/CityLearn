#!/usr/bin/env python3
"""
AI Macro Investor — First-Principles Bottleneck Analysis Tool
Uses Claude claude-opus-4-8 for institutional-grade strategy generation.
Run with: python macro_investor.py --trend ai-power
          python macro_investor.py --trend ai-silicon
          python macro_investor.py --list-trends
          python macro_investor.py --custom "Nuclear SMR buildout" --tickers CEG VST GEV
"""

import os
import sys
import json
import argparse
import math
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.text import Text

console = Console(width=120)

# ─────────────────────────────────────────────────────────────────────────────
# TREND LIBRARY — add any trend here, it gets the full 6-level analysis
# ─────────────────────────────────────────────────────────────────────────────

TRENDS = {
    "ai-power": {
        "name": "AI Power & Energy Infrastructure",
        "description": (
            "The electricity, grid, cooling, and nuclear buildout required to sustain "
            "exponential AI compute demand. Every AI query needs electrons."
        ),
        "tickers": ["VST", "CEG", "GEV", "NRG", "ETN", "PWR", "VRT", "MOD", "MTZ", "FCX"],
        "benchmark": "XLU",
    },
    "ai-silicon": {
        "name": "AI Custom Silicon & ASIC Wave",
        "description": (
            "Custom inference chips, networking silicon, and the wave of hyperscaler-designed "
            "ASICs displacing general-purpose GPUs at the margin."
        ),
        "tickers": ["NVDA", "AVGO", "MRVL", "AMD", "INTC", "QCOM", "ARM", "AMAT"],
        "benchmark": "SOXX",
    },
    "ai-agents": {
        "name": "AI Agents & Enterprise Software Infrastructure",
        "description": (
            "Software orchestration, memory, tool-use, and the enterprise plumbing enabling "
            "autonomous agents to replace human workflows at scale."
        ),
        "tickers": ["PLTR", "NOW", "CRM", "MSFT", "GOOGL", "META", "SNOW", "MDB"],
        "benchmark": "IGV",
    },
    "physical-ai": {
        "name": "Physical AI & Robotics",
        "description": (
            "Humanoid robots, autonomous vehicles, and industrial automation — "
            "the convergence of foundational AI models with the physical world."
        ),
        "tickers": ["TSLA", "ISRG", "HON", "ROK", "NVDA", "BLDP", "PATH", "VIAV"],
        "benchmark": "ROBO",
    },
    "ai-data": {
        "name": "AI Data Infrastructure & Storage",
        "description": (
            "Storage, networking, and data pipeline infrastructure that AI training "
            "and inference workloads consume at scale."
        ),
        "tickers": ["PSTG", "NTAP", "WDC", "STX", "EQIX", "DLR", "CSCO", "ANET"],
        "benchmark": "VGT",
    },
    "copper": {
        "name": "Copper & Critical Minerals Supercycle",
        "description": (
            "Raw materials bottleneck driven by AI infrastructure buildout, "
            "EV adoption, and grid electrification — the picks-and-shovels of picks-and-shovels."
        ),
        "tickers": ["FCX", "SCCO", "TECK", "BHP", "RIO", "VALE", "MP", "LTHM"],
        "benchmark": "COPX",
    },
    "quantum": {
        "name": "Quantum Computing",
        "description": (
            "Early-stage quantum hardware and software — the post-silicon compute wave "
            "with 5–10 year horizon to commercial relevance."
        ),
        "tickers": ["IONQ", "RGTI", "QBTS", "IBM", "GOOGL", "MSFT"],
        "benchmark": "SPY",
    },
    "grid-infra": {
        "name": "Grid Infrastructure & Transmission",
        "description": (
            "Transformers, substations, transmission lines, and the electrical "
            "construction workforce enabling power to reach data centers."
        ),
        "tickers": ["ETN", "PWR", "MTZ", "PRIM", "MYRG", "WESCO", "HUB.B", "HUBB"],
        "benchmark": "GRID",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATORS  (no external TA library required)
# ─────────────────────────────────────────────────────────────────────────────

def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def compute_sma(closes: list[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)


def find_support_resistance(highs: list[float], lows: list[float], current: float) -> dict:
    recent_highs = sorted(highs[-20:], reverse=True)
    recent_lows = sorted(lows[-20:])
    # nearest resistance above current price
    resistances = [h for h in recent_highs if h > current * 1.005]
    supports = [l for l in recent_lows if l < current * 0.995]
    return {
        "resistance_1": round(resistances[0], 2) if resistances else None,
        "resistance_2": round(resistances[2], 2) if len(resistances) > 2 else None,
        "support_1": round(supports[0], 2) if supports else None,
        "support_2": round(supports[2], 2) if len(supports) > 2 else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MARKET DATA FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ticker_data(symbol: str, timeout: int = 15) -> dict:
    try:
        tk = yf.Ticker(symbol)
        try:
            info = tk.info or {}
        except Exception:
            info = {}

        # 6-month weekly history
        try:
            hist = tk.history(period="6mo", interval="1wk", auto_adjust=True)
        except Exception:
            hist = None

        closes = hist["Close"].tolist() if hist is not None and not hist.empty else []
        highs  = hist["High"].tolist()  if hist is not None and not hist.empty else []
        lows   = hist["Low"].tolist()   if hist is not None and not hist.empty else []

        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or (closes[-1] if closes else None)

        # Options — nearest 2 expirations
        options_summary = {}
        try:
            opts = tk.options
            exps = opts[:2] if opts else []
            for exp in exps:
                chain = tk.option_chain(exp)
                calls = chain.calls
                puts  = chain.puts
                # ATM IV approximation
                if current_price and not calls.empty:
                    atm_calls = calls[abs(calls["strike"] - current_price) < current_price * 0.05]
                    atm_puts  = puts[abs(puts["strike"] - current_price) < current_price * 0.05] if not puts.empty else atm_calls
                    avg_call_iv = float(atm_calls["impliedVolatility"].mean()) if not atm_calls.empty else None
                    avg_put_iv  = float(atm_puts["impliedVolatility"].mean())  if not atm_puts.empty  else None
                    total_call_oi = int(calls["openInterest"].sum())
                    total_put_oi  = int(puts["openInterest"].sum())
                    options_summary[exp] = {
                        "avg_call_iv": round(avg_call_iv * 100, 1) if avg_call_iv else None,
                        "avg_put_iv":  round(avg_put_iv  * 100, 1) if avg_put_iv  else None,
                        "call_oi": total_call_oi,
                        "put_oi":  total_put_oi,
                        "put_call_ratio": round(total_put_oi / total_call_oi, 2) if total_call_oi else None,
                    }
        except Exception:
            pass

        sr = find_support_resistance(highs, lows, current_price) if current_price else {}

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2) if current_price else None,
            "market_cap_b": round(info.get("marketCap", 0) / 1e9, 1),
            "pe_ratio": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
            "forward_pe": round(info.get("forwardPE", 0), 1) if info.get("forwardPE") else None,
            "pb_ratio": round(info.get("priceToBook", 0), 1) if info.get("priceToBook") else None,
            "revenue_growth_yoy": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
            "earnings_growth": round(info.get("earningsGrowth", 0) * 100, 1) if info.get("earningsGrowth") else None,
            "gross_margin": round(info.get("grossMargins", 0) * 100, 1) if info.get("grossMargins") else None,
            "52w_high": round(info.get("fiftyTwoWeekHigh", 0), 2),
            "52w_low": round(info.get("fiftyTwoWeekLow", 0), 2),
            "pct_from_52w_high": round(
                (current_price - info.get("fiftyTwoWeekHigh", current_price)) / info.get("fiftyTwoWeekHigh", current_price) * 100, 1
            ) if current_price and info.get("fiftyTwoWeekHigh") else None,
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "short_name": info.get("shortName", symbol),
            "beta": round(info.get("beta", 0), 2) if info.get("beta") else None,
            "dividend_yield": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
            "avg_volume_30d": info.get("averageVolume", None),
            "technicals": {
                "rsi_14": compute_rsi(closes),
                "sma_8w": compute_sma(closes, 8),
                "sma_20w": compute_sma(closes, 20),
                "support_1": sr.get("support_1"),
                "support_2": sr.get("support_2"),
                "resistance_1": sr.get("resistance_1"),
                "resistance_2": sr.get("resistance_2"),
                "weeks_of_data": len(closes),
                "price_change_8w_pct": round(
                    (closes[-1] - closes[-8]) / closes[-8] * 100, 1
                ) if len(closes) >= 8 else None,
                "price_change_26w_pct": round(
                    (closes[-1] - closes[0]) / closes[0] * 100, 1
                ) if len(closes) >= 26 else None,
            },
            "options": options_summary,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI-focused macro investor with 20+ years of experience in technology infrastructure investing. You think in first principles, not Wall Street consensus. Your edge is identifying structural supply constraints BEFORE they become consensus trades.

Your analytical framework:
- Identify bottlenecks created by technological progress
- Map second, third, and fourth-order effects
- Find companies that benefit from scarcity — not just demand
- Distinguish between crowded consensus trades and overlooked structural winners
- Use options market data as a sentiment and positioning intelligence layer
- Provide specific, actionable price levels backed by technical analysis

You write with conviction. You name names. You give specific entry prices, stop levels, and targets. You explain WHY each level is important using the data provided. You are never vague.

Output format: Use clear markdown headers. Be specific. Be contrarian where the data supports it. Go 6 levels deep on the bottleneck map."""


def build_analysis_prompt(trend: dict, market_data: list[dict], today: str) -> str:
    data_json = json.dumps(market_data, indent=2)

    return f"""Today is {today}. Analyze the following AI technology trend using first-principles macro investing.

## TREND
Name: {trend['name']}
Description: {trend['description']}

## LIVE MARKET DATA (real-time from yfinance)
{data_json}

## YOUR TASK

Perform a complete macro investment analysis with the following structure. Go 6 LEVELS DEEP on the bottleneck map. Be specific with prices — use the live data above.

---

### 1. THESIS
One paragraph. State the core macro thesis. Name the primary trend, the key scarcity, and why the market is mispricing it.

---

### 2. GROWTH ESTIMATES
Estimate the trend's growth over 1, 3, and 5 years. Back it with logic, not consensus numbers.

---

### 3. BOTTLENECK MAP — 6 LEVELS DEEP
For each level:
- What becomes scarce?
- What is the lead time to add supply?
- Who benefits most?
- Is this level crowded or overlooked?

Format:
#### Level 1: [Primary Trend] → [Resource that becomes scarce]
#### Level 2: [First Bottleneck] → [Second resource that becomes scarce]
...continue through Level 6

---

### 4. WINNERS
For each bottleneck level, list 2-3 public companies. For each:
- Why they win
- Revenue exposure to this bottleneck
- Competitive moat
- Current valuation assessment (use the live PE, P/B data)
- Capacity constraints

---

### 5. CROWDED CONSENSUS TRADES & WHY THEY UNDERPERFORM
Name 3-5 specific positions that Wall Street consensus loves. Explain exactly why each may underperform from current levels. Use the live price data and valuation metrics.

---

### 6. OPTIONS MARKET INTELLIGENCE
For each ticker with options data, analyze:
- Implied volatility level and what it signals
- Put-call ratio and skew interpretation
- Open interest concentration and what smart money is positioning for
- Whether IV is elevated or compressed relative to the price action
- Your read on whether the options market is right or wrong

---

### 7. HIGHEST CONVICTION POSITIONS
For the top 4-5 ideas, provide a complete trade profile:

**[TICKER] — [COMPANY NAME]**
- **Entry:** Specific price zone with reasoning
- **Thesis:** Why this specifically, right now
- **Time horizon:** Tactical (1-6mo) or Strategic (6-18mo) or both
- **Upside targets:** Target 1, Target 2, Target 3 with price levels
- **Stop loss:** Exact level and what it means if hit
- **Max gain / Max loss:** In percentage terms
- **Probability-weighted return:** Your honest estimate
- **Risk/Reward ratio:** Numerical
- **Technical setup:** RSI reading, SMA position, key levels (use the live technicals data)
- **Downside if thesis wrong:** Specific risks and how bad it gets
- **Position sizing:** As % of an AI infrastructure portfolio

---

### 8. RISKS
List 5-7 specific risks. For each: probability (Low/Medium/High), impact (Low/Medium/High), which positions it affects, and how you'd know the risk is materializing.

---

### 9. UPSIDE vs DOWNSIDE SCENARIOS
For the overall thesis:
- Bull case (25% probability): What happens and what returns look like
- Base case (50% probability): What happens and what returns look like
- Bear case (25% probability): What happens and what returns look like

---

### 10. SUMMARY TABLE
Create a markdown table with: Ticker | Price | Entry Zone | Stop | Target 1 | Target 2 | R/R | RSI | Conviction (1-5 stars) | Time Horizon

---

Be contrarian where the data supports it. Call out overpriced consensus trades. Surface overlooked structural winners. Use every data point in the live market data above."""


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def print_market_data_table(market_data: list[dict]) -> None:
    table = Table(title="Live Market Data", show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Ticker", style="bold white", width=8)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Mkt Cap", justify="right", width=10)
    table.add_column("PE", justify="right", width=8)
    table.add_column("Fwd PE", justify="right", width=8)
    table.add_column("52W Hi", justify="right", width=10)
    table.add_column("52W Lo", justify="right", width=10)
    table.add_column("% from Hi", justify="right", width=10)
    table.add_column("RSI", justify="right", width=6)
    table.add_column("8W Chg%", justify="right", width=9)
    table.add_column("26W Chg%", justify="right", width=9)

    for d in market_data:
        if "error" in d:
            table.add_row(d["symbol"], "[red]ERR[/red]", *["—"] * 9)
            continue

        price = f"${d['current_price']:.2f}" if d.get("current_price") else "—"
        mktcap = f"${d['market_cap_b']:.0f}B" if d.get("market_cap_b") else "—"
        pe = str(d["pe_ratio"]) if d.get("pe_ratio") else "—"
        fpe = str(d["forward_pe"]) if d.get("forward_pe") else "—"
        hi = f"${d['52w_high']}" if d.get("52w_high") else "—"
        lo = f"${d['52w_low']}" if d.get("52w_low") else "—"

        pct_hi = d.get("pct_from_52w_high")
        pct_hi_str = f"{pct_hi:.1f}%" if pct_hi is not None else "—"
        pct_hi_color = "green" if pct_hi and pct_hi > -5 else ("yellow" if pct_hi and pct_hi > -15 else "red")

        tech = d.get("technicals", {})
        rsi = tech.get("rsi_14")
        rsi_str = str(rsi) if rsi else "—"
        rsi_color = "green" if rsi and rsi < 40 else ("yellow" if rsi and rsi < 60 else "red")

        chg8 = tech.get("price_change_8w_pct")
        chg8_str = f"{chg8:+.1f}%" if chg8 is not None else "—"
        chg8_color = "green" if chg8 and chg8 > 0 else "red"

        chg26 = tech.get("price_change_26w_pct")
        chg26_str = f"{chg26:+.1f}%" if chg26 is not None else "—"
        chg26_color = "green" if chg26 and chg26 > 0 else "red"

        table.add_row(
            d["symbol"],
            price,
            mktcap,
            pe,
            fpe,
            hi,
            lo,
            f"[{pct_hi_color}]{pct_hi_str}[/{pct_hi_color}]",
            f"[{rsi_color}]{rsi_str}[/{rsi_color}]",
            f"[{chg8_color}]{chg8_str}[/{chg8_color}]",
            f"[{chg26_color}]{chg26_str}[/{chg26_color}]",
        )

    console.print(table)


def print_options_table(market_data: list[dict]) -> None:
    rows = [(d["symbol"], exp, data) for d in market_data if d.get("options") for exp, data in d["options"].items()]
    if not rows:
        return

    table = Table(title="Options Market Intelligence", show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Ticker", style="bold white", width=8)
    table.add_column("Expiry", width=12)
    table.add_column("Call IV%", justify="right", width=9)
    table.add_column("Put IV%", justify="right", width=9)
    table.add_column("Put/Call OI", justify="right", width=11)
    table.add_column("Call OI", justify="right", width=10)
    table.add_column("Put OI", justify="right", width=10)
    table.add_column("Signal", width=20)

    for symbol, exp, data in rows[:20]:
        call_iv = f"{data['avg_call_iv']}%" if data.get("avg_call_iv") else "—"
        put_iv  = f"{data['avg_put_iv']}%"  if data.get("avg_put_iv")  else "—"
        pcr = data.get("put_call_ratio")
        pcr_str = f"{pcr:.2f}" if pcr else "—"
        pcr_color = "red" if pcr and pcr > 1.2 else ("green" if pcr and pcr < 0.7 else "yellow")

        # Signal interpretation
        if pcr and data.get("avg_put_iv") and data.get("avg_call_iv"):
            if pcr > 1.2 and data["avg_put_iv"] > data["avg_call_iv"] * 1.2:
                signal = "[red]FEAR — puts expensive[/red]"
            elif pcr < 0.7 and data["avg_call_iv"] > data["avg_put_iv"] * 1.1:
                signal = "[green]GREED — calls bid up[/green]"
            else:
                signal = "[yellow]Neutral[/yellow]"
        else:
            signal = "—"

        table.add_row(
            symbol, exp, call_iv, put_iv,
            f"[{pcr_color}]{pcr_str}[/{pcr_color}]",
            f"{data.get('call_oi', 0):,}",
            f"{data.get('put_oi', 0):,}",
            signal,
        )

    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(
    trend: dict,
    model: str = "claude-opus-4-8",
    output_file: Optional[str] = None,
    skip_options: bool = False,
    dry_run: bool = False,
) -> None:
    today = datetime.now().strftime("%B %d, %Y")
    tickers = trend["tickers"]

    console.print(Rule(f"[bold cyan]AI MACRO INVESTOR — {trend['name'].upper()}[/bold cyan]"))
    console.print(f"[dim]Model: {model}  |  Date: {today}  |  Tickers: {', '.join(tickers)}[/dim]\n")

    # ── 1. Fetch market data ──────────────────────────────────────────────────
    market_data = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as prog:
        task = prog.add_task("Fetching live market data...", total=len(tickers))
        for ticker in tickers:
            prog.update(task, description=f"Fetching {ticker}...")
            data = fetch_ticker_data(ticker)
            market_data.append(data)
            prog.advance(task)

    # ── 2. Display data tables ────────────────────────────────────────────────
    console.print()
    print_market_data_table(market_data)
    console.print()
    if not skip_options:
        print_options_table(market_data)
        console.print()

    if dry_run:
        console.print("[bold yellow]DRY RUN — skipping Claude API call.[/bold yellow]")
        return

    # ── 3. Call Claude ────────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] ANTHROPIC_API_KEY environment variable not set.")
        console.print("  Export it: [bold]export ANTHROPIC_API_KEY=sk-ant-...[/bold]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_analysis_prompt(trend, market_data, today)

    console.print(f"[dim]Generating strategy with [bold]{model}[/bold] ...[/dim]\n")

    full_response = ""
    with client.messages.stream(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            console.print(text, end="", highlight=False)
            full_response += text

    console.print("\n")
    console.print(Rule("[dim]END OF ANALYSIS[/dim]"))

    # ── 4. Save to file if requested ──────────────────────────────────────────
    if output_file:
        with open(output_file, "w") as f:
            f.write(f"# AI Macro Investor — {trend['name']}\n")
            f.write(f"*Generated: {today} | Model: {model}*\n\n")
            f.write(full_response)
        console.print(f"\n[green]Saved to:[/green] {output_file}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Macro Investor — 6-Level Bottleneck Analysis powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python macro_investor.py --trend ai-power
  python macro_investor.py --trend ai-silicon --model claude-opus-4-8
  python macro_investor.py --trend copper --output copper_thesis.md
  python macro_investor.py --custom "Nuclear SMR" --tickers CEG VST NNE SMR
  python macro_investor.py --list-trends
        """,
    )

    parser.add_argument(
        "--trend",
        choices=list(TRENDS.keys()),
        help="Predefined trend to analyze",
    )
    parser.add_argument(
        "--custom",
        metavar="TREND_NAME",
        help="Custom trend name (use with --tickers)",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Tickers to analyze (for --custom or to override a preset)",
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use (default: claude-opus-4-8)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save analysis to a markdown file",
    )
    parser.add_argument(
        "--list-trends",
        action="store_true",
        help="List all available predefined trends",
    )
    parser.add_argument(
        "--no-options",
        action="store_true",
        help="Skip options chain fetching (faster)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch market data and display tables only — skip Claude API call",
    )

    args = parser.parse_args()

    # ── List trends mode ──────────────────────────────────────────────────────
    if args.list_trends:
        table = Table(title="Available Trends", show_header=True, header_style="bold cyan")
        table.add_column("--trend", style="bold yellow", width=14)
        table.add_column("Name", width=42)
        table.add_column("Tickers", width=50)
        for key, t in TRENDS.items():
            table.add_row(key, t["name"], ", ".join(t["tickers"]))
        console.print(table)
        return

    # ── Resolve trend ─────────────────────────────────────────────────────────
    if args.trend:
        trend = dict(TRENDS[args.trend])
        if args.tickers:
            trend["tickers"] = args.tickers  # allow override
    elif args.custom:
        if not args.tickers:
            console.print("[red]--custom requires --tickers[/red]")
            sys.exit(1)
        trend = {
            "name": args.custom,
            "description": f"Custom trend analysis: {args.custom}",
            "tickers": args.tickers,
            "benchmark": "SPY",
        }
    else:
        parser.print_help()
        sys.exit(0)

    run_analysis(
        trend=trend,
        model=args.model,
        output_file=args.output,
        skip_options=args.no_options,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
