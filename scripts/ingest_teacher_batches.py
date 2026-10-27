#!/usr/bin/env python3
"""
Sinmate Teacher-Batch Ingest & Dataset Preparation Script.

Ingests reviewed teacher-LLM dialogues (output of scripts/apply_critic_verdicts.py,
e.g. data/accepted_dialogs.jsonl), validates schema and mechanical spoken-Sinhala rules,
maps free-text categories onto the 9 canonical ADR-006 categories (or drops unmapped ones),
flags lines with hearsay, health claims, or gendered terms for human review,
deduplicates by user opening and scenario, injects the exact COMPACT_PERSONA_LINES
system prompt per persona, assigns sequential IDs (sinmate_00001, ...),
splits into data/train.jsonl and data/val.jsonl, builds DPO pairs from rejected replies,
and prints distribution statistics against the target mix from docs/dataset_generation_prompts.md.

Usage:
    python scripts/ingest_teacher_batches.py data/accepted_dialogs.jsonl \\
        --rejected data/rejected_dialogs.jsonl \\
        --train-out data/train.jsonl \\
        --val-out data/val.jsonl \\
        --dpo-out data/dpo.jsonl \\
        --report-out data/ingest_report.md
"""

import argparse
import difflib
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from sinmate.brain.normalizer import normalize_sinhala_text
except ImportError:
    def normalize_sinhala_text(text: str) -> str:
        return unicodedata.normalize("NFC", text).strip()

try:
    from sinmate.brain.personas import (
        PersonaRole,
        COMPACT_PERSONA_LINES,
        SINMATE_IDENTITY,
    )
except ImportError:
    class PersonaRole:
        BEST_FRIEND = "BEST_FRIEND"
        SPECIAL_PARTNER = "SPECIAL_PARTNER"
        MOTHER_FIGURE = "MOTHER_FIGURE"
        TEACHER = "TEACHER"

    SINMATE_IDENTITY = (
        "You are Sinmate, an affectionate, emotionally intelligent native Sinhala companion sitting right beside the user."
    )
    COMPACT_PERSONA_LINES = {
        PersonaRole.BEST_FRIEND: "You are the user's closest best friend. Responses must strictly be 1-2 spoken colloquial sentences with Sri Lankan fillers.",
        PersonaRole.SPECIAL_PARTNER: "You are the user's loving partner. Soft, warm tone. Responses strictly 1-2 spoken sentences.",
        PersonaRole.MOTHER_FIGURE: "You are a warm, nurturing maternal figure. Protective, gentle, caring, concerned about health, meals, and rest. Responses strictly 1-2 spoken colloquial sentences.",
        PersonaRole.TEACHER: "You are a patient, inspiring mentor. Responses strictly 1-2 spoken sentences.",
    }


# ---------------------------------------------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------------------------------------------

MAX_SENTENCES = 2
MAX_WORDS = 35

VALID_PERSONAS = {"BEST_FRIEND", "SPECIAL_PARTNER", "MOTHER_FIGURE", "TEACHER"}

INPUT_TYPE_MAP = {
    "sinhala_unicode": "sinhala_unicode",
    "singlish": "singlish",
    "code_switched": "code_switched",
    "mixed_script": "code_switched",
}

VALID_EMOTIONS = {
    "grief_and_loss",
    "panic_and_anxiety",
    "work_burnout_exhaustion",
    "frustration_and_anger",
    "celebration_and_joy",
    "neutral",
    "crisis_support",
    "identity_honesty",
}

# The 9 canonical ADR-006 categories
CANONICAL_CATEGORIES = {
    "work_stress",
    "tech_and_coding",
    "exam_and_study",
    "food_and_cravings",
    "commute_and_traffic",
    "family_and_home",
    "cricket_and_sports",
    "heartbreak_and_crush",
    "late_night_insomnia",
}

