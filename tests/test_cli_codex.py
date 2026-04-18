import unittest

from cli.utils import get_codex_model_choices


class CodexCliTests(unittest.TestCase):
    def test_codex_model_choices_include_frontier_and_codex_models(self):
        values = [value for _, value in get_codex_model_choices()]
        self.assertIn("gpt-5.4", values)
        self.assertIn("gpt-5.3-codex", values)


if __name__ == "__main__":
    unittest.main()
