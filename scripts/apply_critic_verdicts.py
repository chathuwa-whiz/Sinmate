#!/usr/bin/env python3
"""
Apply Prompt 3 (QUALITY CRITIC) verdicts to a teacher-generated batch.

Inputs
  --batch     the batch JSONL the critic reviewed (raw teacher output; code fences and blank lines are ignored)
  verdicts    one or more files holding the critic's reply (pasted as-is; code fences, prose around it, pretty-printed
              JSON and trailing commas are tolerated). Pass several files to combine critics from different LLMs.
              Use "-" to read the reply from stdin. Missing arguments open a file picker (needs tkinter).

The critic's "line" is the 1-based position among the dialogue lines of the batch (fences and blank lines don't count).
Dialogues the critic doesn't mention count as "keep", because critics often list only the problem lines.

Per dialogue
  drop  -> goes to the rejected file
  fix   -> the critic's assistant turns replace the originals; user turns are always kept from the original
  keep  -> unchanged
Every final dialogue must also pass the mechanical MASTER-prompt rules (alternating roles, assistant turns in pure
Sinhala script with no Latin letters/digits/emoji/markdown, at most 2 sentences). A failure goes to the rejected file
with the reason, so an LLM "fix" that breaks the rules never reaches the dataset.

Outputs (the raw batch is never modified)
  <out-dir>/<batch stem>.jsonl           accepted dialogues, NFC-normalized
  <out-dir>/<batch stem>.rejected.jsonl  rejected dialogues plus "reject_reason" and "critic_issues"

Usage
  python scripts/apply_critic_verdicts.py critic_gpt.txt critic_gemini.txt --batch data/teacher_raw/gemini_BEST_FRIEND_singlish_1.jsonl
"""

import argparse
import difflib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "teacher_reviewed"

MAX_SENTENCES = 2
MAX_WORDS = 35
# Fixes whose first user turn is less similar than this to the original probably belong to a different line.
MIN_USER_SIMILARITY = 0.6

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

Message = Dict[str, str]
Dialogue = dict


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------------------------------------------


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8-sig")


