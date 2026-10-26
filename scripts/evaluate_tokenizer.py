#!/usr/bin/env python3
"""
Sinhala Tokenizer Fertility & Compression Ratio Evaluator.

Ported from Sinmate Research Specification:
Evaluates how different model tokenizers (Gemma 2/3, Qwen 2.5, SinLlama) handle
Sinhala Unicode, colloquial phrasing, and Singlish code-mixing.

Fertility Benchmarks:
- < 2.5 Tokens/Word: Native understanding; ready for QLoRA fine-tuning without embedding surgery.
- > 4.0 Tokens/Word: Fragmenting into raw UTF-8 bytes; slow inference & spelling instability.
"""

import sys
import unicodedata

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MODELS_TO_TEST = {
    "Qwen-2.5-1.5B (Out-of-box)": "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen-2.5-1.5B (Sinhala-Extended)": "iCIIT/general-purpose-model-ris-sinhala-qwen2.5-1.5b-cp",
    "Gemma-2-2B-IT": "google/gemma-2-2b-it",
    "Gemma-3-4B-IT": "google/gemma-3-4b-it",
}

TEST_SENTENCES = [
    # 1. Colloquial Spoken Sinhala (Kathitha)
    "මම අද කොළඹ යනවා, ඔයා හවසට එනවද මාව හම්බවෙන්න?",
    # 2. Formal Written Sinhala (Likhitha)
    "ශ්‍රී ලංකාවේ ආර්ථිකය සහ තොරතුරු තාක්ෂණ ක්ෂේත්‍රය පිළිබඳව විශේෂ අවධානයක් යොමු කළ යුතුය.",
    # 3. Conversational Customer Support / Technical
    "මගේ ගිණුමේ ශේෂය පරීක්ෂා කරගන්න පුළුවන් කොහොමද කියලා පැහැදිලි කරන්න.",
    # 4. Singlish + Sinhala Code-Mixing
    "Mata me API endpoint eka integrate karana widiha සිංහලෙන් explain karanna පුළුවන්ද?"
]


def evaluate_tokenizer(model_name: str, repo_id: str, sentences: list):
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print("❌ 'transformers' is not installed. Please run: pip install transformers tabulate")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🔍 MODEL: {model_name} ({repo_id})")
    print(f"{'='*70}")

    try:
        tokenizer = AutoTokenizer.from_pretrained(repo_id, trust_remote_code=True)
    except Exception as e:
        print(f"⚠️ Could not load {repo_id}: {e}")
        return None

    total_words = 0
    total_tokens = 0
    total_chars = 0

    for idx, text in enumerate(sentences, 1):
        clean_text = unicodedata.normalize("NFC", text)
        words = clean_text.split()
        token_ids = tokenizer.encode(clean_text, add_special_tokens=False)
        decoded_pieces = [tokenizer.decode([tid]) for tid in token_ids]

        num_words = len(words)
        num_tokens = len(token_ids)
        fertility = num_tokens / num_words if num_words > 0 else 0

        total_words += num_words
        total_tokens += num_tokens
        total_chars += len(clean_text)

        if idx == 1:
            print(f"Sample Text   : {clean_text}")
            print(f"Decoded Pieces: {decoded_pieces[:15]}...")
            print(f"Word Count    : {num_words} | Token Count: {num_tokens} | Fertility: {fertility:.2f} tok/word")

    overall_fertility = total_tokens / total_words if total_words > 0 else 0
    chars_per_token = total_chars / total_tokens if total_tokens > 0 else 0

    return [
        model_name,
        f"{tokenizer.vocab_size:,}",
        total_words,
        total_tokens,
        f"{overall_fertility:.2f}",
        f"{chars_per_token:.2f}"
    ]


def main():
    try:
        from tabulate import tabulate
    except ImportError:
        print("❌ 'tabulate' is not installed. Please run: pip install tabulate")
        sys.exit(1)

    summary_rows = []
    for name, repo in MODELS_TO_TEST.items():
        row = evaluate_tokenizer(name, repo, TEST_SENTENCES)
        if row:
            summary_rows.append(row)

    if summary_rows:
        print("\n\n📊 FINAL TOKEN FERTILITY BENCHMARK (Lower Fertility = Better/Faster)")
        headers = ["Model", "Vocab Size", "Total Words", "Total Tokens", "Fertility (Tok/Word)", "Chars/Token"]
        print(tabulate(summary_rows, headers=headers, tablefmt="github"))


if __name__ == "__main__":
    main()
