#!/usr/bin/env python3
"""
Sinmate Multi-Agent Context & Concurrency Orchestrator (agent_hub.py)

Zero-dependency CLI tool for managing parallel AI agents (Antigravity/AGY, Claude Code,
OpenAI Codex, OpenCode, Groq, Cursor, Aider).

Maintains single source of truth (SSOT) across:
- .context/PROJECT_STATE.md
- .context/BLACKBOARD.md
- .context/TASKS.json
- Root agent instruction pointers (AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules)
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = REPO_ROOT / ".context"
TASKS_FILE = CONTEXT_DIR / "TASKS.json"
BLACKBOARD_FILE = CONTEXT_DIR / "BLACKBOARD.md"
PROJECT_STATE_FILE = CONTEXT_DIR / "PROJECT_STATE.md"
WORKTREES_DIR = REPO_ROOT / ".worktrees"


def get_current_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_tasks() -> dict:
    if not TASKS_FILE.exists():
        return {"version": "1.0", "project": "Sinmate", "tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data: dict):
    data["last_updated"] = get_current_timestamp()
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_blackboard(agent: str, message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### [{timestamp}] [{agent}]\n* {message}\n"
    with open(BLACKBOARD_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"✅ Appended to Blackboard: [{agent}] {message}")


def update_project_state_table():
    if not PROJECT_STATE_FILE.exists():
        return
    tasks_data = load_tasks()
    tasks = tasks_data.get("tasks", [])

    rows = []
    for t in tasks:
        agent = t.get("assigned_to") or "*Open*"
        status = t.get("status", "todo")
        scope = t.get("title", "")
        task_id = t.get("id", "")
        rows.append(f"| **{agent}** | `{task_id}` | {scope} | `{status}` |")

    table_content = (
        "| Agent Name | Active Task ID | Scope / Modules | Status |\n"
        "| :--- | :--- | :--- | :--- |\n"
        + "\n".join(rows)
    )

    with open(PROJECT_STATE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(## 2\. Active Agents & Assignments\n\n).*?(\n\n## 3\.)"
    replacement = rf"\g<1>{table_content}\g<2>"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Update timestamp
    timestamp = get_current_timestamp()
    new_content = re.sub(r"\*\*Last Updated\*\*: .*?\n", f"**Last Updated**: {timestamp}\n", new_content)

    with open(PROJECT_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def cmd_status(args):
    print("=" * 70)
    print("🌟 SINMATE MULTI-AGENT STATE SNAPSHOT")
    print("=" * 70)
    
    # Git Branch
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        branch = "unknown"
    print(f"Git Branch: {branch}")
    print(f"Time (UTC): {get_current_timestamp()}\n")

    # Tasks
    tasks_data = load_tasks()
    tasks = tasks_data.get("tasks", [])
    print(f"📋 TASKS ({len(tasks)} total):")
    for t in tasks:
        status_icon = "🟢" if t["status"] == "done" else ("🟡" if t["status"] == "in_progress" else "⚪")
        assigned = f" -> [{t.get('assigned_to')}]" if t.get("assigned_to") else " (unassigned)"
        print(f"  {status_icon} {t['id']}: {t['title']} [{t['status']}]{assigned}")
        if t.get("locked_files"):
            print(f"     🔒 Locks: {', '.join(t['locked_files'])}")

    # Recent Blackboard entries
    if BLACKBOARD_FILE.exists():
        print("\n📢 RECENT BLACKBOARD ACTIVITY:")
        with open(BLACKBOARD_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent = [l for l in lines if l.startswith("### ") or l.startswith("* ")][-8:]
        for line in recent:
            print("  " + line.rstrip())
    print("=" * 70)


def cmd_claim(args):
    tasks_data = load_tasks()
    task = next((t for t in tasks_data.get("tasks", []) if t["id"] == args.task_id), None)
    if not task:
        print(f"❌ Error: Task '{args.task_id}' not found.")
        sys.exit(1)

    if task.get("status") == "in_progress" and task.get("assigned_to") and task.get("assigned_to") != args.agent:
        if not args.force:
            print(f"⚠️ Conflict: Task '{args.task_id}' is already claimed by '{task['assigned_to']}'. Use --force to override.")
            sys.exit(1)

    task["status"] = "in_progress"
    task["assigned_to"] = args.agent
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        task["locked_files"] = list(set(task.get("locked_files", []) + files))

    save_tasks(tasks_data)
    update_project_state_table()
    append_blackboard(args.agent, f"Claimed task `{args.task_id}` ({task['title']})")
    print(f"🔒 Agent '{args.agent}' successfully claimed task '{args.task_id}'.")


def cmd_release(args):
    tasks_data = load_tasks()
    task = next((t for t in tasks_data.get("tasks", []) if t["id"] == args.task_id), None)
    if not task:
        print(f"❌ Error: Task '{args.task_id}' not found.")
        sys.exit(1)

    agent_name = task.get("assigned_to") or "Unknown"
    new_status = args.status or "done"
    task["status"] = new_status
    task["locked_files"] = []
    if new_status == "done":
        task["completed_at"] = get_current_timestamp()

    summary = args.summary or f"Task `{args.task_id}` marked as {new_status}."
    save_tasks(tasks_data)
    update_project_state_table()
    append_blackboard(agent_name, f"Completed `{args.task_id}`: {summary}")
    print(f"🔓 Task '{args.task_id}' released with status '{new_status}'.")


def cmd_post(args):
    append_blackboard(args.agent, args.msg)


def cmd_add_task(args):
    tasks_data = load_tasks()
    if any(t["id"] == args.id for t in tasks_data.get("tasks", [])):
        print(f"❌ Error: Task ID '{args.id}' already exists.")
        sys.exit(1)

    new_task = {
        "id": args.id,
        "title": args.title,
        "description": args.desc or "",
        "status": "todo",
        "assigned_to": args.agent or None,
        "locked_files": [],
        "tags": [t.strip() for t in args.tags.split(",")] if args.tags else []
    }
    tasks_data["tasks"].append(new_task)
    save_tasks(tasks_data)
    update_project_state_table()
    print(f"✅ Added task '{args.id}': {args.title}")


def cmd_sync(args):
    """
    Ensures AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules, .github/copilot-instructions.md
    and CONVENTIONS.md are generated and aligned to .context/ SSOT.
    """
    print("🔄 Synchronizing all agent instructions to Single Source of Truth (.context/)...")

    # Universal Core Instruction Content
    universal_instructions = """# AI AGENT WORKSPACE DIRECTIVE: SINMATE

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
- **CLI Commands (macOS/Linux: `./agent <cmd>`, Windows: `.\\agent.ps1 <cmd>` or `python scripts/agent_hub.py <cmd>`)**:
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
"""

    targets = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / ".cursorrules",
        REPO_ROOT / "CONVENTIONS.md",
        REPO_ROOT / ".github" / "copilot-instructions.md"
    ]

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(universal_instructions)
        print(f"  ✓ Synced {target.relative_to(REPO_ROOT)}")

    update_project_state_table()
    print("✅ All agent instruction files successfully synchronized.")


def cmd_worktree(args):
    if args.action == "create":
        agent_name = args.agent
        branch_name = args.branch or f"agent/{agent_name}"
        target_dir = WORKTREES_DIR / agent_name

        if target_dir.exists():
            print(f"⚠️ Worktree directory already exists: {target_dir}")
            return

        WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
        print(f"🌱 Creating git worktree for agent '{agent_name}' on branch '{branch_name}'...")
        try:
            subprocess.check_call(
                ["git", "worktree", "add", "-b", branch_name, str(target_dir), "main"],
                cwd=REPO_ROOT
            )
        except subprocess.CalledProcessError:
            # If branch already exists, checkout without -b
            subprocess.check_call(
                ["git", "worktree", "add", str(target_dir), branch_name],
                cwd=REPO_ROOT
            )

        # Link .context directory to share state in real time
        worktree_context = target_dir / ".context"
        if worktree_context.exists():
            if worktree_context.is_dir() and not worktree_context.is_symlink():
                import shutil
                shutil.rmtree(worktree_context)

        # Create Windows directory junction or symlink
        if os.name == "nt":
            try:
                # Junction works without admin privileges
                subprocess.check_call(["cmd", "/c", "mklink", "/J", str(worktree_context), str(CONTEXT_DIR)])
                print("  ✓ Created NTFS Directory Junction for shared .context/")
            except Exception as e:
                print(f"  ⚠️ Could not create junction: {e}")
        else:
            try:
                os.symlink(str(CONTEXT_DIR), str(worktree_context))
                print("  ✓ Created Symlink for shared .context/")
            except Exception as e:
                print(f"  ⚠️ Could not create symlink: {e}")

        append_blackboard(agent_name, f"Spun up isolated worktree at `.worktrees/{agent_name}` on branch `{branch_name}`.")
        print(f"✨ Worktree ready at: {target_dir}")

    elif args.action == "list":
        try:
            out = subprocess.check_output(["git", "worktree", "list"], cwd=REPO_ROOT, text=True)
            print("🌲 ACTIVE GIT WORKTREES:")
            print(out)
        except Exception as e:
            print(f"❌ Error listing worktrees: {e}")

    elif args.action == "remove":
        agent_name = args.agent
        target_dir = WORKTREES_DIR / agent_name
        if not target_dir.exists():
            print(f"⚠️ Worktree not found: {target_dir}")
            return
        
        worktree_context = target_dir / ".context"
        if worktree_context.exists() or worktree_context.is_symlink():
            if os.name == "nt":
                try:
                    subprocess.check_call(["cmd", "/c", "rmdir", str(worktree_context)])
                except Exception:
                    pass
            else:
                try:
                    if worktree_context.is_symlink():
                        worktree_context.unlink()
                    elif worktree_context.is_dir():
                        import shutil
                        shutil.rmtree(worktree_context)
                except Exception:
                    pass

        try:
            subprocess.check_call(["git", "worktree", "remove", str(target_dir), "--force"], cwd=REPO_ROOT)
            print(f"🗑️ Removed worktree for '{agent_name}'.")
        except Exception as e:
            print(f"❌ Error removing worktree: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sinmate Multi-Agent Orchestration Hub")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="Show current state, tasks, and recent blackboard entries")

    # claim
    claim_p = subparsers.add_parser("claim", help="Claim a task and lock files")
    claim_p.add_argument("task_id", help="Task ID (e.g. TASK-002)")
    claim_p.add_argument("--agent", required=True, help="Name of the agent claiming the task")
    claim_p.add_argument("--files", help="Comma-separated list of files to lock")
    claim_p.add_argument("--force", action="store_true", help="Force claim if already assigned")

    # release
    rel_p = subparsers.add_parser("release", help="Release a claimed task")
    rel_p.add_argument("task_id", help="Task ID (e.g. TASK-002)")
    rel_p.add_argument("--summary", help="Summary of work completed")
    rel_p.add_argument("--status", choices=["done", "blocked", "todo"], default="done", help="New status")

    # post
    post_p = subparsers.add_parser("post", help="Post an update to the agent blackboard")
    post_p.add_argument("--agent", required=True, help="Name of posting agent")
    post_p.add_argument("--msg", required=True, help="Message text")

    # add-task
    add_p = subparsers.add_parser("add-task", help="Add a new task")
    add_p.add_argument("--id", required=True, help="New Task ID (e.g. TASK-009)")
    add_p.add_argument("--title", required=True, help="Short title")
    add_p.add_argument("--desc", help="Detailed description")
    add_p.add_argument("--agent", help="Pre-assign to an agent")
    add_p.add_argument("--tags", help="Comma-separated tags")

    # sync
    subparsers.add_parser("sync", help="Synchronize all agent instruction files")

    # worktree
    wt_p = subparsers.add_parser("worktree", help="Manage git worktrees for isolated parallel agents")
    wt_sub = wt_p.add_subparsers(dest="action")
    
    wt_create = wt_sub.add_parser("create", help="Create a worktree")
    wt_create.add_argument("agent", help="Agent identifier (e.g. claude, codex, opencode)")
    wt_create.add_argument("branch", nargs="?", help="Branch name (default: agent/<agent>)")

    wt_sub.add_parser("list", help="List active worktrees")

    wt_remove = wt_sub.add_parser("remove", help="Remove an agent worktree")
    wt_remove.add_argument("agent", help="Agent identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "status":
        cmd_status(args)
    elif args.command == "claim":
        cmd_claim(args)
    elif args.command == "release":
        cmd_release(args)
    elif args.command == "post":
        cmd_post(args)
    elif args.command == "add-task":
        cmd_add_task(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "worktree":
        cmd_worktree(args)


if __name__ == "__main__":
    main()
