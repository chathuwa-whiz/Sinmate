# Sinmate Living Project State

**Project**: Sinmate (Edge-Deployable Native Sinhala Conversational Voice Companion)  
**Last Updated**: 2026-10-26 19:36 UTC
**Repository Branch**: `main`  
**Current Milestone**: Phase 1 - Multi-Agent Infrastructure & Core Pipeline Scaffolding

---

## 1. Quick Project Summary

Sinmate is an open-source, edge-runnable native Sinhala voice companion designed for laptops and desktops (< 6GB RAM footprint). It combines:
1. **Low-Latency Voice Detection & STT**: Silero VAD + Faster-Whisper with Sinhala checkpoints.
2. **Spoken Sinhala Conversational LLM**: Gemma-2-2B / Gemma-3-4B (4-bit GGUF via Ollama) fine-tuned for colloquial Kathitha Bhashawa and multi-persona switching.
3. **Natural Voice Synthesis**: Native Sinhala VITS / Piper TTS.
4. **Emotional Continuity & Proactivity**: Local SQLite memory + APScheduler proactive heartbeat timer.

---

## 2. Active Agents & Assignments

| Agent Name | Active Task ID | Scope / Modules | Status |
| :--- | :--- | :--- | :--- |
| **Antigravity** | `TASK-001` | Multi-Agent Parallel Environment & Context Engine Setup | `done` |
| ***Open*** | `TASK-002` | Sinhala Tokenizer Fertility & Compression Benchmark Script | `done` |
| ***Open*** | `TASK-003` | Audio Ear Pipeline (Silero VAD + Faster-Whisper Sinhala STT) | `todo` |
| **Claude** | `TASK-004` | Brain Engine & Spoken Sinhala Multi-Persona Templates | `done` |
| ***Open*** | `TASK-005` | Mouth Pipeline (Sinhala VITS / Piper TTS Voice Synthesis) | `todo` |
| ***Open*** | `TASK-006` | Heart & Memory System (SQLite Fact Store + Spontaneous Heartbeat) | `todo` |
| ***Open*** | `TASK-007` | Full-Duplex Orchestrator & Barge-In Audio Loop | `todo` |
| **Antigravity** | `TASK-008` | Conversational Sinhala Dataset Generation & SFT/DPO Pipeline | `done` |
| ***Open*** | `TASK-009` | Teacher-batch ingest script (scripts/ingest_teacher_batches.py) | `todo` |
| ***Open*** | `TASK-010` | Scale teacher dataset: targeted batches (grief, crisis, identity, panic) then ~1,000-4,000 dialogues | `todo` |
| ***Open*** | `TASK-011` | ADR-006 cognitive pipeline stages 1-3 and 5 (input type, emotion, category, guardrail) | `todo` |
| ***Open*** | `TASK-012` | Fine-tune v2 + GGUF export + live re-test against Brain | `todo` |

## 3. Key Environment Invariants

- **Unicode Handling**: All Sinhala text MUST be normalized to Unicode NFC (`unicodedata.normalize("NFC", text)`).
- **Diglossia Rules**: Assistant conversational responses must be in natural spoken Sinhala (*Kathitha Bhashawa*), NOT formal written grammar (*Likhitha Bhashawa*), unless specifically requested.
- **Resource Constraints**: Total runtime memory must stay under 6GB VRAM/RAM.
- **Parallel Safety**: Agents must claim tasks in `TASKS.json` before writing and release locks upon completion.

---

## 4. Handoff Notes (written by Claude, 2026-10-27, for whichever agent continues)