CATEGORY_SYNONYMS = {
    # work_stress
    "office_overtime": "work_stress",
    "late_night_work": "work_stress",
    "job_interview": "work_stress",
    "career_wins": "work_stress",
    "time_management": "work_stress",
    # tech_and_coding
    "computing_concepts": "tech_and_coding",
    "tech_and_internet": "tech_and_coding",
    "tech_troubles": "tech_and_coding",
    "coding_help": "tech_and_coding",
    # exam_and_study
    "academic_success": "exam_and_study",
    "academic_writing": "exam_and_study",
    "campus_life": "exam_and_study",
    "exam_preparation": "exam_and_study",
    "group_projects": "exam_and_study",
    "study_environment": "exam_and_study",
    "study_habits": "exam_and_study",
    "study_motivation": "exam_and_study",
    "math_concepts": "exam_and_study",
    "physics_concepts": "exam_and_study",
    "biology_concepts": "exam_and_study",
    "economics_concepts": "exam_and_study",
    "geography_concepts": "exam_and_study",
    "science_concepts": "exam_and_study",
    "concept_explanation": "exam_and_study",
    "language_learning": "exam_and_study",
    "followup_quiz": "exam_and_study",
    # food_and_cravings
    "food_and_cooking": "food_and_cravings",
    "baking_and_cooking": "food_and_cravings",
    "cooking_mishaps": "food_and_cravings",
    "cooking_success": "food_and_cravings",
    "food_and_dining": "food_and_cravings",
    "food_and_hangouts": "food_and_cravings",
    "lunch_break": "food_and_cravings",
    "grocery_shopping": "food_and_cravings",
    "cravings": "food_and_cravings",
    # commute_and_traffic
    "travel_and_commute": "commute_and_traffic",
    "travel_fatigue": "commute_and_traffic",
    "vehicle_and_commute": "commute_and_traffic",
    # family_and_home
    "family_events": "family_and_home",
    "gardening_and_home": "family_and_home",
    "household_chores": "family_and_home",
    "household_cleaning": "family_and_home",
    "household_issues": "family_and_home",
    # cricket_and_sports
    "sports_and_matches": "cricket_and_sports",
    "cricket": "cricket_and_sports",
    # heartbreak_and_crush
    "crush": "heartbreak_and_crush",
    "dating": "heartbreak_and_crush",
    "breakup": "heartbreak_and_crush",
    "missing_you": "heartbreak_and_crush",
    # late_night_insomnia
    "late_night": "late_night_insomnia",
    "insomnia": "late_night_insomnia",
}

TARGET_MIX = {
    "persona": {
        "BEST_FRIEND": 0.27,
        "SPECIAL_PARTNER": 0.25,
        "MOTHER_FIGURE": 0.23,
        "TEACHER": 0.25,
    },
    "input_type": {
        "sinhala_unicode": 0.45,
        "singlish": 0.35,
        "code_switched": 0.20,
    },
    "emotion": {
        "neutral": 0.36,
        "work_burnout_exhaustion": 0.15,
        "celebration_and_joy": 0.15,
        "panic_and_anxiety": 0.12,
        "frustration_and_anger": 0.12,
        "grief_and_loss": 0.08,
        "crisis_support": 0.02,
    },
    "exchanges": {
        "1": 0.50,
        "2": 0.30,
        "3+": 0.20,
    },
}

_ELLIPSIS = re.compile(r"\.{2,}|…")
_SENTENCE_END = re.compile(r"[.?!]+\s*")
_MARKDOWN_CHARS = set("*#_`~|<>[]{}\\")

SINHALA_CHAR_CLASS = r"[\u0D80-\u0DFF\u200c\u200d]"

# Formal / literary Sinhala markers that should not appear in assistant spoken turns
LITERARY_WORDS = [
    "ඔබ",
    "ඔබට",
    "ඔබගේ",
    "කෙසේද",
    "ඇත",
    "නැත",
    "නොවේ",
    "කරයි",
    "කරමි",
    "කරන්නේය",
    "යුතුය",
    "හැකිය",
    "එබැවින්",
    "එනිසා",
    "පිළිබඳව",
    "නමුත්",
    "උපකාර",
]

