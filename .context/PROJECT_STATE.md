# Sinmate Living Project State

**Project**: Sinmate (Edge-Deployable Native Sinhala Conversational Voice Companion)  
**Last Updated**: 2026-10-26 17:53 UTC
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

## 3. Key Environment Invariants

- **Unicode Handling**: All Sinhala text MUST be normalized to Unicode NFC (`unicodedata.normalize("NFC", text)`).
- **Diglossia Rules**: Assistant conversational responses must be in natural spoken Sinhala (*Kathitha Bhashawa*), NOT formal written grammar (*Likhitha Bhashawa*), unless specifically requested.
- **Resource Constraints**: Total runtime memory must stay under 6GB VRAM/RAM.
- **Parallel Safety**: Agents must claim tasks in `TASKS.json` before writing and release locks upon completion.
