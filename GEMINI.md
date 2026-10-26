# AI AGENT WORKSPACE DIRECTIVE: SINMATE

> **CRITICAL**: You are operating in a multi-agent environment where other agents (Claude, Codex, OpenCode, Antigravity/AGY, Groq, Cursor) may run simultaneously. All agents MUST share the same up-to-date context and follow the coordination protocol.

---

## 1. Single Source of Truth (SSOT)
Before writing or changing code, you **MUST** read:
1. **`.context/PROJECT_STATE.md`** - Living status, current phase, and active agents.
2. **`.context/BLACKBOARD.md`** - Live inter-agent event feed and announcements.
3. **`.context/TASKS.json`** - Backlog and resource locks.
4. **`.context/ARCHITECTURE.md`** - System design, models, and hardware constraints (<6GB RAM).
5. **`.context/DECISIONS.md`** - Architectural Decision Records (ADRs).

---

## 2. Multi-Agent CLI Hub (`agent_hub.py`)
Run these helper commands to coordinate with peers:
- **CLI Commands (macOS/Linux: `./agent <cmd>`, Windows: `.\agent.ps1 <cmd>` or `python scripts/agent_hub.py <cmd>`)**:
  - **Check Status**: `python scripts/agent_hub.py status`
  - **Claim a Task**: `python scripts/agent_hub.py claim <TASK_ID> --agent <YourName>`
  - **Release a Task**: `python scripts/agent_hub.py release <TASK_ID> --summary "What you did"`
  - **Post Note to Peers**: `python scripts/agent_hub.py post --agent <YourName> --msg "Your message"`
  - **Spawn Worktree for Parallel Edits**: `python scripts/agent_hub.py worktree create <YourName> <branch_name>`

---

## 3. Project-Specific Core Rules
1. **Cross-Platform Compatibility**: Code and scripts must run cleanly across macOS, Linux, Windows, and Google Colab.
2. **Sinhala Unicode Normalization**: All text input/output must be normalized to Unicode NFC (`unicodedata.normalize("NFC", text)`).
3. **Spoken Colloquial Style (Kathitha Bhashawa)**: Conversational outputs must be short (1-2 sentences), warm, and use natural Sri Lankan colloquial Sinhala with fillers, NOT formal written Sinhala (*Likhitha Bhashawa*).
4. **Hybrid Colab Training**: Compute-heavy workloads (Gemma 3 fine-tuning, tokenization benchmarks, QLoRA, GGUF export) run in Google Colab (`notebooks/` and `requirements-colab.txt`).
5. **Memory Footprint Limit**: Local runtime RAM/VRAM must remain under 6GB (4-bit GGUF Gemma-2B/3-4B + Faster-Whisper + Sinhala VITS TTS + SQLite).
6. **Never Overwrite Peer Work**: Check `.context/TASKS.json` before modifying files. If a file is locked or a task is `in_progress` by another agent, do not touch it.
