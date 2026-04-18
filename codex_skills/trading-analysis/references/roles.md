# Role Map

This file maps TradingAgents roles to Codex-agent tasks.

## Analysts

### `market`
- Source: `tradingagents/agents/analysts/market_analyst.py`
- Goal: technical market read from OHLCV and indicators
- Inputs:
  - ticker
  - analysis date
  - price history
  - selected indicators
- Output:
  - `rating`
  - `summary`
  - `thesis`
  - `risks`
  - `levels`

Compact guidance:
- Use up to 5 indicators
- Focus on trend, momentum, volatility, support/resistance
- Avoid long indicator descriptions

### `news`
- Source: `tradingagents/agents/analysts/news_analyst.py`
- Goal: macro and company-news report
- Inputs:
  - ticker
  - analysis date
  - company news
  - macro news
- Output:
  - `summary`
  - `bullish_points`
  - `bearish_points`
  - `watch_items`

### `social`
- Source: `tradingagents/agents/analysts/social_media_analyst.py`
- Goal: sentiment and flow signals
- Inputs:
  - ticker
  - analysis date
  - social or forum data
- Output:
  - `summary`
  - `sentiment`
  - `signal_strength`
  - `risks`

### `fundamentals`
- Source: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Goal: valuation, quality, and financial trend read
- Inputs:
  - ticker
  - statements or fundamentals snapshot
- Output:
  - `summary`
  - `quality_signals`
  - `balance_sheet_risks`
  - `valuation_view`

## Research / Debate

### `bull`
- Source: `tradingagents/agents/researchers/bull_researcher.py`
- Goal: strongest long thesis using analyst outputs
- Output:
  - `claim`
  - `evidence`
  - `counter_to_bear`

### `bear`
- Source: `tradingagents/agents/researchers/bear_researcher.py`
- Goal: strongest short or avoid thesis
- Output:
  - `claim`
  - `evidence`
  - `counter_to_bull`

### `research_manager`
- Source: `tradingagents/agents/managers/research_manager.py`
- Goal: choose buy/sell/hold stance from bull vs bear debate
- Output:
  - `recommendation`
  - `rationale`
  - `implementation_plan`

## Execution / Risk

### `trader`
- Source: `tradingagents/agents/trader/trader.py`
- Goal: turn research stance into a trade proposal
- Output:
  - `proposal`
  - `entry_logic`
  - `time_horizon`
  - `invalidations`

### `aggressive`
### `neutral`
### `conservative`
- Source: `tradingagents/agents/risk_mgmt/*.py`
- Goal: debate sizing and risk from different postures
- Output:
  - `position_view`
  - `key_risks`
  - `counterpoints`

### `portfolio_manager`
- Source: `tradingagents/agents/managers/portfolio_manager.py`
- Goal: final rating and execution summary
- Output:
  - `rating`
  - `executive_summary`
  - `investment_thesis`
  - `risk_controls`

## Recommended Codex-Agent Usage

- Run `market/news/social/fundamentals` in parallel.
- Run `bull` and `bear` after analyst outputs are written to disk.
- Run `research_manager` after `bull` and `bear`.
- Run `trader` after `research_manager`.
- Run `aggressive`, `neutral`, `conservative` in parallel after `trader`.
- Run `portfolio_manager` last.