### What exists now
- **Brain (TASK-004, done)**: `src/sinmate/brain/llm_engine.py` (stdlib Ollama client, sentence streaming for TTS, `Brain` loop with barge-in-safe history), `personas.py` with a `compact` prompt style that matches the SFT training prompts. `DEFAULT_MODEL = "gemma3:1b-it-qat"` (user-chosen). Live-tested: plumbing works, but the *base* model's Sinhala is poor (Gujarati script, emoji, copies the `Example:` lines). Quality must come from the fine-tune.
- **Notebooks 01 and 02**: HF login tries Colab secret, then `HF_TOKEN` env var, then `getpass`. Notebook 02 runs on a Colab T4 (picks fp32 compute when GPU capability < 8, because bf16 needs 8.0+; fp16 avoided, Gemma 3 overflows). It targets transformers 5.x / trl 1.x APIs. First fine-tune ran but gave a bad reply (12 seeds expanded to 108 rows, loss on full sequence).
- **Teacher-LLM dataset pipeline (new, this session)**:
  - `docs/dataset_generation_prompts.md`: Prompt 1 MASTER, 2 BATCH REQUEST, 3 QUALITY CRITIC, 4 REJECTED-REPLY (DPO). Teacher output is JSONL with no system prompt and no id. Assistant replies are 100% Sinhala script (no Latin, digits, emoji, markdown) because the TTS cannot read them.
  - `scripts/apply_critic_verdicts.py` (+ `tests/test_apply_critic_verdicts.py`): applies Prompt 3 verdicts to a batch. Unlisted lines count as keep. Fixes replace assistant turns only; every output dialogue must also pass the mechanical rules (alternation, pure Sinhala, <= 2 sentences, <= 35 words). Several critic files supported (`--drop-if any|majority|all`). Writes `data/teacher_reviewed/<stem>.jsonl` and `.rejected.jsonl`.
  - `data/accepted_dialogs.jsonl` (73 dialogues) and `data/rejected_dialogs.jsonl` (73 DPO "rejected" replies, `line` n = nth accepted dialogue, 7 defect types balanced). These are the user's pilot output after running all four prompts. The earlier raw Gemini batch (`data/gemini_generated_dialogs.jsonl`) was removed by the user; the raw teacher output should live in `data/teacher_raw/` going forward.
- **`./agent`** launcher works in Git Bash on Windows (python3 Store-stub workaround).
- Tests: `python -m unittest discover -s tests` (pytest is not installed). 55 tests pass.

### Pilot review findings (73 accepted dialogues)
- Passes all mechanical rules; personas and input types are well balanced.
- **Missing: 0 grief_and_loss, 0 crisis_support, 0 identity_honesty, only 5 panic_and_anxiety.** Neutral is 32/73.
- 66 distinct categories (almost all off the allowed list); the ingest step must map them onto the 9 ADR-006 categories or drop the field.
- MOTHER_FIGURE says `පුතේ` 20x vs `දරුවෝ` 15x (gendered; prompt says do not assume gender). Stock phrases repeat (`කලබල වෙන්න එපා` x3, `ප්‍රතිඵල තමයි ඔය` x3, `තුන් සරණේ පිහිටෙන්` x2).
- Lines to review/fix/drop in `accepted_dialogs.jsonl` (line numbers = file lines; the user is the native-speaker judge): 29 (`ඇඟට ලේ ටිකක් ඉනුවේ` reads as nonsense), 31 (`හාහාපුරා`), 44 (`මාළුපිනි`), 26 (assumes the user is a woman), 21 and 57 (hearsay stated as fact), 16 and 18 (loose or made-up facts), 25 and 48 (health claims), 40 (real singer named).
- The training data in `data/train.jsonl` still has 9 different system-prompt variants (2-3 per persona); the rebuilt dataset should use exactly one per persona (`COMPACT_PERSONA_LINES`).

### What to do next (in order; tasks are in TASKS.json)
1. **TASK-009** Write `scripts/ingest_teacher_batches.py` (spec in the task). This is the missing link: nothing generated so far reaches `train.jsonl`.
2. **TASK-010** Targeted teacher batches for the missing emotions (grief ~20, crisis ~10, identity ~10, panic ~15), then scale to 1,000+ dialogues. Add to Prompt 2: category from the allowed list, no hearsay or health claims, mother persona prefers `දරුවෝ`/`ඔයා`. The user must read all grief and crisis dialogues.
3. **TASK-012** Fine-tune v2 on Colab with response-only loss masking, GGUF export, Ollama import, rerun the Brain live test.
4. **TASK-011** ADR-006 stages 1-3 and 5 (input type, emotion, category, guardrail) are not coded.
5. TASK-003 (ears), TASK-005 (mouth), TASK-006 (memory/heartbeat), TASK-007 (orchestrator) are untouched.

### Leftovers and gotchas
- Personal WhatsApp chats are **not** to be used (user decision). Never commit raw private data. Never read credential files such as `mcp_oauth_tokens.json`.
- Not yet done: remove `Example:` lines from `PERSONA_PROMPTS` in `personas.py` (the base model copies them); fix the `්F` typo in the Yansaya regex in `normalizer.py` (harmless); tests append "Automated test message" entries to `.context/BLACKBOARD.md` on every run (noise; the test fixture should use a temp file).
- Environment: Git Bash `python3` is the Windows Store stub (use `python`); the Edit tool refuses `.ipynb` (use NotebookEdit, which reformats the JSON, so restore `language_info` and line-list sources afterwards); `sys.stdout.reconfigure(encoding="utf-8")` is needed for Sinhala output on Windows.
- Nothing is pushed to a remote.
