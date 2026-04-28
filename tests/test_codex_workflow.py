import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tradingagents.codex_workflow.packets import build_packet_bundle, default_run_dir
from tradingagents.codex_workflow.runner import (
    CodexExecutionError,
    clean_json_text,
    _build_codex_subprocess_env,
    _codex_failure_detail,
    _find_numeric_token_mismatches,
    _repair_numeric_token_mismatches,
    _run_codex_json_prompt,
    _schema_for_payload_shape,
)
from tradingagents.codex_workflow.schemas import schema_for_role


class CodexWorkflowTests(unittest.TestCase):
    def test_default_run_dir_points_to_codex_repo(self):
        path = default_run_dir("AAPL", "2026-04-17")
        self.assertIn("TradingAgents_codex/codex_runs/AAPL/2026-04-17", str(path))

    def test_build_packet_bundle_creates_new_artifact_layout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = build_packet_bundle(
                ticker="AAPL",
                analysis_date="2026-04-17",
                analysts="market,news",
                include_synthesis=True,
                output_dir=Path(tmpdir),
            )
            workflow = json.loads(bundle.workflow_path.read_text(encoding="utf-8"))
            self.assertEqual(workflow["analyst_roles"], ["market", "news"])
            self.assertTrue((bundle.prompts_dir / "market.md").exists())
            self.assertTrue((bundle.prompts_dir / "portfolio_manager.md").exists())
            self.assertTrue(bundle.contexts_dir.exists())
            self.assertTrue(bundle.logs_dir.exists())
            self.assertTrue(bundle.schemas_dir.exists())

    def test_clean_json_text_handles_fenced_output(self):
        raw = "```json\n{\"ok\": true}\n```\nextra"
        self.assertEqual(clean_json_text(raw), "{\"ok\": true}")

    def test_final_decision_schema_is_strict(self):
        schema = schema_for_role("portfolio_manager")
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("positioning", schema["properties"])

    def test_codex_subprocess_env_strips_gateway_override(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_BASE_URL": "https://api.chatanywhere.tech/v1",
                "TRADINGAGENTS_BACKEND_URL": "https://api.chatanywhere.tech/v1",
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            env = _build_codex_subprocess_env()

        self.assertNotIn("OPENAI_BASE_URL", env)
        self.assertNotIn("TRADINGAGENTS_BACKEND_URL", env)
        self.assertNotIn("OPENAI_API_KEY", env)

    def test_translation_schema_preserves_identity_fields(self):
        payload = {
            "role": "news",
            "ticker": "AAPL",
            "analysis_date": "2026-04-18",
            "summary": "English text",
        }
        schema = _schema_for_payload_shape(payload)
        self.assertEqual(schema["properties"]["role"]["const"], "news")
        self.assertEqual(schema["properties"]["ticker"]["const"], "AAPL")
        self.assertEqual(schema["properties"]["analysis_date"]["const"], "2026-04-18")

    def test_codex_subprocess_failure_raises_runtime_error_with_role(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            schema_path = tmpdir_path / "schema.json"
            output_path = tmpdir_path / "output.json"
            log_path = tmpdir_path / "exec.log"
            schema_path.write_text("{}", encoding="utf-8")

            with patch("tradingagents.codex_workflow.runner.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stdout = "stdout"
                mock_run.return_value.stderr = "stderr"

                with self.assertRaises(CodexExecutionError) as exc:
                    _run_codex_json_prompt(
                        role="news",
                        prompt="test prompt",
                        schema_path=schema_path,
                        output_path=output_path,
                        log_path=log_path,
                        model="gpt-5.4-mini",
                        reasoning_effort="low",
                        use_search=False,
                        command_path=Path("/bin/echo"),
                    )

        self.assertIn("Codex role 'news' failed", str(exc.exception))
        self.assertIn(str(log_path), str(exc.exception))
        self.assertEqual(exc.exception.role, "news")

    def test_codex_usage_limit_failure_detail_is_actionable(self):
        detail = _codex_failure_detail(
            "ERROR: You've hit your usage limit. "
            "Upgrade to Pro or try again at 7:19 PM."
        )

        self.assertIn("usage limit", detail)
        self.assertIn("7:19 PM", detail)
        self.assertIn("--max-parallel", detail)

    def test_translation_numeric_integrity_detects_changed_price_range(self):
        source = {
            "positioning": {
                "entry": "Do not chase near 979.07; add only near 895.74-900.37."
            }
        }
        translated = {
            "positioning": {
                "entry": "不要追高；若价格回落至 $75-$82 区间并企稳。"
            }
        }

        mismatches = _find_numeric_token_mismatches(source, translated)

        self.assertEqual(mismatches[0]["path"], "$.positioning.entry")

    def test_translation_numeric_repair_restores_source_string(self):
        source = {"entry": "Do not chase near 979.07; add only near 895.74-900.37."}
        translated = {"entry": "不要追高；若价格回落至 $75-$82 区间并企稳。"}

        repaired, paths = _repair_numeric_token_mismatches(source, translated)

        self.assertEqual(paths, ["$.entry"])
        self.assertEqual(repaired["entry"], source["entry"])


if __name__ == "__main__":
    unittest.main()
