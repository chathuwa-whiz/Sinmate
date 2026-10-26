"""
Unit tests for Sinhala Conversational Dataset Generator and Validator.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = REPO_ROOT / "data" / "seed_dialogues.jsonl"
SCHEMA_FILE = REPO_ROOT / "data" / "schema.json"


class TestDatasetGenerator(unittest.TestCase):
    def test_schema_file_exists(self):
        self.assertTrue(SCHEMA_FILE.exists())
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema["title"], "SinmateConversationalDialogue")

    def test_seed_dialogues_validity(self):
        self.assertTrue(SEED_FILE.exists())
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            dialogues = [json.loads(line) for line in f if line.strip()]

        self.assertGreaterEqual(len(dialogues), 12)
        valid_personas = {"BEST_FRIEND", "SPECIAL_PARTNER", "MOTHER_FIGURE", "TEACHER"}
        valid_inputs = {"sinhala_unicode", "singlish", "code_switched"}

        for d in dialogues:
            self.assertIn("id", d)
            self.assertIn(d["persona"], valid_personas)
            self.assertIn(d["input_type"], valid_inputs)
            self.assertGreaterEqual(len(d["messages"]), 2)
            # Ensure assistant turn exists and has Sinhala or filler content
            assistant_turn = next(m for m in d["messages"] if m["role"] == "assistant")
            self.assertTrue(len(assistant_turn["content"]) > 0)


if __name__ == "__main__":
    unittest.main()
