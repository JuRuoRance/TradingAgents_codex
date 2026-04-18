"""Build reusable Codex role packets for TradingAgents workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_DIR = PROJECT_ROOT / "codex_runs"

ANALYST_ROLES = ["market", "news", "social", "fundamentals"]
SYNTHESIS_ROLES = [
    "bull",
    "bear",
    "research_manager",
    "trader",
    "aggressive",
    "neutral",
    "conservative",
    "portfolio_manager",
]

ROLE_PROMPTS = {
    "market": (
        "Produce a compact technical market report for {ticker} on {analysis_date}. "
        "Use price history and indicators only. Return JSON matching the analyst schema."
    ),
    "news": (
        "Produce a compact company and macro news report for {ticker} on {analysis_date}. "
        "Return JSON matching the analyst schema without technical indicators."
    ),
    "social": (
        "Produce a compact social sentiment report for {ticker} on {analysis_date}. "
        "Focus on positioning, crowding, and sentiment swings. Return JSON."
    ),
    "fundamentals": (
        "Produce a compact fundamentals report for {ticker} on {analysis_date}. "
        "Focus on quality, valuation, and financial trend. Return JSON."
    ),
    "bull": (
        "Use the analyst reports to write the strongest bull case for {ticker} on {analysis_date}. "
        "Return JSON matching the debate schema."
    ),
    "bear": (
        "Use the analyst reports to write the strongest bear case for {ticker} on {analysis_date}. "
        "Return JSON matching the debate schema."
    ),
    "research_manager": (
        "Read bull and bear memos and choose Buy, Hold, or Sell for {ticker} on {analysis_date}. "
        "Return a recommendation plus implementation plan in JSON."
    ),
    "trader": (
        "Convert the research recommendation for {ticker} on {analysis_date} into a tactical trade plan. "
        "Return JSON with entry logic, horizon, and invalidation."
    ),
    "aggressive": (
        "Review the trade plan for {ticker} on {analysis_date} from an aggressive risk posture. "
        "Return JSON with position view, upside case, and key risks."
    ),
    "neutral": (
        "Review the trade plan for {ticker} on {analysis_date} from a neutral risk posture. "
        "Return JSON with balanced position guidance."
    ),
    "conservative": (
        "Review the trade plan for {ticker} on {analysis_date} from a conservative risk posture. "
        "Return JSON with downside controls and stricter invalidation."
    ),
    "portfolio_manager": (
        "Read the trader plan and all three risk memos for {ticker} on {analysis_date}. "
        "Return the final decision JSON using the final-decision schema."
    ),
}


@dataclass(frozen=True)
class PacketBundle:
    run_dir: Path
    prompts_dir: Path
    reports_dir: Path
    contexts_dir: Path
    logs_dir: Path
    schemas_dir: Path
    shared_context_path: Path
    workflow_path: Path


def default_run_dir(
    ticker: str,
    analysis_date: str,
    base_dir: Path | None = None,
) -> Path:
    root = base_dir or DEFAULT_RUNS_DIR
    return root / ticker.upper() / analysis_date


def parse_roles(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, str):
        roles = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        roles = [str(part).strip() for part in raw if str(part).strip()]

    unknown = [role for role in roles if role not in ANALYST_ROLES]
    if unknown:
        raise ValueError(f"Unsupported analyst roles: {', '.join(unknown)}")
    return roles


def build_shared_context(
    ticker: str,
    analysis_date: str,
    analysts: list[str],
    mode: str,
    provider: str,
    base_url_env: str,
    notes: str,
    include_synthesis: bool,
) -> dict:
    return {
        "ticker": ticker.upper(),
        "analysis_date": analysis_date,
        "mode": mode,
        "provider": provider,
        "base_url_env": base_url_env,
        "notes": notes,
        "recommended_order": analysts + (SYNTHESIS_ROLES if include_synthesis else []),
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_prompt(path: Path, role: str, ticker: str, analysis_date: str) -> None:
    text = ROLE_PROMPTS[role].format(ticker=ticker, analysis_date=analysis_date)
    path.write_text(text + "\n", encoding="utf-8")


def build_packet_bundle(
    ticker: str,
    analysis_date: str,
    analysts: str | Iterable[str] = "market,news,social,fundamentals",
    *,
    mode: str = "compact",
    provider: str = "codex",
    base_url_env: str = "",
    notes: str = "",
    include_synthesis: bool = True,
    output_dir: Path | None = None,
) -> PacketBundle:
    analyst_roles = parse_roles(analysts)
    run_dir = default_run_dir(ticker, analysis_date, output_dir)
    prompts_dir = run_dir / "prompts"
    reports_dir = run_dir / "reports"
    contexts_dir = run_dir / "contexts"
    logs_dir = run_dir / "logs"
    schemas_dir = run_dir / "schemas"

    for path in (prompts_dir, reports_dir, contexts_dir, logs_dir, schemas_dir):
        path.mkdir(parents=True, exist_ok=True)

    shared_context_path = run_dir / "shared_context.json"
    workflow_path = run_dir / "workflow.json"

    shared_context = build_shared_context(
        ticker=ticker,
        analysis_date=analysis_date,
        analysts=analyst_roles,
        mode=mode,
        provider=provider,
        base_url_env=base_url_env,
        notes=notes,
        include_synthesis=include_synthesis,
    )
    workflow = {
        "analyst_roles": analyst_roles,
        "synthesis_roles": SYNTHESIS_ROLES if include_synthesis else [],
        "artifacts": {
            "shared_context": str(shared_context_path),
            "prompts_dir": str(prompts_dir),
            "reports_dir": str(reports_dir),
            "contexts_dir": str(contexts_dir),
            "logs_dir": str(logs_dir),
            "schemas_dir": str(schemas_dir),
        },
    }

    write_json(shared_context_path, shared_context)
    write_json(workflow_path, workflow)

    for role in analyst_roles:
        write_prompt(prompts_dir / f"{role}.md", role, ticker.upper(), analysis_date)

    if include_synthesis:
        for role in SYNTHESIS_ROLES:
            write_prompt(prompts_dir / f"{role}.md", role, ticker.upper(), analysis_date)

    return PacketBundle(
        run_dir=run_dir,
        prompts_dir=prompts_dir,
        reports_dir=reports_dir,
        contexts_dir=contexts_dir,
        logs_dir=logs_dir,
        schemas_dir=schemas_dir,
        shared_context_path=shared_context_path,
        workflow_path=workflow_path,
    )
