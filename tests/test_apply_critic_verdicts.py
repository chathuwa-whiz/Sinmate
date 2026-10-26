"""
Unit tests for scripts/apply_critic_verdicts.py: parsing messy critic replies and applying keep/fix/drop safely.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "apply_critic_verdicts.py"
spec = importlib.util.spec_from_file_location("apply_critic_verdicts", SCRIPT)
acv = importlib.util.module_from_spec(spec)
sys.modules["apply_critic_verdicts"] = acv
spec.loader.exec_module(acv)


def dialogue(user, assistant, persona="BEST_FRIEND"):
    return {
        "persona": persona,
        "input_type": "singlish",
        "emotion": "neutral",
        "category": "casual_chat",
        "scenario": "test",
        "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}],
    }


GOOD = "හරි හරි, ඉතින් කියන්නකෝ."
USER = "Miss, group project eke anith aya kisima wada kotasak karanne na!"


class TestParseVerdicts(unittest.TestCase):
    def test_jsonl_inside_code_fence_with_prose(self):
        text = (
            "Here you go:\n```jsonl\n"
            '{"line": 38, "verdict": "drop", "issues": ["TOO_LONG"]}\n'
            '{"line": 39, "verdict": "fix", "issues": [], "fixed_messages": [{"role": "user", "content": "x"}]},\n'
            "```\nHope that helps!"
        )
        verdicts, warnings = acv.parse_verdicts(text)
        self.assertEqual(sorted(verdicts), [38, 39])
        self.assertEqual(warnings, [])

    def test_pretty_printed_array(self):
        text = json.dumps([{"line": 1, "verdict": "keep"}, {"line": 2, "verdict": "drop"}], indent=2)
        verdicts, _ = acv.parse_verdicts(text)
        self.assertEqual({n: v["verdict"] for n, v in verdicts.items()}, {1: "keep", 2: "drop"})

    def test_broken_line_is_skipped_with_warning(self):
        text = '{"line": 1, "verdict": "drop"\n{"line": 2, "verdict": "keep"}\n'
        verdicts, warnings = acv.parse_verdicts(text)
        self.assertEqual(sorted(verdicts), [2])
        self.assertEqual(len(warnings), 1)

    def test_duplicate_line_uses_last(self):
        text = '{"line": 1, "verdict": "keep"}\n{"line": 1, "verdict": "drop"}'
        verdicts, warnings = acv.parse_verdicts(text)
        self.assertEqual(verdicts[1]["verdict"], "drop")
        self.assertTrue(warnings)


class TestRules(unittest.TestCase):
    def test_sentence_counting_ignores_ellipsis(self):
        self.assertEqual(count := acv.count_sentences("හ්ම්ම්... ඇත්තද? හරි."), 2, count)
        self.assertEqual(acv.count_sentences("එක. දෙක. තුන."), 3)

    def test_assistant_must_be_pure_sinhala(self):
        for bad in ["හරි wash කරන්න.", "හරි 2 වතාවක්.", "හරි 😊", "හරි **ඔව්**"]:
            self.assertTrue(acv.check_messages(dialogue(USER, bad)["messages"]), bad)
        self.assertEqual(acv.check_messages(dialogue(USER, GOOD)["messages"]), [])

    def test_user_turn_may_contain_latin(self):
        self.assertEqual(acv.check_messages(dialogue("Mata help ekak ona 123", GOOD)["messages"]), [])

    def test_structure_errors(self):
        self.assertTrue(acv.check_messages([]))
        self.assertTrue(acv.check_messages([{"role": "assistant", "content": GOOD}, {"role": "user", "content": "x"}]))


class TestDecide(unittest.TestCase):
    def setUp(self):
        self.original = dialogue(USER, "දිග අසාධාරණ පිළිතුරක්.")

    def fix(self, assistant, user=USER):
        return {
            "line": 1,
            "verdict": "fix",
            "issues": ["TOO_LONG"],
            "fixed_messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}],
        }

    def run_decide(self, votes, drop_if="any"):
        return acv.decide(1, self.original, votes, drop_if)

    def test_keep(self):
        status, final, _, _ = self.run_decide([{"verdict": "keep"}])
        self.assertEqual(status, "accepted-keep")

    def test_drop(self):
        status, final, note, issues = self.run_decide([{"verdict": "drop", "issues": ["FORMAL_REGISTER"]}])
        self.assertEqual((status, final, issues), ("rejected", None, ["FORMAL_REGISTER"]))
        self.assertIn("drop", note)

    def test_fix_replaces_assistant_and_keeps_original_user_turn(self):
        status, final, _, _ = self.run_decide([self.fix(GOOD, user=USER + " (reworded)")])
        self.assertEqual(status, "accepted-fix")
        self.assertEqual(final["messages"][1]["content"], GOOD)
        self.assertEqual(final["messages"][0]["content"], USER)
        self.assertEqual(final["persona"], "BEST_FRIEND")

    def test_fix_that_breaks_rules_is_rejected(self):
        status, final, note, _ = self.run_decide([self.fix("හරි wash කරන්න.")])
        self.assertEqual(status, "rejected")
        self.assertIn("breaks rules", note)

    def test_fix_for_a_different_line_is_rejected(self):
        status, _, note, _ = self.run_decide([self.fix(GOOD, user="Mage nangi ada exam ekata yanawa")])
        self.assertEqual(status, "rejected")
        self.assertIn("different line", note)

    def test_fix_with_wrong_turn_count_is_rejected(self):
        vote = self.fix(GOOD)
        vote["fixed_messages"].append({"role": "user", "content": "x"})
        self.assertEqual(self.run_decide([vote])[0], "rejected")

    def test_unusable_fix_is_rejected_even_when_another_critic_says_keep(self):
        status, _, _, _ = self.run_decide([self.fix("bad 😊"), {"verdict": "keep"}])
        self.assertEqual(status, "rejected")

    def test_second_critics_valid_fix_is_used(self):
        status, final, _, _ = self.run_decide([self.fix("bad 😊"), self.fix(GOOD)])
        self.assertEqual(status, "accepted-fix")
        self.assertEqual(final["messages"][1]["content"], GOOD)

    def test_drop_policy(self):
        votes = [{"verdict": "drop"}, {"verdict": "keep"}]
        self.assertEqual(self.run_decide(votes, "any")[0], "rejected")
        self.assertEqual(self.run_decide(votes, "majority")[0], "accepted-keep")
        self.assertEqual(self.run_decide(votes, "all")[0], "accepted-keep")

    def test_unknown_verdict_is_rejected(self):
        self.assertEqual(self.run_decide([{"verdict": "maybe"}])[0], "rejected")

    def test_output_is_nfc(self):
        decomposed = "කො" + GOOD  # ක + ෙ + ා decomposed
        self.original = dialogue(USER, decomposed)
        _, final, _, _ = self.run_decide([{"verdict": "keep"}])
        self.assertTrue(final["messages"][1]["content"].startswith("කො"))


class TestEndToEnd(unittest.TestCase):
    def test_cli_round_trip(self):
        import tempfile

        batch = [dialogue(USER, GOOD), dialogue("Mata bayai", "දිග අසාධාරණ.") , dialogue("Hi", "හරි wash කරන්න.")]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            batch_file = tmp / "raw.jsonl"
            batch_file.write_text("```json\n" + "\n".join(json.dumps(d, ensure_ascii=False) for d in batch) + "\n```\n", encoding="utf-8")
            critic_file = tmp / "critic.txt"
            critic_file.write_text('{"line": 2, "verdict": "drop", "issues": ["UNNATURAL_SINHALA"]}\n', encoding="utf-8")
            out = tmp / "out"
            argv = ["apply_critic_verdicts.py", str(critic_file), "--batch", str(batch_file), "--out-dir", str(out)]
            old = sys.argv
            sys.argv = argv
            try:
                self.assertEqual(acv.main(), 0)
            finally:
                sys.argv = old
            accepted = [json.loads(l) for l in (out / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
            rejected = [json.loads(l) for l in (out / "raw.rejected.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(accepted), 1)
            self.assertEqual([r["source_line"] for r in rejected], [2, 3])  # 2 dropped, 3 fails the Latin rule
            with self.assertRaises(SystemExit):  # refuses to overwrite
                sys.argv = argv
                try:
                    acv.main()
                finally:
                    sys.argv = old


if __name__ == "__main__":
    unittest.main()