LITERARY_REGEX = re.compile(
    rf"(?<!{SINHALA_CHAR_CLASS})(" + "|".join(re.escape(w) for w in LITERARY_WORDS) + rf")(?!{SINHALA_CHAR_CLASS})"
)

GENDERED_MOTHER_REGEX = re.compile(
    rf"(?<!{SINHALA_CHAR_CLASS})(පුතේ|පුතා|දුව|දුවේ)(?!{SINHALA_CHAR_CLASS})"
)

HEARSAY_REGEX = re.compile(
    rf"(?<!{SINHALA_CHAR_CLASS}){SINHALA_CHAR_CLASS}+ලු(?!{SINHALA_CHAR_CLASS})|"
    r"(කියලානේ කිව්වේ|ආරංචියි|කියනවා ඇහුණා)"
)

PRICES_REGEX = re.compile(
    rf"(?<!{SINHALA_CHAR_CLASS})(රුපියල්|රු\.|සීයට|දාහක්)(?!{SINHALA_CHAR_CLASS})"
)


# ---------------------------------------------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------------------------------------------

def nfc(text: str) -> str:
    """Normalize text to Unicode NFC and clean ZWJ."""
    return normalize_sinhala_text(text)


def count_sentences(text: str) -> int:
    """Count sentences treating ellipsis as a spoken pause rather than a terminator."""
    cleaned = _ELLIPSIS.sub(" ", text)
    return len([part for part in _SENTENCE_END.split(cleaned) if part.strip()])


def bad_characters(text: str) -> List[str]:
    """Find characters in an assistant reply that Sinhala VITS TTS cannot voice."""
    found = []
    for ch in text:
        in_sinhala_block = "඀" <= ch <= "෿"
        if in_sinhala_block or ch in "‌‍" or ch.isspace():
            continue
        category = unicodedata.category(ch)
        if ch.isalpha() or ch.isdigit() or category in ("So", "Sk", "Cs", "Co", "Cn") or ch in _MARKDOWN_CHARS:
            found.append(ch)
        elif ord(ch) > 0xFFFF:
            found.append(ch)
        elif ch in "()[]{}\"“”«»":
            found.append(ch)
    return found


def map_category(raw_category: Optional[str]) -> Optional[str]:
    """Map free-text category to canonical ADR-006 category, or None if unmapped."""
    if not raw_category or not isinstance(raw_category, str):
        return None
    cleaned = raw_category.strip().lower()
    if cleaned in CANONICAL_CATEGORIES:
        return cleaned
    if cleaned in CATEGORY_SYNONYMS:
        return CATEGORY_SYNONYMS[cleaned]
    return None


def detect_flags(dialogue: Dict[str, Any]) -> List[str]:
    """
    Detect conversational cues requiring human review:
    - gendered assumptions (MOTHER_FIGURE using පුතේ vs දරුවෝ, or gender assumptions like කෙල්ල/කොල්ලා)
    - health claims or medical home-remedy instructions
    - hearsay stated as fact
    - suspicious clumsy idioms
    - named celebrities or specific monetary statistics
    """
    flags = []
    persona = dialogue.get("persona", "")
    messages = dialogue.get("messages", [])

    for i, msg in enumerate(messages):
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "assistant":
            # Gendered terms check
            if persona == "MOTHER_FIGURE":
                if GENDERED_MOTHER_REGEX.search(content):
                    flags.append("gendered_mother_figure_putha_or_duwa")

            if re.search(rf"(?<!{SINHALA_CHAR_CLASS})(මගේ කෙල්ල|මගේ කොල්ලා|කෙල්ලගේ|කොල්ලාගේ)(?!{SINHALA_CHAR_CLASS})", content):
                flags.append("gendered_user_assumption")

            # Health claims & home remedies
            if re.search(r"(ලුණු කැට|ලුණු ටිකක්|කොත්තමල්ලි|පැනඩෝල්|උගුර හෝදන්න|තම්බගන්න|බෙහෙත්|මාත්‍රාව)", content):
                flags.append("health_claim_or_remedy")

            # Hearsay stated as fact
            if HEARSAY_REGEX.search(content):
                flags.append("hearsay_stated_as_fact")

            # Clumsy / odd idioms flagged in review
            if "ඇඟට ලේ ටිකක් ඉනුවේ" in content:
                flags.append("clumsy_idiom_le_inuwe")
            if "හාහාපුරා" in content:
                flags.append("archaic_phrase_hahapura")
            if "මාළුපිනි" in content:
                flags.append("literary_malupini")

            # Specific monetary amounts or statistics
            if PRICES_REGEX.search(content):
                flags.append("specific_prices_or_stats")

        # Mention of real persons / singers
        if re.search(r"\b(Milton Mallawarachchi|මිල්ටන් මල්ලවාරච්චි|ජෝතිපාල|Jothipala)\b", content, re.IGNORECASE):
            flags.append("real_celebrity_named")

    return sorted(set(flags))


