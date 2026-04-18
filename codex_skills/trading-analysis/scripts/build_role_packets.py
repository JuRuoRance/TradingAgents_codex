#!/usr/bin/env python3
"""Generate compact role packets for Codex-agent orchestration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tradingagents.codex_workflow.packets import build_packet_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--analysis-date", required=True)
    parser.add_argument("--analysts", default="market,news,social,fundamentals")
    parser.add_argument("--mode", default="compact", choices=["compact", "full"])
    parser.add_argument("--provider", default="codex")
    parser.add_argument("--base-url-env", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--include-synthesis", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    bundle = build_packet_bundle(
        ticker=args.ticker,
        analysis_date=args.analysis_date,
        analysts=args.analysts,
        mode=args.mode,
        provider=args.provider,
        base_url_env=args.base_url_env,
        notes=args.notes,
        include_synthesis=args.include_synthesis,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(bundle.run_dir)


if __name__ == "__main__":
    main()