def load_batch(text: str) -> Tuple[List[Dialogue], List[str]]:
    """Dialogue objects in file order (code fences and blank lines skipped) plus parse warnings."""
    dialogues: List[Dialogue] = []
    warnings: List[str] = []
    for raw in text.splitlines():
        line = raw.strip().rstrip(",")
        if not line or line.startswith("```"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            warnings.append(f"batch: unparseable line kept as an empty placeholder: {line[:60]!r}")
            dialogues.append({})  # keep numbering aligned with what the critic saw
            continue
        dialogues.append(obj if isinstance(obj, dict) else {})
    return dialogues, warnings


def parse_verdicts(text: str) -> Tuple[Dict[int, dict], List[str]]:
    """
    Extract verdict objects ({"line": n, "verdict": ...}) from free-form critic output. Works for JSONL, a JSON array,
    pretty-printed objects and replies wrapped in prose or code fences.
    """
    decoder = json.JSONDecoder()
    verdicts: Dict[int, dict] = {}
    warnings: List[str] = []
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            newline = text.find("\n", start)
            snippet = text[start : newline if newline != -1 else None][:70]
            warnings.append(f"verdicts: skipped unparseable object: {snippet!r}")
            if newline == -1:
                break
            pos = newline
            continue
        pos = end
        if not isinstance(obj, dict) or "line" not in obj or "verdict" not in obj:
            continue
        try:
            line_no = int(obj["line"])
        except (TypeError, ValueError):
            warnings.append(f"verdicts: bad line number {obj['line']!r}")
            continue
        if line_no in verdicts:
            warnings.append(f"verdicts: line {line_no} appears twice, using the last one")
        verdicts[line_no] = obj
    return verdicts, warnings


# ---------------------------------------------------------------------------------------------------------------
# Mechanical rules (MASTER prompt)
# ---------------------------------------------------------------------------------------------------------------

_ELLIPSIS = re.compile(r"\.{2,}|…")
_SENTENCE_END = re.compile(r"[.?!]+\s*")
_MARKDOWN_CHARS = set("*#_`~|<>[]{}\\")


def count_sentences(text: str) -> int:
    """Sentences as spoken: an ellipsis is a pause, not a boundary."""
    cleaned = _ELLIPSIS.sub(" ", text)
    return len([part for part in _SENTENCE_END.split(cleaned) if part.strip()])


def bad_characters(text: str) -> List[str]:
    """Characters that must not appear in a Sinhala-script assistant reply (TTS can't read them)."""
    found = []
    for ch in text:
        in_sinhala_block = "඀" <= ch <= "෿"
        if in_sinhala_block or ch in "‌‍" or ch.isspace():
            continue
        category = unicodedata.category(ch)
        if ch.isalpha() or ch.isdigit() or category in ("So", "Sk", "Cs", "Co", "Cn") or ch in _MARKDOWN_CHARS:
            found.append(ch)
        elif ord(ch) > 0xFFFF:  # emoji planes
            found.append(ch)
    return found


def check_messages(messages) -> List[str]:
    """Reasons a messages array breaks the rules; empty if it's fine."""
    if not isinstance(messages, list) or len(messages) < 2:
        return ["messages is not a list of at least 2 turns"]
    reasons: List[str] = []
    for i, msg in enumerate(messages):
        expected = "user" if i % 2 == 0 else "assistant"
        if not isinstance(msg, dict) or msg.get("role") != expected or not isinstance(msg.get("content"), str):
            return [f"turn {i + 1} should be a {expected} message with text content"]
        if not msg["content"].strip():
            return [f"turn {i + 1} is empty"]
    if messages[-1]["role"] != "assistant":
        reasons.append("dialogue must end with an assistant turn")
    for i, msg in enumerate(messages):
        if msg["role"] != "assistant":
            continue
        text = msg["content"]
        bad = bad_characters(text)
        if bad:
            reasons.append(f"turn {i + 1}: forbidden characters {''.join(sorted(set(bad)))[:12]!r}")
        if count_sentences(text) > MAX_SENTENCES:
            reasons.append(f"turn {i + 1}: more than {MAX_SENTENCES} sentences")
        if len(text.split()) > MAX_WORDS:
            reasons.append(f"turn {i + 1}: more than {MAX_WORDS} words")
    return reasons


# ---------------------------------------------------------------------------------------------------------------
# Applying verdicts
# ---------------------------------------------------------------------------------------------------------------


def merge_fix(original: Dialogue, fixed_messages) -> Tuple[Optional[List[Message]], str]:
    """The original messages with assistant turns replaced by the critic's. (messages, "") or (None, reason)."""
    original_messages = original.get("messages")
    if not isinstance(fixed_messages, list):
        return None, "fix has no fixed_messages"
    if not isinstance(original_messages, list) or len(fixed_messages) != len(original_messages):
        return None, "fixed_messages has a different number of turns than the original"
    merged: List[Message] = []
    for old, new in zip(original_messages, fixed_messages):
        if not isinstance(new, dict) or new.get("role") != old.get("role") or not isinstance(new.get("content"), str):
            return None, "fixed_messages roles don't match the original"
        merged.append({"role": old["role"], "content": new["content"] if old["role"] == "assistant" else old["content"]})
    first_old = nfc(original_messages[0]["content"])
    first_new = nfc(fixed_messages[0]["content"])
    if difflib.SequenceMatcher(None, first_old, first_new).ratio() < MIN_USER_SIMILARITY:
        return None, "fix looks like it belongs to a different line (first user turn doesn't match)"
    return merged, ""


def decide(
    index: int, original: Dialogue, critic_verdicts: List[dict], drop_if: str
) -> Tuple[str, Optional[Dialogue], str, List[str]]:
    """Returns (status, dialogue, note, issues). status is accepted-keep, accepted-fix or rejected."""
    issues: List[str] = []
    for verdict in critic_verdicts:
        issues += [str(i) for i in verdict.get("issues", []) if isinstance(i, str)]
    issues = sorted(set(issues))

    if not original:
        return "rejected", None, "batch line could not be parsed", issues
    labels = [str(v.get("verdict", "")).strip().lower() for v in critic_verdicts]
    unknown = [l for l in labels if l not in ("keep", "fix", "drop")]
    if unknown:
        return "rejected", None, f"unknown verdict {unknown[0]!r}", issues

    drops, total = labels.count("drop"), len(critic_verdicts)
    dropped = {"any": drops >= 1, "majority": drops * 2 > total, "all": drops == total}[drop_if]
    if dropped:
        return "rejected", None, f"critic verdict: drop ({drops}/{total})", issues

    final = dict(original)
    status = "accepted-keep"
    fixes = [v for v, l in zip(critic_verdicts, labels) if l == "fix"]
    if fixes:
        reasons: List[str] = []
        for verdict in fixes:
            merged, why = merge_fix(original, verdict.get("fixed_messages"))
            if merged is None:
                reasons.append(why)
                continue
            problems = check_messages(merged)
            if problems:
                reasons.append("fix breaks rules: " + "; ".join(problems))
                continue
            final["messages"] = merged
            status = "accepted-fix"
            break
        else:
            return "rejected", None, "no usable fix: " + " | ".join(reasons), issues

    final["messages"] = [{"role": m["role"], "content": nfc(m["content"]).strip()} for m in final["messages"]]
    problems = check_messages(final["messages"])
    if problems:
        return "rejected", None, "fails rules: " + "; ".join(problems), issues
    return status, final, "", issues


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def pick_file(title: str) -> str:
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        sys.exit("No file given and tkinter is unavailable for a file picker. Pass the paths as arguments.")
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askopenfilename(title=title)
    root.destroy()
    if not chosen:
        sys.exit("No file selected.")
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply QUALITY CRITIC verdicts to a teacher batch.")
    parser.add_argument("verdicts", nargs="*", help="critic reply file(s); '-' reads stdin")
    parser.add_argument("-b", "--batch", help="the batch JSONL the critic reviewed")
    parser.add_argument("-o", "--out-dir", default=str(DEFAULT_OUT_DIR), help="where to write results")
    parser.add_argument(
        "--drop-if",
        choices=["any", "majority", "all"],
        default="any",
        help="with several critics, how many 'drop' votes reject a dialogue (default: any)",
    )
    parser.add_argument("--dry-run", action="store_true", help="show the report without writing files")
    parser.add_argument("--force", action="store_true", help="overwrite existing output files")
    args = parser.parse_args()

    batch_path = args.batch or pick_file("Select the BATCH file the critic reviewed")
    verdict_paths = args.verdicts or [pick_file("Select the critic's reply file")]

    dialogues, warnings = load_batch(read_text(batch_path))
    if not dialogues:
        sys.exit(f"No dialogues found in {batch_path}")

    critics: List[Dict[int, dict]] = []
    for path in verdict_paths:
        verdicts, more = parse_verdicts(read_text(path))
        warnings += [f"{path}: {w}" for w in more]
        if not verdicts:
            sys.exit(f"No verdicts found in {path}. Paste the critic's JSONL reply into the file.")
        out_of_range = sorted(n for n in verdicts if not 1 <= n <= len(dialogues))
        if out_of_range:
            warnings.append(f"{path}: line numbers outside 1..{len(dialogues)} ignored: {out_of_range[:10]}")
        critics.append(verdicts)

    accepted: List[Dialogue] = []
    rejected: List[Dialogue] = []
    status_count: Counter = Counter()
    issue_count: Counter = Counter()
    reject_reasons: Counter = Counter()
    for index, original in enumerate(dialogues, start=1):
        votes = [c[index] for c in critics if index in c] or [{"verdict": "keep"}]
        status, final, note, issues = decide(index, original, votes, args.drop_if)
        status_count[status] += 1
        issue_count.update(issues)
        if final is not None:
            accepted.append(final)
        else:
            reject_reasons[note.split(":")[0].split(" (")[0]] += 1
            rejected.append({**original, "source_line": index, "reject_reason": note, "critic_issues": issues})

    stem = Path(batch_path).stem
    out_dir = Path(args.out_dir)
    accepted_path = out_dir / f"{stem}.jsonl"
    rejected_path = out_dir / f"{stem}.rejected.jsonl"

    print(f"Batch: {batch_path}  ({len(dialogues)} dialogues, {len(critics)} critic file(s))")
    mentioned = {n for c in critics for n in c if 1 <= n <= len(dialogues)}
    print(f"Critic mentioned {len(mentioned)} lines; the other {len(dialogues) - len(mentioned)} are treated as keep.")
    print(
        f"Accepted {len(accepted)} (unchanged {status_count['accepted-keep']}, "
        f"fixed {status_count['accepted-fix']}), rejected {len(rejected)}."
    )
    if reject_reasons:
        print("Reject reasons: " + ", ".join(f"{r} x{n}" for r, n in reject_reasons.most_common()))
    if issue_count:
        print("Critic issues: " + ", ".join(f"{i} x{n}" for i, n in issue_count.most_common()))
    for row in rejected[:15]:
        print(f"  line {row['source_line']}: {row['reject_reason']}")
    if len(rejected) > 15:
        print(f"  ... {len(rejected) - 15} more in the rejected file")
    for warning in warnings:
        print(f"warning: {warning}")

    if args.dry_run:
        print("Dry run: nothing written.")
        return 0
    existing = [p for p in (accepted_path, rejected_path) if p.exists()]
    if existing and not args.force:
        sys.exit(f"Refusing to overwrite {', '.join(map(str, existing))}. Use --force or --out-dir.")
    write_jsonl(accepted_path, accepted)
    write_jsonl(rejected_path, rejected)
    print(f"Wrote {accepted_path}\nWrote {rejected_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
