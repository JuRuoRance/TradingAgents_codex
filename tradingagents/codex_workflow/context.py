"""Collect compact local context for Codex workflow roles."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.default_config import DEFAULT_CONFIG


def configure_local_data_vendors() -> None:
    config = DEFAULT_CONFIG.copy()
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    set_config(config)


def build_role_context(role: str, ticker: str, analysis_date: str) -> str:
    configure_local_data_vendors()
    if role == "market":
        return _build_market_context(ticker, analysis_date)
    if role == "news":
        return _build_news_context(ticker, analysis_date)
    if role == "social":
        return _build_social_context(ticker, analysis_date)
    if role == "fundamentals":
        return _build_fundamentals_context(ticker, analysis_date)
    raise ValueError(f"Unsupported analyst role: {role}")


def _build_market_context(ticker: str, analysis_date: str) -> str:
    end_date = _parse_date(analysis_date)
    start_date = end_date - timedelta(days=180)
    stock_data = route_to_vendor(
        "get_stock_data",
        ticker,
        start_date.isoformat(),
        analysis_date,
    )
    indicator_names = [
        "rsi",
        "macd",
        "atr",
        "close_50_sma",
        "close_200_sma",
        "boll",
    ]
    indicators = []
    for name in indicator_names:
        indicators.append(
            f"## {name}\n{_shorten_text(route_to_vendor('get_indicators', ticker, name, analysis_date, 90), max_chars=3000)}"
        )

    return "\n\n".join(
        [
            f"# Market Context for {ticker}",
            _shorten_csv_block(stock_data),
            *indicators,
        ]
    )


def _build_news_context(ticker: str, analysis_date: str) -> str:
    end_date = _parse_date(analysis_date)
    start_date = end_date - timedelta(days=7)
    company_news = route_to_vendor(
        "get_news",
        ticker,
        start_date.isoformat(),
        analysis_date,
    )
    macro_news = route_to_vendor("get_global_news", analysis_date, 7, 8)
    return "\n\n".join(
        [
            f"# Company News for {ticker}",
            _shorten_text(company_news, max_chars=10000),
            "# Macro News",
            _shorten_text(macro_news, max_chars=8000),
        ]
    )


def _build_social_context(ticker: str, analysis_date: str) -> str:
    end_date = _parse_date(analysis_date)
    start_date = end_date - timedelta(days=7)
    company_news = route_to_vendor(
        "get_news",
        ticker,
        start_date.isoformat(),
        analysis_date,
    )
    return "\n\n".join(
        [
            f"# Sentiment Proxy Context for {ticker}",
            (
                "The local data connectors do not expose a dedicated social-media feed. "
                "Use the news flow below as a positioning and crowding proxy, and call out "
                "that limitation explicitly in your output."
            ),
            _shorten_text(company_news, max_chars=10000),
        ]
    )


def _build_fundamentals_context(ticker: str, analysis_date: str) -> str:
    fundamentals = route_to_vendor("get_fundamentals", ticker, analysis_date)
    balance_sheet = route_to_vendor("get_balance_sheet", ticker, "quarterly", analysis_date)
    cashflow = route_to_vendor("get_cashflow", ticker, "quarterly", analysis_date)
    income_statement = route_to_vendor("get_income_statement", ticker, "quarterly", analysis_date)
    insider = route_to_vendor("get_insider_transactions", ticker)
    return "\n\n".join(
        [
            f"# Fundamentals Context for {ticker}",
            _shorten_text(fundamentals, max_chars=9000),
            "## Balance Sheet",
            _shorten_text(balance_sheet, max_chars=5000),
            "## Cash Flow",
            _shorten_text(cashflow, max_chars=5000),
            "## Income Statement",
            _shorten_text(income_statement, max_chars=5000),
            "## Insider Transactions",
            _shorten_text(insider, max_chars=4000),
        ]
    )


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _shorten_csv_block(text: str, *, max_chars: int = 7000) -> str:
    lines = text.splitlines()
    if len(lines) <= 35:
        return _shorten_text(text, max_chars=max_chars)
    trimmed = lines[:6] + ["..."] + lines[-28:]
    return _shorten_text("\n".join(trimmed), max_chars=max_chars)


def _shorten_text(text: str, *, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    keep_head = max_chars // 2
    keep_tail = max_chars - keep_head - len("\n...\n")
    return text[:keep_head].rstrip() + "\n...\n" + text[-keep_tail:].lstrip()
