import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tradingagents.codex_workflow.packets import build_packet_bundle, default_run_dir
from tradingagents.codex_workflow.runner import (
    clean_json_text,
    _build_codex_subprocess_env,
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


if __name__ == "__main__":
    unittest.main()
