# Sinmate Architecture Specification

> **Project Mission**: A lightweight, locally runnable native Sinhala AI companion that talks, listens, remembers, and spontaneously initiates conversation like a real friend, family member, partner, or teacher. Designed to run offline on a laptop/desktop within 4 GB - 6 GB of RAM/VRAM.

---

## 1. System Overview: The 4-Part Modular Companion

Instead of one monolithic giant model, Sinmate runs 4 lightweight local subsystems side-by-side:

```mermaid
graph TD
    User([User Voice / Text]) --> Ears[1. The Ears: Silero VAD + Faster-Whisper]
    Ears -->|Sinhala Transcription| Brain[2. The Brain: Local LLM Engine]
    Brain -->|Colloquial Sinhala Response| Mouth[3. The Mouth: Sinhala VITS / Piper TTS]
    Mouth --> AudioOut([Audio Output / Speaker])

    Heart[4. The Heart & Memory: SQLite DB + APScheduler] <-->|Context & Memories| Brain
    Heart -.->|Spontaneous Proactive Trigger| Brain
    Ears -.->|Barge-in Interrupt Signal| Mouth
```

| Subsystem | Technical Component | Recommended Models / Tools | VRAM/RAM Target |
| :--- | :--- | :--- | :--- |
| **1. The Ears** | Silero VAD + Faster-Whisper | `snakers4/silero-vad` + `SinhaSpeech/whisper-small-sinhala-run11` | ~400 MB - 600 MB |
| **2. The Brain** | Local LLM Engine (4-bit GGUF via Ollama / llama.cpp) | `google/gemma-3-1b-it` (Primary low-spec target) or `gemma-3-4b-it` | ~700 MB - 1.8 GB |
| **3. The Mouth** | Local Neural TTS (VITS / Piper) | `dialoglk/SinhalaVITS-TTS-F1` or `SafnasKaldeen/Sinhala-Text-to-Speech-VITS` | ~200 MB - 350 MB |
| **4. The Heart & Memory** | Async Event Loop + Local SQLite + APScheduler | SQLite fact/chat store + APScheduler background heartbeat timer | < 100 MB |

---

## 2. Core Behavioral Mechanics

### A. Spontaneous Proactive Heartbeat
Traditional chatbots wait silently. Sinmate uses a background heartbeat loop (15-30 min intervals) tracking:
- Current local time
- User silence duration
- Historical memories / pending topics
- Generates proactive greetings (e.g., at 11:30 PM: *"ඒයි, දැන් රෑ 11:30 යි නේද? තාම වැඩද? පොඩ්ඩක් ඇස්දෙකට නිවාඩුවක් දෙන්න."*)

### B. Natural Spoken Colloquial Sinhala (Kathitha Bhashawa)
Avoids stiff textbook grammar (*Likhitha Bhashawa*) and robotic translationese.
- Outputs 1-2 short spoken sentences per turn.
- Uses natural Sri Lankan conversational fillers (*"හ්ම්ම්..."*, *"ආ ඇත්තද?"*, *"ඉතින් කියන්නකෝ"*, *"හරි හරි"*).

### C. Dynamic Multi-Persona System
Single model configured via dynamic role markers:
- `[ROLE: BEST_FRIEND]`: Casual, humorous, supportive, uses friendly colloquial phrasing.
- `[ROLE: SPECIAL_PARTNER]`: Warm, caring, emotionally attentive, affectionate tone.
- `[ROLE: MOTHER_FIGURE]`: Nurturing, protective, asks about meals/rest, gentle guidance.
- `[ROLE: TEACHER]`: Encouraging, patient, structured explanations, asks follow-up questions.

### D. Full-Duplex Barge-In (Interruptibility)
When the user speaks while TTS playback is active:
- Silero VAD detects user voice within 30ms.
- Immediately signals audio playback to halt and routes the incoming speech to STT.

---

## 3. Real-Time Cognitive Pipeline (User Flow & Emotional Alignment)

To guarantee emotional intelligence (zero tone-deaf responses on tragic news) and factuality on low-spec hardware without latency spikes, Sinmate follows a **6-stage modular cognitive loop**:

