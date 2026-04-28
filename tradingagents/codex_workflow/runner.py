"""Codex-driven orchestration path for TradingAgents."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .context import build_role_context
from .packets import (
    ANALYST_ROLES,
    PacketBundle,
    PROJECT_ROOT,
    SYNTHESIS_ROLES,
    build_packet_bundle,
)
from .schemas import schema_for_role


ROLE_PHASES = [
    ("analysts", ["market", "news", "social", "fundamentals"]),
    ("debate", ["bull", "bear"]),
    ("research", ["research_manager"]),
    ("trader", ["trader"]),
    ("risk", ["aggressive", "neutral", "conservative"]),
    ("portfolio", ["portfolio_manager"]),
]

ROLE_LABELS = {
    "market": {"english": "market", "chinese": "市场分析"},
    "news": {"english": "news", "chinese": "新闻分析"},
    "social": {"english": "social", "chinese": "情绪分析"},
    "fundamentals": {"english": "fundamentals", "chinese": "基本面分析"},
    "bull": {"english": "bull", "chinese": "看多观点"},
    "bear": {"english": "bear", "chinese": "看空观点"},
    "research_manager": {"english": "research_manager", "chinese": "研究经理"},
    "trader": {"english": "trader", "chinese": "交易员"},
    "aggressive": {"english": "aggressive", "chinese": "激进风控"},
    "neutral": {"english": "neutral", "chinese": "中性风控"},
    "conservative": {"english": "conservative", "chinese": "保守风控"},
    "portfolio_manager": {"english": "portfolio_manager", "chinese": "投资组合经理"},
}

NUMERIC_TOKEN_PATTERN = re.compile(
    r"[+-]?\s*[$€£¥]?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:%|[KMBT])?",
    re.IGNORECASE,
)


class CodexExecutionError(RuntimeError):
    """Raised when a Codex CLI role process exits unsuccessfully."""

    def __init__(
        self,
        *,
        role: str,
        exit_code: int,
        log_path: Path,
        detail: str,
    ) -> None:
        self.role = role
        self.exit_code = exit_code
        self.log_path = log_path
        super().__init__(
            f"Codex role '{role}' failed with exit code {exit_code}. {detail} "
            f"See {log_path}."
        )


@dataclass(frozen=True)
class CodexAnalysisConfig:
    ticker: str
    analysis_date: str
    model: str = "gpt-5.5"
    analysts: tuple[str, ...] = ("market", "news", "social", "fundamentals")
    include_synthesis: bool = True
    use_search: bool = False
    output_language: str = "Chinese"
    reasoning_effort: str = "medium"
    max_parallel: int = 2
    notes: str = ""
    output_dir: Path | None = None
    codex_command: Path | None = None

    def command_path(self) -> Path:
        if self.codex_command is not None:
            return self.codex_command
        codex_path = shutil.which("codex")
        if codex_path:
            return Path(codex_path)
        return PROJECT_ROOT / "bin" / "codex-local"


def run_codex_analysis(config: CodexAnalysisConfig) -> dict[str, Any]:
    bundle = build_packet_bundle(
        ticker=config.ticker,
        analysis_date=config.analysis_date,
        analysts=config.analysts,
        provider="codex",
        notes=config.notes,
        include_synthesis=config.include_synthesis,
        output_dir=config.output_dir,
    )
    context_paths = _write_contexts(bundle, config)
    results: dict[str, Any] = {}
    report_paths: dict[str, Path] = {}

    for phase_name, phase_roles in ROLE_PHASES:
        if not config.include_synthesis and phase_name != "analysts":
            break
        active_roles = [role for role in phase_roles if _role_enabled(role, config.analysts)]
        if not active_roles:
            continue
        batch = _run_phase(active_roles, bundle, context_paths, report_paths, config)
        results.update(batch)
        for role, payload in batch.items():
            report_paths[role] = bundle.reports_dir / f"{role}.json"
            _write_report_files(role, payload, bundle.reports_dir)

    complete_report_path = _write_complete_report(results, bundle.reports_dir)

    if config.output_language.strip().lower() != "english":
        _write_backup_artifacts(results, bundle.reports_dir)
        translated_results = _translate_results(results, bundle, config)
        for role, payload in translated_results.items():
            _write_report_files(
                role,
                payload,
                bundle.reports_dir,
                output_language=config.output_language,
            )
        complete_report_path = _write_complete_report(
            translated_results,
            bundle.reports_dir,
            output_language=config.output_language,
        )
        results = translated_results

    final_payload = results.get("portfolio_manager")
    return {
        "run_dir": bundle.run_dir,
        "workflow_path": bundle.workflow_path,
        "reports_dir": bundle.reports_dir,
        "complete_report_path": complete_report_path,
        "results": results,
        "final_decision": final_payload,
    }


def clean_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            _, end = decoder.raw_decode(text[index:])
        except ValueError:
            continue
        return text[index : index + end]
    return text


def _role_enabled(role: str, analysts: tuple[str, ...]) -> bool:
    if role in ANALYST_ROLES:
        return role in analysts
    return True


def _write_contexts(bundle: PacketBundle, config: CodexAnalysisConfig) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for role in config.analysts:
        context_text = build_role_context(role, config.ticker, config.analysis_date)
        path = bundle.contexts_dir / f"{role}.md"
        path.write_text(context_text + "\n", encoding="utf-8")
        paths[role] = path
    return paths


def _run_phase(
    roles: list[str],
    bundle: PacketBundle,
    context_paths: dict[str, Path],
    report_paths: dict[str, Path],
    config: CodexAnalysisConfig,
) -> dict[str, Any]:
    worker_count = max(1, min(config.max_parallel, len(roles)))
    if worker_count == 1:
        return {
            role: _run_role(role, bundle, context_paths, report_paths, config)
            for role in roles
        }

    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                _run_role,
                role,
                bundle,
                context_paths,
                report_paths,
                config,
            ): role
            for role in roles
        }
        for future in as_completed(future_map):
            role = future_map[future]
            results[role] = future.result()
    return results


def _run_role(
    role: str,
    bundle: PacketBundle,
    context_paths: dict[str, Path],
    report_paths: dict[str, Path],
    config: CodexAnalysisConfig,
) -> Any:
    schema_path = bundle.schemas_dir / f"{role}.schema.json"
    schema_path.write_text(
        json.dumps(schema_for_role(role), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    output_path = bundle.logs_dir / f"{role}.last_message.json"
    log_path = bundle.logs_dir / f"{role}.exec.log"
    prompt = _build_role_prompt(role, bundle, context_paths, report_paths, schema_path, config)

    return _run_codex_json_prompt(
        role=role,
        prompt=prompt,
        schema_path=schema_path,
        output_path=output_path,
        log_path=log_path,
        model=config.model,
        reasoning_effort=config.reasoning_effort,
        use_search=config.use_search,
        command_path=config.command_path(),
    )


def _run_codex_json_prompt(
    *,
    role: str,
    prompt: str,
    schema_path: Path,
    output_path: Path,
    log_path: Path,
    model: str,
    reasoning_effort: str,
    use_search: bool,
    command_path: Path,
) -> Any:
    """Run a non-interactive Codex prompt that must return a JSON payload."""

    command = [
        str(command_path),
        "-s",
        "read-only",
        "-a",
        "never",
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
    ]
    if use_search:
        command.append("--search")
    command.extend(
        [
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "-C",
            str(PROJECT_ROOT),
            "-m",
            model,
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
            prompt,
        ]
    )

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=_build_codex_subprocess_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    log_text = completed.stdout + ("\n" + completed.stderr if completed.stderr else "")
    log_path.write_text(log_text, encoding="utf-8")
    if completed.returncode != 0:
        raise CodexExecutionError(
            role=role,
            exit_code=completed.returncode,
            log_path=log_path,
            detail=_codex_failure_detail(log_text),
        )

    raw_output = output_path.read_text(encoding="utf-8")
    return json.loads(clean_json_text(raw_output))


def _codex_failure_detail(log_text: str) -> str:
    usage_limit = _extract_usage_limit_message(log_text)
    if usage_limit:
        return (
            f"{usage_limit} Retry after the reset time, reduce --max-parallel, "
            "or choose a lighter model such as gpt-5.4-mini."
        )

    excerpt = _log_excerpt(log_text)
    if excerpt:
        return f"Last Codex output:\n{excerpt}\n"

    return "Codex produced no diagnostic output."


def _extract_usage_limit_message(log_text: str) -> str | None:
    for line in log_text.splitlines():
        if "usage limit" in line.lower():
            return re.sub(r"^ERROR:\s*", "", line.strip())
    return None


def _log_excerpt(log_text: str, *, max_lines: int = 8) -> str:
    lines = [line for line in log_text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])


def _build_codex_subprocess_env() -> dict[str, str]:
    """Remove app-level API gateway overrides before spawning Codex.

    The TradingAgents app can load OpenAI-compatible gateway settings like
    ChatAnywhere through `.env`. Codex CLI should not inherit those unless they
    point at the official OpenAI endpoint, otherwise Codex auth tokens get sent
    to a third-party base URL and fail with 401s.
    """
    env = os.environ.copy()

    openai_base_url = env.get("OPENAI_BASE_URL", "").strip()
    if openai_base_url and not openai_base_url.startswith("https://api.openai.com"):
        env.pop("OPENAI_BASE_URL", None)

    # TradingAgents-specific backend alias should never affect Codex CLI.
    env.pop("TRADINGAGENTS_BACKEND_URL", None)

    # Empty values from `.env` should not shadow Codex's own auth flow.
    if env.get("OPENAI_API_KEY", "").strip() == "":
        env.pop("OPENAI_API_KEY", None)

    return env


def _build_role_prompt(
    role: str,
    bundle: PacketBundle,
    context_paths: dict[str, Path],
    report_paths: dict[str, Path],
    schema_path: Path,
    config: CodexAnalysisConfig,
) -> str:
    prompt_path = bundle.prompts_dir / f"{role}.md"
    shared_context = bundle.shared_context_path
    references = [
        f"Read the workflow context from {shared_context}.",
        f"Read the role brief from {prompt_path}.",
        f"Your output must match the JSON schema at {schema_path}.",
    ]

    if role in ANALYST_ROLES:
        references.append(f"Read the prepared local context at {context_paths[role]}.")
    elif role in {"bull", "bear", "research_manager"}:
        references.extend(
            f"Read analyst report {report_paths[name]}."
            for name in config.analysts
            if name in report_paths
        )
    elif role == "trader":
        references.append(f"Read the research decision at {report_paths['research_manager']}.")
        references.extend(
            f"Read analyst report {report_paths[name]}."
            for name in config.analysts
            if name in report_paths
        )
    elif role in {"aggressive", "neutral", "conservative"}:
        references.append(f"Read the trader plan at {report_paths['trader']}.")
        references.append(f"Read the research decision at {report_paths['research_manager']}.")
    elif role == "portfolio_manager":
        references.append(f"Read the trader plan at {report_paths['trader']}.")
        references.append(f"Read the research decision at {report_paths['research_manager']}.")
        for name in ("aggressive", "neutral", "conservative"):
            references.append(f"Read risk memo {report_paths[name]}.")

    if config.use_search:
        search_rule = (
            "Live web search is enabled. Use it only to fill gaps in current news or context; "
            "prefer the local run artifacts first."
        )
    else:
        search_rule = (
            "Live web search is disabled. Ground the response only in the local run artifacts."
        )

    return "\n".join(
        [
            f"You are the '{role}' role in a TradingAgents Codex workflow for {config.ticker.upper()} on {config.analysis_date}.",
            *references,
            search_rule,
            "Rules:",
            "1. Produce exactly one JSON object and nothing else.",
            "2. Do not wrap the JSON in markdown fences.",
            "3. Keep claims tightly grounded in the provided files.",
            "4. If an input is missing, say so briefly inside the JSON fields instead of inventing facts.",
        ]
    )


def _translate_results(
    results: dict[str, Any],
    bundle: PacketBundle,
    config: CodexAnalysisConfig,
) -> dict[str, Any]:
    translated: dict[str, Any] = {}
    for role, payload in results.items():
        source_path = bundle.reports_dir / f"{role}.en.json"
        schema_path = bundle.schemas_dir / f"{role}.translated.schema.json"
        output_path = bundle.logs_dir / f"{role}.translated.last_message.json"
        log_path = bundle.logs_dir / f"{role}.translated.exec.log"
        integrity_path = bundle.logs_dir / f"{role}.translation_integrity.json"
        schema_path.write_text(
            json.dumps(_schema_for_payload_shape(payload), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        source_json = json.dumps(payload, indent=2, ensure_ascii=False)
        mismatches: list[dict[str, Any]] = []
        candidate: Any = None
        for attempt in range(2):
            prompt = _build_translation_prompt(
                role=role,
                source_path=source_path,
                source_json=source_json,
                schema_path=schema_path,
                target_language=config.output_language,
                numeric_mismatches=mismatches,
            )
            candidate = _run_codex_json_prompt(
                role=role,
                prompt=prompt,
                schema_path=schema_path,
                output_path=output_path,
                log_path=log_path,
                model=config.model,
                reasoning_effort="low",
                use_search=False,
                command_path=config.command_path(),
            )
            mismatches = _find_numeric_token_mismatches(payload, candidate)
            if not mismatches:
                break

        if mismatches:
            candidate, repaired_paths = _repair_numeric_token_mismatches(payload, candidate)
            integrity_path.write_text(
                json.dumps(
                    {
                        "role": role,
                        "status": "repaired",
                        "message": (
                            "Numeric tokens changed during translation. "
                            "Affected string fields were restored from the English source."
                        ),
                        "mismatches": mismatches,
                        "repaired_paths": repaired_paths,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        translated[role] = candidate
    return translated


def _build_translation_prompt(
    *,
    role: str,
    source_path: Path,
    source_json: str,
    schema_path: Path,
    target_language: str,
    numeric_mismatches: list[dict[str, Any]] | None = None,
) -> str:
    lines = [
        f"Translate the report JSON for role '{role}' into {target_language}.",
        f"The source JSON is also saved at {source_path}.",
        f"Your output must match the JSON schema at {schema_path}.",
        "Rules:",
        "1. Preserve JSON keys and structure exactly.",
        "2. This is translation only. Do not perform new analysis, update facts, replace the thesis, or invent content.",
        "3. Preserve every numeric token exactly, including dates, prices, percentages, ranges, currency symbols, decimals, and K/M/B/T suffixes.",
        "4. Translate all user-facing English text into natural Simplified Chinese when target language is Chinese.",
        "5. Translate rating words, but do not translate or alter tickers, dates, prices, percentages, or other numeric values.",
        "6. Return exactly one JSON object and nothing else.",
    ]
    if numeric_mismatches:
        lines.extend(
            [
                "The previous translation changed numeric tokens at these paths. Fix them exactly:",
                json.dumps(numeric_mismatches, indent=2, ensure_ascii=False),
            ]
        )
    lines.extend(
        [
            "Source JSON to translate exactly:",
            "```json",
            source_json,
            "```",
        ]
    )
    return "\n".join(lines)


def _numeric_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        re.sub(r"\s+", "", match.group(0)).replace(",", "").upper()
        for match in NUMERIC_TOKEN_PATTERN.finditer(text)
    )


def _find_numeric_token_mismatches(
    source: Any,
    translated: Any,
    *,
    path: str = "$",
) -> list[dict[str, Any]]:
    if isinstance(source, str) and isinstance(translated, str):
        source_tokens = _numeric_tokens(source)
        translated_tokens = _numeric_tokens(translated)
        if source_tokens != translated_tokens:
            return [
                {
                    "path": path,
                    "source_tokens": source_tokens,
                    "translated_tokens": translated_tokens,
                }
            ]
        return []
    if isinstance(source, dict) and isinstance(translated, dict):
        mismatches: list[dict[str, Any]] = []
        for key, source_value in source.items():
            if key in translated:
                mismatches.extend(
                    _find_numeric_token_mismatches(
                        source_value,
                        translated[key],
                        path=f"{path}.{key}",
                    )
                )
        return mismatches
    if isinstance(source, list) and isinstance(translated, list):
        mismatches = []
        for index, source_value in enumerate(source):
            if index < len(translated):
                mismatches.extend(
                    _find_numeric_token_mismatches(
                        source_value,
                        translated[index],
                        path=f"{path}[{index}]",
                    )
                )
        return mismatches
    return []


def _repair_numeric_token_mismatches(
    source: Any,
    translated: Any,
    *,
    path: str = "$",
) -> tuple[Any, list[str]]:
    if isinstance(source, str) and isinstance(translated, str):
        if _numeric_tokens(source) != _numeric_tokens(translated):
            return source, [path]
        return translated, []
    if isinstance(source, dict) and isinstance(translated, dict):
        repaired = dict(translated)
        repaired_paths: list[str] = []
        for key, source_value in source.items():
            if key not in repaired:
                continue
            repaired_value, child_paths = _repair_numeric_token_mismatches(
                source_value,
                repaired[key],
                path=f"{path}.{key}",
            )
            repaired[key] = repaired_value
            repaired_paths.extend(child_paths)
        return repaired, repaired_paths
    if isinstance(source, list) and isinstance(translated, list):
        repaired = list(translated)
        repaired_paths = []
        for index, source_value in enumerate(source):
            if index >= len(repaired):
                continue
            repaired_value, child_paths = _repair_numeric_token_mismatches(
                source_value,
                repaired[index],
                path=f"{path}[{index}]",
            )
            repaired[index] = repaired_value
            repaired_paths.extend(child_paths)
        return repaired, repaired_paths
    return translated, []


def _schema_for_payload_shape(payload: Any, *, key_name: str | None = None) -> dict[str, Any]:
    if isinstance(payload, bool):
        return {"type": "boolean"}
    if isinstance(payload, int):
        return {"type": "integer"}
    if isinstance(payload, float):
        return {"type": "number"}
    if isinstance(payload, str):
        if key_name in {"role", "ticker", "analysis_date"}:
            return {"type": "string", "const": payload}
        return {"type": "string"}
    if isinstance(payload, list):
        item_schema = _schema_for_payload_shape(payload[0]) if payload else {}
        return {"type": "array", "items": item_schema}
    if isinstance(payload, dict):
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(payload.keys()),
            "properties": {
                key: _schema_for_payload_shape(value, key_name=key)
                for key, value in payload.items()
            },
        }
    return {}


def _write_backup_artifacts(results: dict[str, Any], reports_dir: Path) -> None:
    for role, payload in results.items():
        _write_report_files(role, payload, reports_dir, filename_suffix=".en")
    _write_complete_report(
        results,
        reports_dir,
        output_language="English",
        filename="complete_report.en.md",
    )


def _write_report_files(
    role: str,
    payload: Any,
    reports_dir: Path,
    *,
    output_language: str = "English",
    filename_suffix: str = "",
) -> None:
    json_path = reports_dir / f"{role}{filename_suffix}.json"
    md_path = reports_dir / f"{role}{filename_suffix}.md"
    heading = _role_heading(role, output_language)
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        f"# {heading}\n\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n",
        encoding="utf-8",
    )


def _write_complete_report(
    results: dict[str, Any],
    reports_dir: Path,
    *,
    output_language: str = "English",
    filename: str = "complete_report.md",
) -> Path:
    sections = []
    for role in list(ANALYST_ROLES) + list(SYNTHESIS_ROLES):
        if role not in results:
            continue
        sections.append(
            f"## {_role_heading(role, output_language)}\n\n```json\n{json.dumps(results[role], indent=2, ensure_ascii=False)}\n```"
        )
    path = reports_dir / filename
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return path


def _role_heading(role: str, output_language: str) -> str:
    language_key = "chinese" if output_language.strip().lower() == "chinese" else "english"
    return ROLE_LABELS.get(role, {}).get(language_key, role)
