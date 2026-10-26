# Architecture Decision Records (ADRs)

This document records the architectural and technology decisions agreed upon for **Sinmate**. Agents must consult this before proposing conflicting changes.

---

### ADR-001: Centralized Multi-Agent State Hub (`.context/`)
* **Status**: Accepted
* **Context**: Multiple autonomous agents (Claude Code, OpenAI Codex, Antigravity, OpenCode, Groq, Cursor) will run concurrently on this project. Without a shared memory and locking protocol, agents overwrite files, duplicate work, or operate on stale assumptions.
* **Decision**: Establish `.context/` as the single source of truth (SSOT) containing live state (`PROJECT_STATE.md`), message bus (`BLACKBOARD.md`), atomic task board (`TASKS.json`), and architecture specs. Provide `scripts/agent_hub.py` as a zero-dependency CLI tool for claiming tasks, posting updates, and spawning git worktrees.
* **Consequence**: All agents must check in with `agent_hub.py` or `.context/` before starting work and release locks upon completion.

---

### ADR-002: Base Conversational LLM Choice (Gemma-2-2B / Gemma-3-4B)
* **Status**: Accepted
* **Context**: Sinhala is morphologically rich (U+0D80–U+0DFF Unicode block). Base models like LLaMA 3.2 or base Qwen 2.5 fragment Sinhala characters into 3 raw UTF-8 bytes per character (~6.5-8.0 tokens/word fertility), causing massive slowdowns and broken grammar unless complex tokenizer surgery and embedding retraining are performed.
* **Decision**: Standardize on `google/gemma-2-2b-it` or `google/gemma-3-4b-it` as the primary base model. Gemma possesses a native 256k+ SentencePiece vocabulary that cleanly tokenizes Sinhala subwords and graphemes out-of-the-box (~1.8-2.4 tokens/word) without requiring tokenizer extension.
* **Consequence**: Focus fine-tuning efforts on high-quality spoken colloquial dataset curation (SFT + DPO) rather than fragile embedding resizing.

---

### ADR-003: 4-Part Modular Edge Architecture (< 6GB RAM)
* **Status**: Accepted
* **Context**: The target deployment is local laptops and desktop computers, running alongside the user during daily work. Giant models (>8B) or heavy cloud APIs create high latency, cost, and prohibitive hardware requirements.
* **Decision**: Build four decoupled, lightweight components:
  1. **Ears**: Silero VAD (voice detection in 1ms) + Faster-Whisper with Sinhala checkpoint (`SinhaSpeech/whisper-small-sinhala-run11`).
  2. **Brain**: 4-bit quantized Gemma GGUF via Ollama / llama.cpp (~1.6GB - 2.8GB VRAM).
  3. **Mouth**: VITS / Piper TTS using native Sri Lankan voice checkpoints (`SinhalaVITS-TTS-F1` / `SafnasKaldeen`).
  4. **Heart**: SQLite persistent store + APScheduler background heartbeat loop for proactive spontaneous dialogue.
* **Consequence**: Total footprint remains within 4GB - 6GB RAM, allowing smooth real-time execution on typical developer laptops without dedicated high-end GPUs.

---

### ADR-004: Spoken Colloquial Sinhala (Kathitha Bhashawa) Focus
* **Status**: Accepted
* **Context**: Existing Sinhala NLP models often sound like formal textbook news broadcasts (*Likhitha Bhashawa*) or machine-translated English (*translationese*), which fails in an intimate voice companion.
* **Decision**: All conversational prompts, training examples, and persona templates must use natural spoken Sinhala (*Kathitha Bhashawa*), short conversational turns (1-2 sentences), Sri Lankan conversational fillers, and handle Romanized Singlish code-mixing.
* **Consequence**: Formal written Sinhala is reserved only for academic or document summaries when explicitly requested.

---

### ADR-005: Cross-Platform & Google Colab Hybrid Workflow
* **Status**: Accepted
* **Context**: The developer machines include Mac laptops and Windows PCs that cannot run or fine-tune Gemma 3 locally due to VRAM limitations. Additionally, scripts limited to Windows PowerShell cannot run on macOS.
* **Decision**: 
  1. Offload heavy computation (tokenizer benchmarking, QLoRA fine-tuning, DPO, GGUF quantization) to Google Colab with free T4 or cloud GPUs via `notebooks/` and `requirements-colab.txt`.
  2. Maintain 100% cross-platform parity across macOS, Linux, and Windows for multi-agent development. Provide a universal POSIX executable `./agent` for Mac/Linux and `agent.bat`/`agent.ps1` for Windows, with all core logic in cross-platform standard Python.
  3. Enforce LF line endings via `.gitattributes` to avoid cross-platform Git conflicts.
* **Consequence**: Developers and AI agents on Mac, Windows, or cloud VMs can collaborate concurrently with zero platform friction.

---

### ADR-006: 6-Stage Real-Time Cognitive Pipeline & Deterministic Guardrail
* **Status**: Accepted
* **Context**: Low-resource 1B/4B models can suffer from emotional tone blindness (e.g. responding cheerfully with slang to tragic news like a family death) and hallucinations. Relying on a second LLM to critique every response would double latency and exceed low-spec laptop CPU budgets.
* **Decision**: Adopt a sequential 6-stage cognitive loop:
  1. `Input Type Check` (Regex: pure_sinhala / singlish / mixed_script in <1ms)
  2. `Emotion Classification` (Lexical analysis across 5 Sri Lankan emotional registers: grief, anxiety, burnout, joy, neutral in <2ms)
  3. `Category Mapping` (Contextual topic matching)
  4. `Answer Generation` (Gemma-3-1B-IT with persona + dynamic emotional directive in ~300ms)
  5. `Deterministic Guardrail & Hallucination Double-Check` (Tone-clash interceptor preventing cheerful slang on grief, factuality/RAG memory verification, and TTS markdown cleaner in <5ms)
  6. `Audio Output` (Sentence streaming to VITS TTS with full-duplex barge-in)
* **Consequence**: Prevents tone-deaf blunders with zero added latency, maintaining sub-second voice turnaround on low-spec hardware.