```mermaid
flowchart TD
    A["🎤 User Voice / Prompt"] --> B["1. Check Input Type<br/>(sinhala_unicode / singlish / mixed_script)"]
    B --> C["2. Check User Emotion<br/>(grief, anxiety, burnout, joy, neutral)"]
    C --> D["3. Check Category<br/>(work, tech, academics, relationships, daily)"]
    D --> E["4. Generate Answer<br/>(Gemma-3-1B + Active Persona + Emotional Context)"]
    E --> F{"5. Guardrail & Hallucination Check<br/>(Tone clash? Bad advice? Fact check?)"}
    F -->|Tone Clash / Bad Pattern| G[Auto-Correction / Soft Fallback]
    F -->|Passed| H["🔊 Output to TTS (VITS / Piper)<br/>(Streamed 1-2 spoken sentences with barge-in)"]
    G --> H
```

### Stage Details:

1. **Stage 1: Input Modality Detection (`< 1ms`)**:
   - `sinhala_unicode`: Pure native Sinhala script (*"අද අපි යමුද?"* / *"අඩෝ පට්ට ආතල්"*).
   - `singlish`: Romanized Latin script with phonetic transliteration and chat slang (*"Ado machan ada mara kammali"*).
   - `mixed_script`: Dual-script code-mixing (*"Mata API eka integrate කරගන්න විදිහ කියලා දෙන්න"*).

2. **Stage 2: User Emotion Classification (`< 2ms`)**:
   - Scans lexical cues and triggers across 5 core Sri Lankan emotional registers:
     - `grief_and_loss`: Tragic news, death, illness (*නැති වුණා, funeral, hospital*).
     - `panic_and_anxiety`: Exam failure, urgency, fear (*failed, case ekak, bayai*).
     - `work_burnout_exhaustion`: Fatigue, late nights, headache (*mahansiyi, oluwa kakkumayi, nidimathayi*).
     - `frustration_and_anger`: Unfair situations, traffic, anger (*mala panala, epa wela*).
     - `celebration_and_joy`: Wins, good news, humor (*pass una, dinna, job eka labuna*).
     - `neutral`: Everyday queries and routine chit-chat.

3. **Stage 3: Category Mapping**:
   - Maps topic to one of the Sri Lankan thematic categories (`work_stress`, `tech_and_coding`, `exam_and_study`, `food_and_cravings`, `commute_and_traffic`, `family_and_home`, `cricket_and_sports`, `heartbreak_and_crush`, `late_night_insomnia`).

4. **Stage 4: Answer Generation (`~300ms on CPU`)**:
   - Formulates system prompt combining:
     - Active Persona (`[ROLE: BEST_FRIEND]`, `[ROLE: SPECIAL_PARTNER]`, `[ROLE: MOTHER_FIGURE]`, `[ROLE: TEACHER]`).
     - Dynamic Emotional Invariant: If emotion is `grief_and_loss`, immediately suppress cheerful slang (*"marune"*, *"patta"*, *"gindara"*) and adopt a quiet, supportive, comforting tone.
     - Formats with Gemma turn tags and generates 1–2 short spoken sentences.

5. **Stage 5: Deterministic Guardrail & Hallucination Double-Check (`< 5ms`)**:
   - **Tone Clash Interceptor**: Deterministically ensures that celebratory words never coexist with grief/loss events. If detected, overrides with soft empathetic fallback (*"අයියෝ බං... මට හිතාගන්නවත් බෑ. උඹට කොහොමද දැන්? මම මොනවා හරි කරන්නද මචං?"*).
   - **Factuality & RAG Consistency**: Cross-checks factual dates, phone numbers, or technical steps against local SQLite memory facts to prevent hallucinated phone numbers or misinformation.
   - **TTS Purity Cleaner**: Strips markdown artifacts (`**`, `###`, bullets) so spoken audio remains natural and fluent.

6. **Stage 6: Audio Playback & Barge-In**:
   - Sentence-by-sentence streaming into Sinhala VITS TTS.
   - If user interrupts by speaking, Silero VAD cuts playback within 30ms and routes new audio to STT.

---

## 4. Directory Layout

