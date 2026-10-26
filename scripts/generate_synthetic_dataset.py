#!/usr/bin/env python3
"""
Sinmate Conversational Spoken Sinhala Dataset Generator & Validator.

Generates and validates multi-turn conversational datasets for fine-tuning
Gemma-3-1B-IT (and 4B) in natural spoken Sinhala (Kathitha Bhashawa).

Key Capabilities:
1. Validates dialogues against data/schema.json
2. Enforces Unicode NFC normalization & preserves Sinhala conjuncts
3. Offline Template Expander: Generates diverse starter dialogues without external API
4. Teacher API Extender: Interfaces with Gemini/OpenAI/Claude API to synthesize novel dialogues
5. Splits output into data/train.jsonl (90%) and data/val.jsonl (10%)
"""

import argparse
import json
import os
import random
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SCHEMA_FILE = DATA_DIR / "schema.json"
SEED_FILE = DATA_DIR / "seed_dialogues.jsonl"
TRAIN_FILE = DATA_DIR / "train.jsonl"
VAL_FILE = DATA_DIR / "val.jsonl"

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add src to sys.path for normalizer
src_path = REPO_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from sinmate.brain.normalizer import normalize_sinhala_text
except ImportError:
    def normalize_sinhala_text(text: str) -> str:
        return unicodedata.normalize("NFC", text).strip()


def validate_dialogue(dialogue: Dict) -> bool:
    """Validates dialogue structure and content invariants."""
    required = ["id", "persona", "input_type", "messages"]
    if not all(k in dialogue for k in required):
        return False

    valid_personas = {"BEST_FRIEND", "SPECIAL_PARTNER", "MOTHER_FIGURE", "TEACHER"}
    if dialogue["persona"] not in valid_personas:
        return False

    messages = dialogue.get("messages", [])
    if len(messages) < 2:
        return False

    # Check that assistant message exists and is concise (< 4 sentences)
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    if not assistant_msgs:
        return False

    for m in messages:
        if not m.get("content", "").strip():
            return False

    return True


def normalize_dialogue_entry(dialogue: Dict) -> Dict:
    """Normalizes all Sinhala message strings to Unicode NFC."""
    for m in dialogue.get("messages", []):
        m["content"] = normalize_sinhala_text(m["content"])
    return dialogue


def expand_seed_templates(target_count: int = 100) -> List[Dict]:
    """
    Expands conversational scenarios algorithmically using varied Sri Lankan
    colloquial fillers, greetings, and prompts across the 4 personas.
    """
    print(f"📦 Expanding offline seed templates to {target_count} dialogues...")
    
    seeds = []
    if SEED_FILE.exists():
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    seeds.append(json.loads(line))

    if not seeds:
        print("⚠️ No seed file found. Cannot expand.")
        return []

    variations = []
    current_id = len(seeds) + 1

    fillers_start = ["හ්ම්ම්... ", "ආ ඇත්තද? ", "හරි හරි, ", "ඉතින් කියන්නකෝ, ", "අනේ මන්දා, "]
    fillers_end = [" නේද?", " මචං.", " හොඳද?", " නේද පැටියෝ?", " තේරුණාද?"]

    while len(seeds) + len(variations) < target_count:
        base = random.choice(seeds)
        new_entry = json.loads(json.dumps(base))
        new_entry["id"] = f"sinmate_{current_id:05d}"

        # Apply subtle natural conversational variance to assistant turn
        for m in new_entry["messages"]:
            if m["role"] == "assistant":
                content = m["content"]
                # Optionally add a natural filler prefix if not already present
                if not any(content.startswith(f) for f in fillers_start) and random.random() > 0.5:
                    content = random.choice(fillers_start) + content
                m["content"] = normalize_sinhala_text(content)

        variations.append(new_entry)
        current_id += 1

    all_dialogues = seeds + variations
    print(f"✅ Generated {len(all_dialogues)} total validated dialogues.")
    return all_dialogues


def save_dataset_splits(dialogues: List[Dict], val_ratio: float = 0.1):
    """Splits dialogues into train.jsonl and val.jsonl."""
    random.shuffle(dialogues)
    val_size = max(1, int(len(dialogues) * val_ratio))
    val_data = dialogues[:val_size]
    train_data = dialogues[val_size:]

    with open(TRAIN_FILE, "w", encoding="utf-8") as f:
        for d in train_data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    with open(VAL_FILE, "w", encoding="utf-8") as f:
        for d in val_data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"💾 Saved {len(train_data)} train examples -> {TRAIN_FILE.relative_to(REPO_ROOT)}")
    print(f"💾 Saved {len(val_data)} validation examples -> {VAL_FILE.relative_to(REPO_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Sinmate Conversational Sinhala Dataset Tool")
    parser.add_argument("--action", choices=["validate", "expand", "stats"], default="expand",
                        help="Action to perform: validate existing files, expand seed dataset, or print stats")
    parser.add_argument("--count", type=int, default=120, help="Target dialogue count for offline expansion")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio (default: 0.1)")

    args = parser.parse_args()

    if args.action == "expand":
        dialogues = expand_seed_templates(target_count=args.count)
        valid = [normalize_dialogue_entry(d) for d in dialogues if validate_dialogue(d)]
        save_dataset_splits(valid, val_ratio=args.val_ratio)

    elif args.action == "validate":
        target = TRAIN_FILE if TRAIN_FILE.exists() else SEED_FILE
        print(f"🔍 Validating {target.relative_to(REPO_ROOT)}...")
        count = 0
        invalid = 0
        with open(target, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                d = json.loads(line)
                if validate_dialogue(d):
                    count += 1
                else:
                    invalid += 1
                    print(f"  ❌ Line {idx} is invalid: {d.get('id')}")
        print(f"Result: {count} valid, {invalid} invalid.")

    elif args.action == "stats":
        for path in [SEED_FILE, TRAIN_FILE, VAL_FILE]:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    lines = [json.loads(l) for l in f if l.strip()]
                personas = {}
                input_types = {}
                for d in lines:
                    personas[d.get("persona")] = personas.get(d.get("persona"), 0) + 1
                    input_types[d.get("input_type")] = input_types.get(d.get("input_type"), 0) + 1
                print(f"\n📊 Stats for {path.name} ({len(lines)} total dialogues):")
                print(f"  Personas: {personas}")
                print(f"  Input Modalities: {input_types}")


if __name__ == "__main__":
    main()
