"""
Unit tests for Sinmate Multi-Agent Orchestrator (agent_hub.py).
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_HUB = REPO_ROOT / "scripts" / "agent_hub.py"


class TestAgentHub(unittest.TestCase):
    def test_agent_hub_status(self):
        result = subprocess.run(
            [sys.executable, str(AGENT_HUB), "status"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SINMATE MULTI-AGENT STATE SNAPSHOT", result.stdout)
        self.assertIn("TASKS", result.stdout)

    def test_agent_hub_sync(self):
        result = subprocess.run(
            [sys.executable, str(AGENT_HUB), "sync"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue((REPO_ROOT / "AGENTS.md").exists())
        self.assertTrue((REPO_ROOT / "CLAUDE.md").exists())
        self.assertTrue((REPO_ROOT / "GEMINI.md").exists())
        self.assertTrue((REPO_ROOT / ".cursorrules").exists())
        self.assertTrue((REPO_ROOT / ".github" / "copilot-instructions.md").exists())

    def test_agent_hub_post(self):
        blackboard_path = REPO_ROOT / ".context" / "BLACKBOARD.md"
        orig_content = blackboard_path.read_text(encoding="utf-8")
        self.addCleanup(lambda: blackboard_path.write_text(orig_content, encoding="utf-8"))
        test_msg = "Automated test message for blackboard verification."
        result = subprocess.run(
            [sys.executable, str(AGENT_HUB), "post", "--agent", "TestRunner", "--msg", test_msg],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0)
        blackboard = blackboard_path.read_text(encoding="utf-8")
        self.assertIn(test_msg, blackboard)


if __name__ == "__main__":
    unittest.main()
