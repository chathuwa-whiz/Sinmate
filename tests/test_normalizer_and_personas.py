"""
Unit tests for Sinhala Unicode normalizer and persona prompt manager.
"""

import sys
import unittest
from pathlib import Path

# Add src to python path for testing
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sinmate.brain.normalizer import normalize_sinhala_text
from sinmate.brain.personas import PersonaManager, PersonaRole


class TestNormalizerAndPersonas(unittest.TestCase):
    def test_sinhala_nfc_normalization(self):
        raw = "කොළඹ"
        normalized = normalize_sinhala_text(raw)
        self.assertEqual(normalized, "කොළඹ")

    def test_sinhala_conjunct_preservation(self):
        # Rakaransaya: ප්‍ර (Pa + Hal + ZWJ + Ra)
        word = "ප්‍රශ්නය"
        normalized = normalize_sinhala_text(word)
        self.assertIn("ප්‍ර", normalized)

        # Yansaya: සත්‍ය (Sa + Ta + Hal + ZWJ + Ya)
        word_yan = "සත්‍ය"
        normalized_yan = normalize_sinhala_text(word_yan)
        self.assertIn("ත්‍ය", normalized_yan)

    def test_persona_manager_switching(self):
        manager = PersonaManager(default_role=PersonaRole.BEST_FRIEND)
        prompt_friend = manager.get_system_prompt()
        self.assertIn("[ROLE: BEST_FRIEND]", prompt_friend)
        self.assertIn("මචං", prompt_friend)

        manager.set_persona(PersonaRole.MOTHER_FIGURE)
        prompt_mother = manager.get_system_prompt()
        self.assertIn("[ROLE: MOTHER_FIGURE]", prompt_mother)
        self.assertIn("බත් කෑවද", prompt_mother)

        manager.set_persona(PersonaRole.TEACHER)
        prompt_teacher = manager.get_system_prompt(memory_context="User is studying Python AST.")
        self.assertIn("[ROLE: TEACHER]", prompt_teacher)
        self.assertIn("User is studying Python AST.", prompt_teacher)


if __name__ == "__main__":
    unittest.main()
