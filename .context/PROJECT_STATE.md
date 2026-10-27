# Sinmate Living Project State

**Project**: Sinmate (Edge-Deployable Native Sinhala Conversational Voice Companion)  
**Last Updated**: 2026-10-27 06:26 UTC
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
| **Antigravity** | `TASK-009` | Teacher-batch ingest script (scripts/ingest_teacher_batches.py) | `done` |
| ***Open*** | `TASK-010` | Scale teacher dataset: targeted batches (grief, crisis, identity, panic) then ~1,000-4,000 dialogues | `todo` |
| ***Open*** | `TASK-011` | ADR-006 cognitive pipeline stages 1-3 and 5 (input type, emotion, category, guardrail) | `todo` |
| ***Open*** | `TASK-012` | Fine-tune v2 + GGUF export + live re-test against Brain | `todo` |

## 3. Key Environment Invariants

- **Unicode Handling**: All Sinhala text MUST be normalized to Unicode NFC (`unicodedata.normalize("NFC", text)`).
- **Diglossia Rules**: Assistant conversational responses must be in natural spoken Sinhala (*Kathitha Bhashawa*), NOT formal written grammar (*Likhitha Bhashawa*), unless specifically requested.
- **Resource Constraints**: Total runtime memory must stay under 6GB VRAM/RAM.
- **Parallel Safety**: Agents must claim tasks in `TASKS.json` before writing and release locks upon completion.

---

## 4. Current State & Handoff Notes

### What exists now
- **Brain Engine (`TASK-004`, done)**: `src/sinmate/brain/llm_engine.py` (stdlib Ollama client, sentence streaming for TTS, `Brain` loop with barge-in-safe history), `personas.py` with `compact` prompt style matching SFT training prompts. `DEFAULT_MODEL = "gemma3:1b-it-qat"`. `Example:` lines removed from `PERSONA_PROMPTS` so model won't mimic them.
- **Teacher-LLM Dataset Pipeline (`TASK-008`, `TASK-009`, `TASK-010`, done)**:
  - `docs/dataset_generation_prompts.md`: Prompt 1 MASTER, Prompt 2 BATCH REQUESTS (structured by emotion: 2.1 grief, 2.2 crisis, 2.3 panic, 2.4 identity, 2.5 burnout, 2.6 anger, 2.7 joy, 2.8 neutral, 2.9 general), Prompt 3 CRITIC, Prompt 4 DPO rejected-reply.
  - `scripts/apply_critic_verdicts.py` (+ tests): applies Prompt 3 verdicts.
  - `scripts/ingest_teacher_batches.py` (+ tests): schema & spoken-Sinhala mechanical validation with true Sinhala lookaround regexes, ADR-006 category mapping, human review flag detector, compact system prompt injection, and train/val/DPO split generation.
  - Pilot dataset: **117 accepted dialogues** and **117 DPO preference pairs** ingested into `data/train.jsonl` (106), `data/val.jsonl` (11), `data/dpo.jsonl` (117).
  - Emotion distribution now balanced: neutral (42), panic (19), burnout (14), joy (12), grief (11), anger (10), crisis (9), identity honesty (10).
  - All 4 personas and 3 input modalities are in target ranges.
- **Google Colab Fine-Tuning v2 Ready (`TASK-012`, in progress)**:
  - `notebooks/02_colab_qlora_finetune_gemma3.ipynb`:
    - Updated cell 5 with native TRL conversational format and `assistant_only_loss=True` (with automatic fallback to `DataCollatorForCompletionOnlyLM` for older TRL versions), resolving the `ImportError: cannot import name 'DataCollatorForCompletionOnlyLM' from 'trl'`.
    - Set tokenizer padding token (`pad_token = eos_token`, `padding_side = 'right'`) for safe batching.
    - Updated cell 6 test prompt to exact `compact` format with `model.eval()` and `do_sample=True`.
    - Added cell 8 to merge LoRA into base model.
    - Added cell 9 to quantize to 4-bit Q4_K_M GGUF via `llama.cpp` (idempotent git clone).
    - Added cell 10 to generate Ollama `Modelfile` with valid triple-quote syntax.
- **Test Suite**: 63 unit tests pass (`python -m unittest discover -s tests`). Cleaned up blackboard test fixtures to prevent noise.

### What to do next (in order)
1. **Run Colab Fine-Tuning v2 (`TASK-012`)**:
   - Push/clone repository on Google Colab GPU runtime (T4 or better).
   - Run `notebooks/02_colab_qlora_finetune_gemma3.ipynb`.
   - Export `sinmate-gemma-3-1b-q4_k_m.gguf` and import into Ollama locally using the generated `Modelfile`.
   - Live test Brain against the fine-tuned model.
2. **`TASK-011`**: Implement ADR-006 cognitive pipeline stages 1-3 and 5 (input type, emotion, category, guardrail).
3. **`TASK-003`** (Silero VAD + Faster-Whisper ears), **`TASK-005`** (Sinhala VITS mouth), **`TASK-006`** (SQLite heart & memory), **`TASK-007`** (full-duplex loop).
