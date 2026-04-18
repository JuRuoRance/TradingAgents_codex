# Schemas

Use these compact JSON contracts between Codex agents.

## Analyst Report

```json
{
  "role": "market",
  "ticker": "SNDK",
  "analysis_date": "2026-04-09",
  "summary": "One paragraph.",
  "signals": [
    "Signal 1",
    "Signal 2"
  ],
  "risks": [
    "Risk 1"
  ],
  "rating": "Buy",
  "confidence": 0.68,
  "levels": {
    "support": "780-785",
    "resistance": "855",
    "invalidation": "726"
  }
}
```

## Debate Memo

```json
{
  "role": "bull",
  "ticker": "SNDK",
  "analysis_date": "2026-04-09",
  "claim": "Why the long case is stronger.",
  "evidence": [
    "Point 1",
    "Point 2"
  ],
  "counterpoints": [
    "Response to main opposing claim"
  ],
  "confidence": 0.64
}
```

## Final Decision

```json
{
  "ticker": "SNDK",
  "analysis_date": "2026-04-09",
  "rating": "Buy",
  "time_horizon": "swing",
  "summary": "Short action summary.",
  "positioning": {
    "entry": "rule or level",
    "size": "starter / full / reduced",
    "stop": "level",
    "take_profit": "level or rule"
  },
  "top_reasons": [
    "Reason 1",
    "Reason 2",
    "Reason 3"
  ],
  "top_risks": [
    "Risk 1",
    "Risk 2"
  ]
}
```
