"""
Unit tests for Sinmate teacher batch ingestion, validation, and DPO generation.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scripts.ingest_teacher_batches import (
    CANONICAL_CATEGORIES,
    LITERARY_WORDS,
    bad_characters,
    build_system_prompt,
    count_sentences,
    detect_flags,
    ingest_batches,
    map_category,
    validate_dialogue,
)
from sinmate.brain.personas import PersonaManager, PersonaRole


class TestIngestTeacherBatches(unittest.TestCase):
    def test_count_sentences(self):
        # Ellipsis is a pause, not a sentence end
        self.assertEqual(count_sentences("හ්ම්ම්... මම මෙතන ඉන්නවා. බය වෙන්න එපා."), 2)
        self.assertEqual(count_sentences("හරි හරි."), 1)
        self.assertEqual(count_sentences("මේක පළවෙනි එක. මේක දෙවෙනි එක. මේක තුන්වෙනි එක."), 3)

    def test_bad_characters(self):
        # Pure Sinhala with punctuation allowed
        self.assertEqual(bad_characters("හරි මචං, කොහොමද?"), [])
        # Latin letters forbidden in assistant turns
        self.assertIn("a", bad_characters("හරි api යමු"))
        # Digits forbidden in assistant turns
        self.assertIn("1", bad_characters("වෙලාව 12 යි"))
        # Markdown forbidden
        self.assertIn("*", bad_characters("**හරි**"))
        # Brackets / parentheses forbidden
        self.assertIn("(", bad_characters("හරි (good)"))

    def test_spoken_vs_literary_sinhala(self):
        # Standalone literary words should be caught
        dialogue_literary = {
            "persona": "BEST_FRIEND",
            "input_type": "sinhala_unicode",
            "emotion": "neutral",
            "scenario": "Friend talking formally",
            "messages": [
                {"role": "user", "content": "කොහොමද මචං?"},
                {"role": "assistant", "content": "ඔබ පැමිණීම ගැන සතුටුයි."},
            ]
        }
        valid, errors = validate_dialogue(dialogue_literary)
        self.assertFalse(valid)
        self.assertTrue(any("contains literary Sinhala word 'ඔබ'" in e for e in errors))

        # Combining vowels like ඇති, නැති, ඔබාගෙන should NOT trigger false positive
        dialogue_combining = {
            "persona": "BEST_FRIEND",
            "input_type": "sinhala_unicode",
            "emotion": "neutral",
            "scenario": "Friend giving casual advice",
            "messages": [
                {"role": "user", "content": "මහන්සියි බං."},
                {"role": "assistant", "content": "දැන් ඔය වැඩ කළා ඇති. කකුල් දෙක වතුරේ ඔබාගෙන ඉන්න."},
            ]
        }
        valid, errors = validate_dialogue(dialogue_combining)
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_alternation_and_turn_rules(self):
        # Wrong role order
        d_bad_order = {
            "persona": "BEST_FRIEND",
            "input_type": "sinhala_unicode",
            "emotion": "neutral",
            "scenario": "Bad order",
            "messages": [
                {"role": "assistant", "content": "හෙලෝ"},
                {"role": "user", "content": "හායි"},
            ]
        }
        valid, errors = validate_dialogue(d_bad_order)
        self.assertFalse(valid)

        # Ends with user
        d_ends_user = {
            "persona": "BEST_FRIEND",
            "input_type": "sinhala_unicode",
            "emotion": "neutral",
            "scenario": "Ends with user",
            "messages": [
                {"role": "user", "content": "හායි"},
                {"role": "assistant", "content": "හෙලෝ."},
                {"role": "user", "content": "ආයෙත් මම"},
            ]
        }
        valid, errors = validate_dialogue(d_ends_user)
        self.assertFalse(valid)

    def test_category_mapping(self):
        self.assertEqual(map_category("work_stress"), "work_stress")
        self.assertEqual(map_category("office_overtime"), "work_stress")
        self.assertEqual(map_category("academic_writing"), "exam_and_study")
        self.assertEqual(map_category("baking_and_cooking"), "food_and_cravings")
        self.assertEqual(map_category("sports_and_matches"), "cricket_and_sports")
        self.assertIsNone(map_category("completely_random_unknown_category"))

    def test_detect_flags(self):
        # MOTHER_FIGURE using පුතේ
        d_mother = {
            "persona": "MOTHER_FIGURE",
            "messages": [
                {"role": "user", "content": "අම්මේ බඩගිනියි."},
                {"role": "assistant", "content": "කෑම ලෑස්තියි මගේ පුතේ."},
            ]
        }
        flags = detect_flags(d_mother)
        self.assertIn("gendered_mother_figure_putha_or_duwa", flags)

        # Gendered user assumption
        d_gender = {
            "persona": "SPECIAL_PARTNER",
            "messages": [
                {"role": "user", "content": "කේක් හැදුවා."},
                {"role": "assistant", "content": "මගේ කෙල්ලගේ වැඩ කොහොමත් ලස්සනයි."},
            ]
        }
        flags = detect_flags(d_gender)
        self.assertIn("gendered_user_assumption", flags)

        # Health claim
        d_health = {
            "persona": "MOTHER_FIGURE",
            "messages": [
                {"role": "user", "content": "උගුර කසනවා."},
                {"role": "assistant", "content": "කොත්තමල්ලි ටිකක් බීලා ඉන්න දරුවෝ."},
            ]
        }
        flags = detect_flags(d_health)
        self.assertIn("health_claim_or_remedy", flags)

        # Hearsay
        d_hearsay = {
            "persona": "BEST_FRIEND",
            "messages": [
                {"role": "user", "content": "අර කඩේ කොහොමද?"},
                {"role": "assistant", "content": "ඒකේ කෑම රසයිලු මචං."},
            ]
        }
        flags = detect_flags(d_hearsay)
        self.assertIn("hearsay_stated_as_fact", flags)

    def test_system_prompt_matches_compact_format(self):
        for role in PersonaRole:
            expected = PersonaManager(role).get_system_prompt(style="compact")
            generated = build_system_prompt(role.value)
            self.assertEqual(generated, expected)

    def test_full_pipeline_ingest_and_dpo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            accepted_file = tmp_path / "accepted.jsonl"
            rejected_file = tmp_path / "rejected.jsonl"

            # Create 4 sample dialogues across all 4 personas
            sample_dialogues = [
                {
                    "persona": "BEST_FRIEND",
                    "input_type": "sinhala_unicode",
                    "emotion": "neutral",
                    "category": "daily_life",
                    "scenario": "Friend chilling on rainy day",
                    "messages": [
                        {"role": "user", "content": "වැස්ස හින්දා කම්මැලියි බං."},
                        {"role": "assistant", "content": "තේ එකක් බීලා ෆිල්ම් එකක් බලපන්කෝ. මොකද හිතන්නේ?"}
                    ]
                },
                {
                    "persona": "SPECIAL_PARTNER",
                    "input_type": "singlish",
                    "emotion": "work_burnout_exhaustion",
                    "category": "office_overtime",
                    "scenario": "Partner working late at laptop",
                    "messages": [
                        {"role": "user", "content": "Ada wada wadi patiyo."},
                        {"role": "assistant", "content": "පොඩ්ඩක් ඇස් පියාගෙන ඉන්න මගේ රත්තරං. මම ඔයා ළඟ ඉන්නවා."}
                    ]
                },
                {
                    "persona": "MOTHER_FIGURE",
                    "input_type": "code_switched",
                    "emotion": "celebration_and_joy",
                    "category": "academic_success",
                    "scenario": "User passed exam with flying colors",
                    "messages": [
                        {"role": "user", "content": "Amma mama exam pass una!"},
                        {"role": "assistant", "content": "අනේ හරිම සතුටුයි මගේ දරුවෝ. ඔයා හොඳට මහන්සි වුණානේ."}
                    ]
                },
                {
                    "persona": "TEACHER",
                    "input_type": "sinhala_unicode",
                    "emotion": "panic_and_anxiety",
                    "category": "concept_explanation",
                    "scenario": "Student confused about programming concept",
                    "messages": [
                        {"role": "user", "content": "ගුරුතුමනි මේ කොටස තේරෙන්නේ නෑ."},
                        {"role": "assistant", "content": "කලබල වෙන්න එපා. අපි සරල උදාහරණයකින් ආයෙත් බලමුද?"}
                    ]
                },
            ]

            sample_rejected = [
                {"line": 1, "defect": "FORMAL_WRITTEN", "rejected": "ඔබ තේ පානය කරමින් චිත්‍රපටයක් නැරඹිය යුතුය."},
                {"line": 2, "defect": "TONE_DEAF", "rejected": "මටත් මහන්සියි, මට නිදාගන්න ඕනේ."},
                {"line": 3, "defect": "ROBOTIC_ASSISTANT", "rejected": "විභාගය සමත්වීම පිළිබඳ මගේ සුබපැතුම්."},
                {"line": 4, "defect": "TOO_LONG_LISTY", "rejected": "මුලින්ම පොත බලන්න. ඊළඟට නෝට්ස් ලියන්න. ඊටපස්සේ මට කියන්න."},
            ]

            with open(accepted_file, "w", encoding="utf-8") as f:
                for d in sample_dialogues:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")

            with open(rejected_file, "w", encoding="utf-8") as f:
                for r in sample_rejected:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            result = ingest_batches(
                input_paths=[accepted_file],
                rejected_path=rejected_file,
                val_ratio=0.25,
                seed=42,
                start_id=1,
            )

            self.assertEqual(result["accepted_count"], 4)
            self.assertEqual(result["rejected_count"], 0)
            self.assertEqual(len(result["dpo_pairs"]), 4)
            self.assertEqual(len(result["train_set"]), 3)
            self.assertEqual(len(result["val_set"]), 1)

            # Check that injected messages have system prompt first
            first_train = result["train_set"][0]
            self.assertEqual(first_train["messages"][0]["role"], "system")
            self.assertIn("You are Sinmate", first_train["messages"][0]["content"])
            self.assertTrue(first_train["id"].startswith("sinmate_"))

            # Check DPO pair structure
            first_dpo = result["dpo_pairs"][0]
            self.assertTrue(first_dpo["id"].startswith("sinmate_dpo_"))
            self.assertIn("prompt", first_dpo)
            self.assertIn("chosen", first_dpo)
            self.assertIn("rejected", first_dpo)
            self.assertEqual(first_dpo["defect"], "FORMAL_WRITTEN")


if __name__ == "__main__":
    unittest.main()
