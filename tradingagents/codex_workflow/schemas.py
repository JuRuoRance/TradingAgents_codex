"""JSON schemas for Codex workflow outputs."""

from __future__ import annotations


def schema_for_role(role: str) -> dict:
    if role in {"market", "news", "social", "fundamentals"}:
        return _analyst_schema(role)
    if role in {"bull", "bear"}:
        return _debate_schema(role)
    if role == "research_manager":
        return _research_manager_schema()
    if role == "trader":
        return _trader_schema()
    if role in {"aggressive", "neutral", "conservative"}:
        return _risk_schema(role)
    if role == "portfolio_manager":
        return _final_decision_schema()
    raise ValueError(f"Unsupported role: {role}")


def _analyst_schema(role: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role",
            "ticker",
            "analysis_date",
            "summary",
            "signals",
            "risks",
            "rating",
            "confidence",
            "levels",
        ],
        "properties": {
            "role": {"type": "string", "const": role},
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "summary": {"type": "string"},
            "signals": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "rating": {"type": "string", "enum": ["Buy", "Hold", "Sell"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "levels": {
                "type": "object",
                "additionalProperties": False,
                "required": ["support", "resistance", "invalidation"],
                "properties": {
                    "support": {"type": "string"},
                    "resistance": {"type": "string"},
                    "invalidation": {"type": "string"},
                },
            },
        },
    }


def _debate_schema(role: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role",
            "ticker",
            "analysis_date",
            "claim",
            "evidence",
            "counterpoints",
            "confidence",
        ],
        "properties": {
            "role": {"type": "string", "const": role},
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "claim": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "counterpoints": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _research_manager_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role",
            "ticker",
            "analysis_date",
            "rating",
            "summary",
            "implementation_plan",
            "confidence",
        ],
        "properties": {
            "role": {"type": "string", "const": "research_manager"},
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "rating": {"type": "string", "enum": ["Buy", "Hold", "Sell"]},
            "summary": {"type": "string"},
            "implementation_plan": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _trader_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role",
            "ticker",
            "analysis_date",
            "rating",
            "time_horizon",
            "summary",
            "entry_logic",
            "invalidation",
            "execution_notes",
            "confidence",
        ],
        "properties": {
            "role": {"type": "string", "const": "trader"},
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "rating": {"type": "string", "enum": ["Buy", "Hold", "Sell"]},
            "time_horizon": {"type": "string"},
            "summary": {"type": "string"},
            "entry_logic": {"type": "string"},
            "invalidation": {"type": "string"},
            "execution_notes": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _risk_schema(role: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role",
            "ticker",
            "analysis_date",
            "position_view",
            "sizing_guidance",
            "stop_guidance",
            "key_risks",
            "confidence",
        ],
        "properties": {
            "role": {"type": "string", "const": role},
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "position_view": {"type": "string"},
            "sizing_guidance": {"type": "string"},
            "stop_guidance": {"type": "string"},
            "key_risks": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _final_decision_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "ticker",
            "analysis_date",
            "rating",
            "time_horizon",
            "summary",
            "positioning",
            "top_reasons",
            "top_risks",
        ],
        "properties": {
            "ticker": {"type": "string"},
            "analysis_date": {"type": "string"},
            "rating": {"type": "string", "enum": ["Buy", "Hold", "Sell"]},
            "time_horizon": {"type": "string"},
            "summary": {"type": "string"},
            "positioning": {
                "type": "object",
                "additionalProperties": False,
                "required": ["entry", "size", "stop", "take_profit"],
                "properties": {
                    "entry": {"type": "string"},
                    "size": {"type": "string"},
                    "stop": {"type": "string"},
                    "take_profit": {"type": "string"},
                },
            },
            "top_reasons": {"type": "array", "items": {"type": "string"}},
            "top_risks": {"type": "array", "items": {"type": "string"}},
        },
    }
