# Sinmate Living Project State

**Project**: Sinmate (Edge-Deployable Native Sinhala Conversational Voice Companion)  
**Last Updated**: 2026-10-27 16:01 UTC
**Repository Branch**: `main`  
**Current Milestone**: Phase 1 - Release `v0.1.0-alpha` (Proof of Concept Verified & Documented)

---

## 1. Quick Project Summary

Sinmate is an open-source, edge-runnable native Sinhala voice companion designed for laptops and desktops (< 6GB RAM footprint). It combines:
1. **Low-Latency Voice Detection & STT**: Silero VAD + Faster-Whisper with Sinhala checkpoints.
2. **Spoken Sinhala Conversational LLM**: Gemma-3-1B / 4B (4-bit GGUF via Ollama) fine-tuned for colloquial Kathitha Bhashawa and multi-persona switching.
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
| **Antigravity** | `TASK-012` | Fine-tune v2 + GGUF export + live re-test against Brain | `done` |
| **Claude** | `TASK-013` | Split notebooks into colab/ and global/ with sibling-sync rule | `done` |

## 3. Key Environment Invariants

- **Unicode Handling**: All Sinhala text MUST be normalized to Unicode NFC (`unicodedata.normalize("NFC", text)`).
- **Diglossia Rules**: Assistant conversational responses must be in natural spoken Sinhala (*Kathitha Bhashawa*), NOT formal written grammar (*Likhitha Bhashawa*), unless specifically requested.
- **Resource Constraints**: Total runtime memory must stay under 6GB VRAM/RAM.
- **Parallel Safety**: Agents must claim tasks in `TASKS.json` before writing and release locks upon completion.

---

## 4. Current State & Handoff Notes

### What exists now
- **Release `v0.1.0-alpha` (Proof-of-Concept Milestone Completed)**:
  - Full end-to-end training, quantization, packaging, and real-time inference executed in [`notebooks/colab/02_colab_qlora_finetune_gemma3.ipynb`](notebooks/colab/02_colab_qlora_finetune_gemma3.ipynb).
  - Base model: `google/gemma-3-1b-it` (1.01B params).
  - Train dataset: 106 pilot dialogues; 3 epochs, 42 steps, final training loss = **`3.5006`**.
  - Quantized to **`Q4_K_M` GGUF (768.7 MB)** with `llama.cpp` and packaged into Ollama model **`sinmate-gemma3:1b` (806 MB)**.
  - Interactive multi-persona live chat executed with real-time text streaming.
  - Model exhibits strong emergent lexical and persona alignment (e.g. "ආදරෙන්", "රසවත්" for romantic; "හෙමින්", "කතා කරන්නේ" for counsellor; "බං", "වැඩේ" for best friend; "ඔව්" for sibling). Syntax is fragmented/unformed at this loss level, as expected for 106 samples.
  - Comprehensive documentation, output logs, linguistic analysis, and version tracking documented in [`README.md`](README.md).
- **Brain Engine (`TASK-004`, done)**: `src/sinmate/brain/llm_engine.py` (stdlib Ollama client, sentence streaming for TTS, `Brain` loop with barge-in-safe history), `personas.py` with `compact` prompt style matching SFT training prompts.
- **Teacher-LLM Dataset Pipeline (`TASK-008`, `TASK-009`, done)**: Ingest script with schema & spoken-Sinhala mechanical validation, compact system prompt injection, and train/val/DPO split generation.
- **Notebook Twins (`TASK-013`, ADR-007)**: Colab notebooks in `notebooks/colab/` and global Jupyter-server twins in `notebooks/global/`.
- **Test Suite**: 63 unit tests pass (`python -m unittest discover -s tests`).

### What to do next (in order)
1. **`TASK-010` (Scale Teacher Dataset towards `v0.2.0-beta`)**:
   - Generate targeted batches to reach 1,000 – 2,000 dialogues.
   - Run DPO preference training to drive loss down to < 1.8 and achieve grammatical sentence fluency.
2. **`TASK-011`**: Implement ADR-006 cognitive pipeline stages 1-3 and 5 (input type, emotion, category, guardrail).
3. **`TASK-003`** (Silero VAD + Faster-Whisper ears), **`TASK-005`** (Sinhala VITS mouth), **`TASK-006`** (SQLite heart & memory), **`TASK-007`** (full-duplex loop).
