#!/usr/bin/env python3
"""
LabServe — Synthetic Fabrication Planner
=========================================
Main entry point.  Autonomous AI agent that ingests raw fabrication
requests and turns them into validated, rule-checked execution plans.

Usage:
    python main.py                          # Interactive REPL
    python main.py --request "Build a ..."  # Single request
    python main.py --resume <thread_id>     # Resume a checkpointed run
    python main.py --reset                  # Reset state to seed data
    python main.py --server                 # Run MCP server standalone
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


# ── Banner ───────────────────────────────────────────────────────────

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██╗      █████╗ ██████╗ ███████╗███████╗██████╗ ██╗   ██╗ ║
║   ██║     ██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗██║   ██║ ║
║   ██║     ███████║██████╔╝███████╗█████╗  ██████╔╝██║   ██║ ║
║   ██║     ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝ ║
║   ███████╗██║  ██║██████╔╝███████║███████╗██║  ██║ ╚████╔╝  ║
║   ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝   ║
║                                                              ║
║   Synthetic Fabrication Planner — The Foundry, LA 2049       ║
║   MCP + LangGraph Autonomous Agent                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def _print_msg(msg):
    """Pretty-print a LangGraph message."""
    if not hasattr(msg, "content") or not msg.content:
        return
    if hasattr(msg, "type"):
        if msg.type == "ai" and not msg.tool_calls:
            print(f"\n🤖 Agent: {msg.content}")
        elif msg.type == "tool":
            try:
                r = json.loads(msg.content)
                s = r.get("status", "?")
                icon = {"success": "✅", "refused": "🚫", "error": "❌",
                        "approval_required": "⏸️"}.get(s, "📋")
                print(f"  {icon} {msg.name}: {r.get('message', msg.content)}")
            except (json.JSONDecodeError, AttributeError):
                print(f"  📋 Tool: {msg.content}")


# ── MCP Server Mode ─────────────────────────────────────────────────

def run_mcp_server():
    from mcp_server.server import mcp as mcp_app
    print("[LabServe] Starting MCP server (The Foundry) …")
    mcp_app.run()


# ── Single Request ───────────────────────────────────────────────────

def run_single_request(request: str, thread_id: str | None = None):
    from agent.graph import create_agent

    graph = create_agent()
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}

    print(f"\n[LabServe] Thread: {tid}")
    print(f"[LabServe] Processing: {request}\n")
    print("─" * 60)

    for event in graph.stream(
        {"messages": [("user", request)]},
        config=config,
        stream_mode="values",
    ):
        if event.get("messages"):
            _print_msg(event["messages"][-1])

    print("─" * 60)

    # Check for interrupt
    try:
        snap = graph.get_state(config)
        if snap.next:
            print("\n⏸️  EXECUTION PAUSED — awaiting Chief's sign-off")
            print(f"   Resume with: python main.py --resume {tid}")
            return tid, True
    except Exception:
        pass

    print("\n✅ Execution complete.")
    return tid, False


# ── Resume ───────────────────────────────────────────────────────────

def resume_run(thread_id: str):
    from agent.graph import create_agent
    from langgraph.types import Command

    graph = create_agent()
    config = {"configurable": {"thread_id": thread_id}}

    snap = graph.get_state(config)
    if not snap.next:
        print("[LabServe] No pending interrupts for this thread.")
        return

    print(f"\n[LabServe] Resuming thread: {thread_id}")
    print(f"[LabServe] Pending at: {', '.join(snap.next)}")

    while True:
        choice = input("\n🔑 Chief's Decision — [A]pprove / [R]eject / [Q]uit: ").strip().upper()
        if choice in ("A", "R", "Q"):
            break
        print("   Enter A, R, or Q.")

    if choice == "Q":
        print("[LabServe] Aborted. State preserved.")
        return

    approved = choice == "A"
    reason = input("   Reason: ").strip() if not approved else ""
    approval_result = {"approved": approved, "reason": reason}

    print("─" * 60)
    for event in graph.stream(
        Command(resume=approval_result),
        config=config,
        stream_mode="values",
    ):
        if event.get("messages"):
            _print_msg(event["messages"][-1])
    print("─" * 60)
    print("\n✅ Resumed execution complete.")


# ── Interactive REPL ─────────────────────────────────────────────────

def run_interactive():
    from agent.graph import create_agent

    graph = create_agent()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print(BANNER)
    print(f"Thread: {thread_id}")
    print("Type a fabrication request, 'reset' to reload seed data,")
    print("'approve <order_id>' / 'reject <order_id> <reason>', or 'quit'.\n")

    while True:
        try:
            user_input = input("⚡ Foundry> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[LabServe] Goodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("[LabServe] Shutting down. Checkpoints preserved.")
            break
        if user_input.lower() == "reset":
            from mcp_server.state import reset_state
            reset_state()
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            print("[LabServe] State reset. New thread started.")
            continue
        if user_input.lower().startswith("approve "):
            from agent.human_approval import process_approval
            oid = user_input.split(" ", 1)[1].strip()
            print(f"  ✅ {process_approval(oid, True)}")
            continue
        if user_input.lower().startswith("reject "):
            from agent.human_approval import process_approval
            parts = user_input.split(" ", 2)
            oid = parts[1].strip()
            reason = parts[2].strip() if len(parts) > 2 else ""
            print(f"  🚫 {process_approval(oid, False, reason)}")
            continue

        print()
        try:
            for event in graph.stream(
                {"messages": [("user", user_input)]},
                config=config,
                stream_mode="values",
            ):
                if event.get("messages"):
                    _print_msg(event["messages"][-1])

            try:
                snap = graph.get_state(config)
                if snap.next:
                    print(f"\n⏸️  PAUSED at: {', '.join(snap.next)}")
                    print("   Type 'approve <order_id>' or 'reject <order_id> <reason>'")
            except Exception:
                pass

        except Exception as e:
            print(f"❌ Error: {e}")
        print()


# ── CLI Entry Point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LabServe — Synthetic Fabrication Planner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py                                        # Interactive mode
  python main.py --request "Fabricate a replicant arm"  # Single request
  python main.py --resume abc-123                       # Resume paused run
  python main.py --server                               # Run MCP server
  python main.py --reset                                # Reset seed data
""")
    parser.add_argument("--request", "-r", type=str)
    parser.add_argument("--resume", type=str)
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.server:
        run_mcp_server()
    elif args.reset:
        from mcp_server.state import reset_state
        reset_state()
        print("[LabServe] State reset.")
    elif args.resume:
        print(BANNER)
        resume_run(args.resume)
    elif args.request:
        print(BANNER)
        run_single_request(args.request)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