```
Sinmate/
├── .context/                  # Shared Multi-Agent Nerve Center (SSOT)
│   ├── PROJECT_STATE.md       # High-level state & progress
│   ├── BLACKBOARD.md          # Live agent message & event log
│   ├── TASKS.json             # Atomic task board & locks
│   ├── ARCHITECTURE.md        # This specification file
│   ├── DECISIONS.md           # Architecture Decision Records (ADRs)
│   └── AGENT_PROTOCOL.md      # Operating rules for parallel agents
├── docs/                      # Reference manuals & research documents
│   └── Training a Native Sinhala AI Model.pdf
├── src/
│   └── sinmate/
│       ├── __init__.py
│       ├── audio/             # VAD, STT, and audio stream handling
│       │   ├── __init__.py
│       │   ├── vad.py         # Silero VAD wrapper
│       │   ├── stt.py         # Faster-Whisper Sinhala transcriber
│       │   └── player.py      # Audio playback & barge-in controller
│       ├── brain/             # LLM orchestration & personas
│       │   ├── __init__.py
│       │   ├── llm_engine.py  # Local LLM client (Ollama / GGUF)
│       │   ├── personas.py    # Multi-persona prompt templates
│       │   └── normalizer.py  # Unicode NFC & Sinhala text cleaning
│       ├── tts/               # Voice synthesis engine
│       │   ├── __init__.py
│       │   └── vits_tts.py    # VITS / Piper Sinhala TTS integration
│       ├── memory/            # Persistent memory & fact store
│       │   ├── __init__.py
│       │   └── db.py          # SQLite schema & memory retrieval
│       └── proactive/         # Spontaneous heartbeat loop
│           ├── __init__.py
│           └── heartbeat.py   # Background scheduler & event triggers
├── notebooks/                 # Training & benchmark notebooks, kept as twins (ADR-007)
│   ├── colab/                 # Google Colab only (Colab secrets, `!` magics, /content, apt)
│   │   ├── 01_colab_sinhala_tokenizer_benchmark.ipynb
│   │   └── 02_colab_qlora_finetune_gemma3.ipynb
│   └── global/                # Regular Jupyter servers (%pip, subprocess, cross-platform)
│       ├── 01_global_sinhala_tokenizer_benchmark.ipynb
│       └── 02_global_qlora_finetune_gemma3.ipynb
├── scripts/                   # Tooling, evaluation & agent sync
│   ├── agent_hub.py           # Multi-agent orchestrator & state manager
│   ├── evaluate_tokenizer.py  # Sinhala tokenizer fertility evaluator
│   └── sync_context.py        # Synchronizer for CLAUDE/GEMINI/AGENTS files
├── tests/                     # Automated unit and integration test suite
├── agent                      # Universal POSIX executable launcher (macOS / Linux / Colab)
├── agent.bat                  # Windows CMD launcher
├── agent.ps1                  # Windows PowerShell launcher
├── .cursorrules               # Cursor IDE agent instructions
├── AGENTS.md                  # Universal / Codex / OpenCode agent instructions
├── CLAUDE.md                  # Anthropic Claude Code agent instructions
├── GEMINI.md                  # Google Antigravity / Gemini agent instructions
├── requirements-colab.txt     # Colab GPU dependencies (Unsloth, bitsandbytes, PEFT)
├── pyproject.toml             # Project configuration and dependencies
└── README.md                  # Getting started & environment guide
```

---

## 5. Hybrid Infrastructure: Google Colab & Cross-Platform Clients

Due to local hardware constraints when running or fine-tuning models like Gemma 3:
1. **Google Colab (Compute Engine - Free T4 / Cloud GPUs)**:
   - Used for heavy tasks: Sinhala tokenizer fertility evaluation, synthetic dataset curation, QLoRA SFT training, DPO preference alignment, and 4-bit GGUF quantization export.
   - Notebooks reside in `notebooks/colab/` with Colab-optimized dependencies in `requirements-colab.txt`. Each has a Jupyter-server twin in `notebooks/global/` for machines that are not Colab (needs an NVIDIA CUDA GPU for the QLoRA notebook). The twins must be updated together (ADR-007).
2. **Mac & Windows Client Development**:
   - Code development, voice loop integration, and testing happen on developer laptops (macOS and Windows).
   - Zero Windows lock-in: Universal POSIX `./agent` shell script for macOS and Linux; `agent.bat`/`agent.ps1` for Windows; all core tooling in cross-platform Python.
   - Once trained on Colab, quantized 4-bit GGUF models (~700MB - 1.8GB) run efficiently on consumer CPU/MPS via Ollama / llama.cpp.

