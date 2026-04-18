# TradingAgents Codex

`TradingAgents Codex` 是一个面向 Codex CLI 的 `TradingAgents` 分支。它保留了原项目的多模型/API 工作流，同时新增了一条 Codex 原生分析链路：直接用 `codex exec` 驱动多角色研究、交易和风控流程，并在最后把主报告统一翻译为中文。

上游项目：[`TauricResearch/TradingAgents`](https://github.com/TauricResearch/TradingAgents)  
本文档针对当前这个仓库，而不是上游默认发行版。

## 这个分支做了什么

- 新增 `tradingagents codex-analyze` 命令
- 启动后提供和旧版接近的终端交互式选择界面
- 按角色执行 Codex 工作流：`market/news/social/fundamentals -> bull/bear -> research_manager -> trader -> risk -> portfolio_manager`
- 将最终保存的 JSON/Markdown 报告自动翻译为中文
- 同时保留英文原稿，便于核对：`*.en.json`、`*.en.md`、`complete_report.en.md`
- 保留原版 `tradingagents analyze` 能力，仍可走 API / provider 模式

## 工作流模式

| 模式 | 命令 | 说明 |
| --- | --- | --- |
| 原版 API 模式 | `tradingagents analyze` | 继续使用项目里的 provider 配置、LangGraph 图和 API Key |
| Codex 模式 | `tradingagents codex-analyze` | 直接调用本机 Codex CLI 执行每个角色，不依赖项目内 OpenAI API Key |

Codex 模式下，项目会优先使用本地数据上下文和 `yfinance` 构建角色输入；如果开启 `--search`，Codex 还能补充实时网络检索。

## 目录说明

```text
cli/                            CLI 入口与终端交互界面
tradingagents/codex_workflow/   Codex 工作流编排、schema、context、packet 构建
codex_skills/                   配套 Codex skill 与参考资料
bin/codex-local                 项目内 Codex 启动包装脚本
codex_runs/                     每次 Codex 分析的输出目录（自动生成，不纳入版本控制）
```

一次 Codex 分析会生成类似目录：

```text
codex_runs/
  AAPL/
    2026-04-18/
      prompts/
      contexts/
      schemas/
      logs/
      reports/
```

其中 `reports/` 里会包含每个角色的：

- 中文主报告：`<role>.json`、`<role>.md`
- 英文备份：`<role>.en.json`、`<role>.en.md`
- 汇总报告：`complete_report.md`、`complete_report.en.md`

## 环境要求

- Python 3.10+，推荐 3.13
- 已安装 `codex` CLI
- 已完成 Codex 登录
- 可访问市场数据源

确认 Codex CLI 可用：

```bash
codex --help
codex login
```

## 安装

```bash
git clone <your-repo-url>
cd TradingAgents_codex

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

`.env.example` 中保留了原版 provider 入口，适用于 `tradingagents analyze`。  
如果你主要使用 `tradingagents codex-analyze`：

- 不需要在项目里再填 `OPENAI_API_KEY`
- 只需要本机 `codex login` 已完成
- Codex 子进程会自动屏蔽非官方 `OPENAI_BASE_URL` 覆盖，避免把 Codex 登录态误发到第三方兼容网关

如果你仍然要运行原版 API 模式，再按需填写：

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`
- `XAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ALPHA_VANTAGE_API_KEY`

## 使用方式

### 1. 原版 API 模式

```bash
tradingagents analyze
```

### 2. Codex 交互模式

```bash
tradingagents codex-analyze
```

启动后会在终端里依次选择：

- ticker
- analysis date
- analysts
- Codex model
- output language
- reasoning effort
- full workflow / analysts only
- live search
- parallelism

### 3. Codex 非交互模式

完整链路：

```bash
tradingagents codex-analyze \
  --ticker AAPL \
  --analysis-date 2026-04-18 \
  --model gpt-5.4 \
  --output-language Chinese \
  --reasoning-effort medium \
  --search
```

只跑分析师角色的快速测试：

```bash
tradingagents codex-analyze \
  --ticker AAPL \
  --analysis-date 2026-04-18 \
  --analysts market,news \
  --analysts-only \
  --model gpt-5.4-mini \
  --reasoning-effort low \
  --max-parallel 1
```

查看帮助：

```bash
tradingagents --help
tradingagents codex-analyze --help
```

## Codex 模式的执行过程

`tradingagents codex-analyze` 会按下面的顺序运行：

1. 生成本次分析需要的 prompt packet、共享上下文和输出目录
2. 用本地数据连接器为 analyst 角色构建精简上下文
3. 对每个角色调用一次 `codex exec`
4. 将角色结果写入 JSON 和 Markdown
5. 汇总完整报告
6. 把最终报告翻译成中文，并保留英文原始副本

如果某个角色执行失败，可直接查看对应日志：

```text
codex_runs/<ticker>/<date>/logs/<role>.exec.log
codex_runs/<ticker>/<date>/logs/<role>.translated.exec.log
```

## 当前仓库的关键改动

- CLI 新增 `codex-analyze`
- CLI 补齐交互式选项选择
- 新增 `tradingagents/codex_workflow/`
- 新增中文翻译收尾阶段
- 新增 Codex 相关测试：
  - `tests/test_cli_codex.py`
  - `tests/test_codex_workflow.py`

## 测试

```bash
pytest tests/test_codex_workflow.py tests/test_cli_codex.py -q
```

## 已知说明

- Codex 模式和原版 API 模式是并存的，两条链路分别服务不同使用场景
- Codex 模式最终默认输出中文，但中间角色最初生成时仍可能先出现英文文件，翻译步骤结束后会覆盖为中文主文件
- `codex_runs/`、`.codex_project/`、本地 `.env` 都不应提交到公开仓库

## 致谢

- 上游项目：[`TauricResearch/TradingAgents`](https://github.com/TauricResearch/TradingAgents)
- 论文：[`TradingAgents: Multi-Agents LLM Financial Trading Framework`](https://arxiv.org/abs/2412.20138)

## License

继承仓库中的 [`LICENSE`](./LICENSE)。
