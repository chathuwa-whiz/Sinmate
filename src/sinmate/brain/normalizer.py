"""
Sinhala Unicode Normalization & Cleaning Utilities.

Adheres to Sinhala NLP best practices:
- Normalizes all strings to Unicode NFC.
- Preserves valid Sinhala conjunct modifiers (Yansaya, Rakaransaya, Repaya with ZWJ U+200D).
- Removes stray zero-width joiners/non-joiners elsewhere.
"""

import re
import unicodedata

# Valid ZWJ sequences in Sinhala:
# 1. Yansaya: Consonant + Hal (U+0DCA) + ZWJ (U+200D) + Ya (U+0DBF) -> e.g. ත්‍ය
# 2. Rakaransaya: Consonant + Hal (U+0DCA) + ZWJ (U+200D) + Ra (U+0DBB) -> e.g. ප්‍ර
# 3. Repaya: Ra (U+0DBB) + Hal (U+0DCA) + ZWJ (U+200D) + Consonant -> e.g. ර්‍ම
# 4. Bandi Akuru (touching letters): Consonant + Hal + ZWJ + Consonant

VALID_ZWJ_PATTERN = re.compile(
    r"([\u0D9A-\u0DC6]\u0DCA\u200D[\u0D9A-\u0DC6])|"  # General touching consonants / conjuncts
    r"([\u0D9A-\u0DC6]\u0DCA\u200D\u0DBF)|"          # Yansaya
    r"([\u0D9A-\u0DC6]\u0DCA\u200D\u0DBB)|"          # Rakaransaya
    r"(\u0DBB\u0DCA\u200D[\u0D9A-\u0DC6])"           # Repaya
)


def normalize_sinhala_text(text: str) -> str:
    """
    Normalizes Sinhala text to Unicode NFC and cleans superfluous zero-width characters.
    """
    if not text:
        return ""

    # Step 1: Standard NFC normalization
    normalized = unicodedata.normalize("NFC", text)

    # Step 2: Temporarily protect valid ZWJ conjuncts
    placeholders = {}
    
    def replacer(match):
        idx = f"__SIN_CONJUNCT_{len(placeholders)}__"
        placeholders[idx] = match.group(0)
        return idx

    protected = VALID_ZWJ_PATTERN.sub(replacer, normalized)

    # Step 3: Strip extraneous ZWJ (U+200D) and ZWNJ (U+200C)
    cleaned = protected.replace("\u200d", "").replace("\u200c", "")

    # Step 4: Restore valid conjuncts
    for placeholder, original in placeholders.items():
        cleaned = cleaned.replace(placeholder, original)

    # Step 5: Clean multiple whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()

    return cleaned