def validate_dialogue(
    dialogue: Dict[str, Any],
    require_all_fields: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validates a dialogue dictionary against Sinmate schema & mechanical rules.
    Returns (is_valid, error_reasons).
    """
    errors: List[str] = []

    if not isinstance(dialogue, dict):
        return False, ["dialogue is not a JSON object"]

    # Persona
    persona = dialogue.get("persona")
    if persona not in VALID_PERSONAS:
        errors.append(f"invalid persona: {persona!r}")

    # Input type
    input_type = dialogue.get("input_type")
    if input_type not in INPUT_TYPE_MAP:
        errors.append(f"invalid input_type: {input_type!r}")

    # Emotion
    emotion = dialogue.get("emotion")
    if emotion not in VALID_EMOTIONS:
        errors.append(f"invalid emotion: {emotion!r}")

    # Scenario
    scenario = dialogue.get("scenario")
    if require_all_fields:
        if not isinstance(scenario, str) or not scenario.strip():
            errors.append("missing or empty scenario")

    # Messages
    messages = dialogue.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        errors.append("messages must be a list with at least 2 turns")
        return False, errors

    # Check alternation: user -> assistant -> user -> assistant
    for i, msg in enumerate(messages):
        expected_role = "user" if i % 2 == 0 else "assistant"
        if not isinstance(msg, dict):
            errors.append(f"turn {i + 1} is not an object")
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role != expected_role:
            errors.append(f"turn {i + 1} has role {role!r}, expected {expected_role!r}")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"turn {i + 1} is empty")

    if messages[-1].get("role") != "assistant":
        errors.append("dialogue must end with an assistant turn")

    # Assistant turn specific rules
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        bad = bad_characters(content)
        if bad:
            errors.append(f"turn {i + 1}: forbidden characters {''.join(sorted(set(bad)))[:12]!r}")
        sentences = count_sentences(content)
        if sentences > MAX_SENTENCES:
            errors.append(f"turn {i + 1}: more than {MAX_SENTENCES} sentences ({sentences})")
        words = len(content.split())
        if words > MAX_WORDS:
            errors.append(f"turn {i + 1}: more than {MAX_WORDS} words ({words})")

        # Check literary written words using Sinhala character lookaround
        lit_match = LITERARY_REGEX.search(content)
        if lit_match:
            errors.append(f"turn {i + 1}: contains literary Sinhala word {lit_match.group(0)!r}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------------------------------------------
# Ingest Engine
# ---------------------------------------------------------------------------------------------------------------

def load_jsonl_lines(path: Path) -> List[Tuple[int, str, Dict[str, Any]]]:
    """Reads a JSONL file, ignoring markdown code fences and empty lines. Returns (line_no, raw, obj)."""
    items = []
    line_no = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line_no += 1
            line = raw_line.strip().rstrip(",")
            if not line or line.startswith("```"):
                continue
            try:
                obj = json.loads(line)
                items.append((line_no, raw_line.strip(), obj))
            except Exception as e:
                items.append((line_no, raw_line.strip(), {"__parse_error__": str(e)}))
    return items


def load_rejected_dialogues(path: Optional[Path]) -> Dict[int, Dict[str, Any]]:
    """Loads rejected dialogues map: line_number / position -> rejected_dict."""
    if not path or not path.exists():
        return {}
    rejected_map = {}
    items = load_jsonl_lines(path)
    for idx, (line_no, raw, obj) in enumerate(items, start=1):
        if "__parse_error__" in obj:
            continue
        line_idx = obj.get("line")
        if isinstance(line_idx, int) and line_idx not in rejected_map:
            rejected_map[line_idx] = obj
        else:
            rejected_map[idx] = obj
    return rejected_map


def build_system_prompt(persona: str) -> str:
    """Builds the exact compact system prompt matching COMPACT_PERSONA_LINES."""
    role = PersonaRole(persona) if hasattr(PersonaRole, persona) else persona
    role_key = persona
    compact_line = COMPACT_PERSONA_LINES.get(role) or COMPACT_PERSONA_LINES.get(role_key, "")
    return f"{SINMATE_IDENTITY}\n[ROLE: {persona}]\n{compact_line}"


def ingest_batches(
    input_paths: List[Path],
    rejected_path: Optional[Path] = None,
    val_ratio: float = 0.1,
    seed: int = 42,
    start_id: int = 1,
    drop_unmapped_categories: bool = True,
    flag_only: bool = True,
) -> Dict[str, Any]:
    """
    Main ingestion pipeline:
    - Ingests and validates dialogues
    - Applies NFC normalization
    - Categorizes and maps ADR-006 categories
    - Detects review flags
    - Deduplicates by opener and scenario
    - Injects compact system prompt
    - Builds train/val split and DPO pairs
    """
    random.seed(seed)
    accepted_dialogues: List[Dict[str, Any]] = []
    rejected_items: List[Dict[str, Any]] = []
    all_flags: List[Dict[str, Any]] = []

    seen_openers: Set[str] = set()
    seen_scenarios: Set[str] = set()

    # Load rejected file for DPO if present
    rejected_by_line = load_rejected_dialogues(rejected_path)

    id_counter = start_id
    total_raw_count = 0

    for input_file in input_paths:
        lines = load_jsonl_lines(input_file)
        file_dialogue_idx = 0

        for line_no, raw_text, obj in lines:
            total_raw_count += 1
            file_dialogue_idx += 1

            if "__parse_error__" in obj:
                rejected_items.append({
                    "source_file": str(input_file),
                    "line": line_no,
                    "reason": f"JSON parse error: {obj['__parse_error__']}",
                    "raw": raw_text
                })
                continue

            # Basic validation
            valid, errors = validate_dialogue(obj)
            if not valid:
                rejected_items.append({
                    "source_file": str(input_file),
                    "line": line_no,
                    "reason": "; ".join(errors),
                    "raw": obj
                })
                continue

            # NFC Normalization
            persona = obj["persona"]
            input_type = INPUT_TYPE_MAP[obj["input_type"]]
            emotion = obj["emotion"]
            scenario = nfc(obj.get("scenario", "")).strip()

            norm_messages = []
            for msg in obj["messages"]:
                norm_messages.append({
                    "role": msg["role"],
                    "content": nfc(msg["content"]).strip()
                })

            # Opener and scenario deduplication
            first_user_text = norm_messages[0]["content"].strip().lower()
            opener_key = re.sub(r"\s+", " ", first_user_text)
            scenario_key = re.sub(r"\s+", " ", scenario.lower())

            if opener_key in seen_openers:
                rejected_items.append({
                    "source_file": str(input_file),
                    "line": line_no,
                    "reason": f"Duplicate user opener: {opener_key[:50]!r}",
                    "raw": obj
                })
                continue

            if scenario_key and scenario_key in seen_scenarios:
                rejected_items.append({
                    "source_file": str(input_file),
                    "line": line_no,
                    "reason": f"Duplicate scenario: {scenario_key[:50]!r}",
                    "raw": obj
                })
                continue

            seen_openers.add(opener_key)
            if scenario_key:
                seen_scenarios.add(scenario_key)

            # Category mapping
            raw_cat = obj.get("category")
            mapped_cat = map_category(raw_cat)
            category_val = mapped_cat if mapped_cat else (None if drop_unmapped_categories else raw_cat)

            # Detect flags for review
            flags = detect_flags({
                "persona": persona,
                "messages": norm_messages,
                "category": raw_cat
            })

            dialogue_id = f"sinmate_{id_counter:05d}"
            id_counter += 1

            if flags:
                all_flags.append({
                    "id": dialogue_id,
                    "file": str(input_file),
                    "line": file_dialogue_idx,
                    "scenario": scenario,
                    "flags": flags
                })

            # System prompt injection
            system_msg = {
                "role": "system",
                "content": build_system_prompt(persona)
            }
            final_messages = [system_msg] + norm_messages

            out_dialogue: Dict[str, Any] = {
                "id": dialogue_id,
                "persona": persona,
                "input_type": input_type,
                "emotion": emotion,
                "scenario": scenario,
                "messages": final_messages,
            }
            if category_val is not None:
                out_dialogue["category"] = category_val

            # Store extra metadata for tracking/pairing
            out_dialogue["_file_dialogue_idx"] = file_dialogue_idx
            out_dialogue["_source_file"] = str(input_file)
            out_dialogue["_flags"] = flags

            accepted_dialogues.append(out_dialogue)

    # Build DPO preference pairs
    dpo_pairs: List[Dict[str, Any]] = []
    dpo_counter = 1

    for accepted in accepted_dialogues:
        line_idx = accepted.get("_file_dialogue_idx")
        rejected_entry = rejected_by_line.get(line_idx)
        if not rejected_entry:
            continue

        rejected_text = nfc(rejected_entry.get("rejected", "")).strip()
        defect = rejected_entry.get("defect", "UNSPECIFIED")
        if not rejected_text:
            continue

        # Last assistant turn is chosen
        chosen_turn = accepted["messages"][-1]
        chosen_text = chosen_turn["content"]
        prompt_messages = accepted["messages"][:-1]

        dpo_pair = {
            "id": f"sinmate_dpo_{dpo_counter:05d}",
            "dialogue_id": accepted["id"],
            "persona": accepted["persona"],
            "input_type": accepted["input_type"],
            "emotion": accepted["emotion"],
            "defect": defect,
            "prompt": prompt_messages,
            "chosen": [{"role": "assistant", "content": chosen_text}],
            "rejected": [{"role": "assistant", "content": rejected_text}],
            "chosen_text": chosen_text,
            "rejected_text": rejected_text
        }
        dpo_pairs.append(dpo_pair)
        dpo_counter += 1

    # Train / Val split
    # Strip internal keys before saving
    clean_accepted = []
    for d in accepted_dialogues:
        item = {k: v for k, v in d.items() if not k.startswith("_")}
        clean_accepted.append(item)

    shuffled = list(clean_accepted)
    random.shuffle(shuffled)

    val_count = int(len(shuffled) * val_ratio)
    val_set = shuffled[:val_count]
    train_set = shuffled[val_count:]

    return {
        "total_raw": total_raw_count,
        "accepted_count": len(clean_accepted),
        "rejected_count": len(rejected_items),
        "train_set": train_set,
        "val_set": val_set,
        "dpo_pairs": dpo_pairs,
        "rejected_items": rejected_items,
        "flags": all_flags,
    }


# ---------------------------------------------------------------------------------------------------------------
# Target Mix & Reporting
# ---------------------------------------------------------------------------------------------------------------

def format_stats_report(result: Dict[str, Any]) -> str:
    """Formats a detailed report comparing current dataset against target distribution."""
    total = result["accepted_count"]
    if total == 0:
        return "No dialogues accepted.\n"

    all_accepted = result["train_set"] + result["val_set"]
    lines = []
    lines.append("# Sinmate Teacher Ingest Report")
    lines.append(f"\n- **Total Raw Inputs**: {result['total_raw']}")
    lines.append(f"- **Accepted**: {total} ({len(result['train_set'])} train, {len(result['val_set'])} val)")
    lines.append(f"- **Rejected**: {result['rejected_count']}")
    lines.append(f"- **DPO Preference Pairs**: {len(result['dpo_pairs'])}")
    lines.append(f"- **Flagged for Review**: {len(result['flags'])}")
    lines.append("\n---\n")

    # Persona distribution
    lines.append("### 1. Persona Distribution")
    lines.append("| Persona | Count | Current % | Target % | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    p_counts = Counter(d["persona"] for d in all_accepted)
    for p, target_pct in TARGET_MIX["persona"].items():
        count = p_counts.get(p, 0)
        curr_pct = count / total
        diff = curr_pct - target_pct
        status = "✅ OK" if abs(diff) <= 0.08 else ("⚠️ Low" if diff < 0 else "ℹ️ High")
        lines.append(f"| `{p}` | {count} | {curr_pct:.1%} | {target_pct:.1%} | {status} |")

    # Input Type distribution
    lines.append("\n### 2. Input Type Distribution")
    lines.append("| Input Type | Count | Current % | Target % | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    inp_counts = Counter(d["input_type"] for d in all_accepted)
    for inp, target_pct in TARGET_MIX["input_type"].items():
        count = inp_counts.get(inp, 0)
        curr_pct = count / total
        diff = curr_pct - target_pct
        status = "✅ OK" if abs(diff) <= 0.08 else ("⚠️ Low" if diff < 0 else "ℹ️ High")
        lines.append(f"| `{inp}` | {count} | {curr_pct:.1%} | {target_pct:.1%} | {status} |")

    # Emotion distribution
    lines.append("\n### 3. Emotion Distribution")
    lines.append("| Emotion | Count | Current % | Target % | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    emo_counts = Counter(d["emotion"] for d in all_accepted)
    for emo, target_pct in TARGET_MIX["emotion"].items():
        count = emo_counts.get(emo, 0)
        curr_pct = count / total
        diff = curr_pct - target_pct
        status = "🚨 ZERO" if count == 0 else ("✅ OK" if abs(diff) <= 0.08 else ("⚠️ Low" if diff < 0 else "ℹ️ High"))
        lines.append(f"| `{emo}` | {count} | {curr_pct:.1%} | {target_pct:.1%} | {status} |")

    # Exchanges distribution
    lines.append("\n### 4. Exchange Length Distribution")
    lines.append("| Exchanges | Count | Current % | Target % | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    # Number of exchanges = (len(messages) - 1) // 2 (since msg 0 is system)
    ex_counts = Counter()
    for d in all_accepted:
        turns = (len(d["messages"]) - 1) // 2
        bucket = "1" if turns == 1 else ("2" if turns == 2 else "3+")
        ex_counts[bucket] += 1
    for bucket, target_pct in TARGET_MIX["exchanges"].items():
        count = ex_counts.get(bucket, 0)
        curr_pct = count / total
        status = "✅ OK" if abs(curr_pct - target_pct) <= 0.1 else "ℹ️ Imbalanced"
        lines.append(f"| `{bucket}` exchange(s) | {count} | {curr_pct:.1%} | {target_pct:.1%} | {status} |")

    # Category Mapping distribution
    lines.append("\n### 5. ADR-006 Category Distribution")
    cat_counts = Counter(d.get("category", "<unmapped/dropped>") for d in all_accepted)
    lines.append("| Category | Count | Share |")
    lines.append("| :--- | :--- | :--- |")
    for cat, c in cat_counts.most_common():
        lines.append(f"| `{cat}` | {c} | {c / total:.1%} |")

    # Flagged lines for review
    lines.append("\n### 6. Flagged Dialogues for Human Review")
    if not result["flags"]:
        lines.append("No dialogues flagged for review.")
    else:
        lines.append(f"Found {len(result['flags'])} flagged dialogue(s):\n")
        lines.append("| ID | File:Line | Scenario | Flags |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for flag_item in result["flags"][:30]:  # show up to 30
            fname = Path(flag_item["file"]).name
            fline = f"{fname}:{flag_item['line']}"
            flags_str = ", ".join(flag_item["flags"])
            lines.append(f"| `{flag_item['id']}` | `{fline}` | {flag_item['scenario'][:40]} | `{flags_str}` |")
        if len(result["flags"]) > 30:
            lines.append(f"\n*(and {len(result['flags']) - 30} more flags)*")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest and validate teacher-generated batches into train, val, and DPO sets."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more reviewed teacher JSONL files (e.g. data/accepted_dialogs.jsonl)"
    )
    parser.add_argument(
        "--rejected",
        type=str,
        default=None,
        help="Path to rejected dialogues JSONL for constructing DPO pairs (e.g. data/rejected_dialogs.jsonl)"
    )
    parser.add_argument(
        "--train-out",
        type=str,
        default=str(REPO_ROOT / "data" / "train.jsonl"),
        help="Output path for SFT train JSONL"
    )
    parser.add_argument(
        "--val-out",
        type=str,
        default=str(REPO_ROOT / "data" / "val.jsonl"),
        help="Output path for SFT validation JSONL"
    )
    parser.add_argument(
        "--dpo-out",
        type=str,
        default=str(REPO_ROOT / "data" / "dpo.jsonl"),
        help="Output path for DPO preference pairs JSONL"
    )
    parser.add_argument(
        "--rejected-out",
        type=str,
        default=str(REPO_ROOT / "data" / "ingest_rejected.jsonl"),
        help="Output path for dialogues rejected during ingestion"
    )
    parser.add_argument(
        "--report-out",
        type=str,
        default=None,
        help="Optional path to write a markdown ingestion report (e.g. data/ingest_report.md)"
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="Validation split ratio (default: 0.1)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatable train/val split (default: 42)"
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="Starting sequential integer for sinmate_NNNNN IDs (default: 1)"
    )
    parser.add_argument(
        "--keep-unmapped-categories",
        action="store_true",
        help="Keep unmapped free-text categories instead of dropping the category field"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and generate report without modifying output files"
    )

    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    rejected_path = Path(args.rejected) if args.rejected else None

    # Check inputs existence
    for p in input_paths:
        if not p.exists():
            print(f"Error: input file not found: {p}", file=sys.stderr)
            sys.exit(1)

    result = ingest_batches(
        input_paths=input_paths,
        rejected_path=rejected_path,
        val_ratio=args.val_ratio,
        seed=args.seed,
        start_id=args.start_id,
        drop_unmapped_categories=not args.keep_unmapped_categories,
    )

    report = format_stats_report(result)
    print("\n" + report)

    if not args.dry_run:
        train_out = Path(args.train_out)
        val_out = Path(args.val_out)
        dpo_out = Path(args.dpo_out)
        rej_out = Path(args.rejected_out)

        train_out.parent.mkdir(parents=True, exist_ok=True)

        # Write train.jsonl
        with open(train_out, "w", encoding="utf-8") as f:
            for item in result["train_set"]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Wrote {len(result['train_set'])} dialogues to {train_out}")

        # Write val.jsonl
        with open(val_out, "w", encoding="utf-8") as f:
            for item in result["val_set"]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Wrote {len(result['val_set'])} dialogues to {val_out}")

        # Write dpo.jsonl if pairs exist
        if result["dpo_pairs"]:
            with open(dpo_out, "w", encoding="utf-8") as f:
                for item in result["dpo_pairs"]:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"Wrote {len(result['dpo_pairs'])} DPO pairs to {dpo_out}")

        # Write rejected if any
        if result["rejected_items"]:
            with open(rej_out, "w", encoding="utf-8") as f:
                for item in result["rejected_items"]:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"Wrote {len(result['rejected_items'])} rejected entries to {rej_out}")

        # Write report if requested
        if args.report_out:
            report_out = Path(args.report_out)
            report_out.parent.mkdir(parents=True, exist_ok=True)
            with open(report_out, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Wrote ingestion report to {report_out}")


if __name__ == "__main__":
    main()
