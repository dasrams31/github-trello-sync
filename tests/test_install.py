import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import install  # noqa: E402


class WorkflowTemplateTest(unittest.TestCase):
    def test_writes_only_filled_settings_and_quotes_values(self):
        text = install.workflow(
            "dasrams31/github-trello-sync@v1",
            "main, dev's",
            {"board-id": "B1", "done-list-id": "D1", "progress-list-id": "", "authors": "Rama, O'Neil"},
            ["FE: blade, css"],
        )

        self.assertIn("branches: ['main', 'dev''s']", text)
        self.assertIn("- uses: dasrams31/github-trello-sync@v1", text)
        self.assertIn("trello-token: ${{ secrets.TRELLO_TOKEN }}", text)
        self.assertIn("done-list-id: 'D1'", text)
        self.assertIn("authors: 'Rama, O''Neil'", text)
        self.assertNotIn("progress-list-id", text)
        self.assertIn("categories: |\n            FE: blade, css", text)

    def test_all_branches_by_default(self):
        self.assertIn("branches: ['**']", install.workflow("a@v1", "**", {"done-list-id": "D"}, []))


if __name__ == "__main__":
    unittest.main()
