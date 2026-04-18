---
name: trading-analysis
description: Use this skill when the user wants to run or refactor TradingAgents-style multi-agent trading analysis with Codex agents. Covers splitting analyst, researcher, risk, trader, and portfolio-manager roles into compact Codex-agent tasks, generating role packets, and running a free-tier-friendly workflow for a ticker and analysis date.
---

# Trading Analysis

Use this skill for `/home/hanyu/Codes/TradingAgents_codex` when the user wants any of:
- Split TradingAgents roles into Codex agents
- Replace the LangGraph flow with a Codex-orchestrated workflow
- Run a compact workflow that is friendlier to third-party or free-tier APIs
- Generate reusable role packets for analysts and decision makers

## Quick Workflow

1. Confirm the target ticker and analysis date.
2. Generate role packets with `scripts/build_role_packets.py`.
3. Spawn parallel Codex agents for the selected analyst roles.
4. Merge analyst outputs through bull/bear/research-manager roles if needed.
5. Finish with trader and portfolio-manager synthesis.

## Default Split

Analyst layer:
- `market`
- `news`
- `social`
- `fundamentals`

Decision layer:
- `bull`
- `bear`
- `research_manager`
- `trader`
- `aggressive`
- `neutral`
- `conservative`
- `portfolio_manager`

## When To Use Compact Mode

Prefer compact mode when:
- The provider has strict prompt-token limits
- News/fundamentals APIs are unstable
- The user wants a fast technical or tactical read

Compact default:
- Run `market` first
- Add `news` and `fundamentals` only if data is available
- Skip debate loops unless the user explicitly wants them

## Script

Generate role packets:

```bash
python /home/hanyu/Codes/TradingAgents_codex/codex_skills/trading-analysis/scripts/build_role_packets.py \
  --ticker SNDK \
  --analysis-date 2026-04-09 \
  --analysts market,news,fundamentals \
  --include-synthesis
```

Outputs go to `codex_runs/<ticker>/<date>/` by default and include:
- `shared_context.json`
- `workflow.json`
- `prompts/*.md`

Run the full Codex workflow:

```bash
tradingagents codex-analyze \
  --ticker SNDK \
  --analysis-date 2026-04-09 \
  --model gpt-5.4 \
  --reasoning-effort medium \
  --search
```

## References

- Role map and compact prompt guidance: `references/roles.md`
- Output contracts: `references/schemas.md`

## Operating Rules

- Reuse local data or cached reports when possible.
- Keep prompts short enough for the active provider.
- Treat each Codex agent as stateless unless you explicitly pass prior outputs.
- Persist intermediate outputs as files so later roles can consume them without rebuilding context.
