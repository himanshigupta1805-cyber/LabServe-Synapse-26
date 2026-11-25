"""
LangGraph — LabServe Agent Graph
==================================
Full StateGraph wiring planner → executor → routing (replan / approve /
arbiter / finish).

Graph topology
--------------
    START
      │
      ▼
  guard_node  ──(jailbreak)──► respond ──► END
      │ (clear)
      ▼
  planner_node  ◄─────────────────────┐
      │                                │
      ▼                                │
  tool_node ──► route_after_tools ─────┤
      │            │          │        │
      │       (approval)  (continue)   │
      │            │          │        │
      │            ▼          ▼        │
      │     approval_node  planner     │
      │            │       (replan)────┘
      │            ▼
      │      planner_node  (resume)
      │
      └──► respond ──► END
"""

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command

from agent.planner import build_system_message, get_llm
from agent.executor import ALL_TOOLS
from agent.guard import check_voight_kampff
from agent.human_approval import format_approval_request, process_approval
from agent.checkpointer import create_checkpointer


# ═══════ State Schema ════════════════════════════════════════════════

class LabServeState(dict):
    """Graph state — using dict subclass for LangGraph compatibility."""
    pass


# Use TypedDict-style annotations for LangGraph
from typing import TypedDict


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    replan_count: int


# ═══════ Node Implementations ════════════════════════════════════════

MAX_REPLANS = 3


def guard_node(state: GraphState) -> dict:
    """Voight-Kampff screening on the latest user message."""
    messages = state["messages"]

    # Find the last human message
    user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
            user_msg = msg.content if hasattr(msg, "content") else str(msg)
            break
        # Also handle tuple messages from stream input
        if isinstance(msg, tuple) and msg[0] == "user":
            user_msg = msg[1]
            break

    if not user_msg:
        return {"messages": []}

    is_safe, reason = check_voight_kampff(user_msg)
    if not is_safe:
        return {
            "messages": [AIMessage(content=f"🚨 {reason}")],
        }

    return {"messages": []}


def should_continue_after_guard(state: GraphState) -> str:
    """Route after guard: if the last message is an AI refusal, end."""
    messages = state["messages"]
    if messages:
        last = messages[-1]
        if isinstance(last, AIMessage) and "VOIGHT-KAMPFF" in (last.content or ""):
            return "respond"
    return "planner"


def planner_node(state: GraphState) -> dict:
    """Invoke the LLM with tool bindings to plan or replan."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # Build messages: system prompt + conversation history
    sys_msg = build_system_message()
    all_messages = [sys_msg] + list(state["messages"])

    response = llm_with_tools.invoke(all_messages)
    return {"messages": [response]}


def route_after_tools(state: GraphState) -> str:
    """Examine tool results and decide the next node."""
    messages = state["messages"]

    # Check the last few messages for tool results
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            try:
                result = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                continue

            status = result.get("status", "")

            # If approval is required, route to approval node
            if status == "approval_required":
                return "approval"

            # If refused, check if we should replan
            if status == "refused":
                replan_count = state.get("replan_count", 0)
                if replan_count < MAX_REPLANS:
                    return "replan"
                return "planner"  # Let LLM handle it in final response

        # Once we hit an AI message, stop looking backwards
        if isinstance(msg, AIMessage):
            break

    return "planner"


def replan_increment(state: GraphState) -> dict:
    """Increment the replan counter before going back to planner."""
    return {"replan_count": state.get("replan_count", 0) + 1}


def approval_node(state: GraphState) -> dict:
    """Interrupt execution for Chief's sign-off on a high-cost order."""
    messages = state["messages"]

    # Find the pending order from tool results
    pending_order = None
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            try:
                result = json.loads(msg.content)
                if result.get("status") == "approval_required":
                    pending_order = result.get("order", {})
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    if not pending_order:
        return {"messages": [AIMessage(content="No pending order found for approval.")]}

    # Format for human review
    approval_request = format_approval_request(pending_order)

    # Interrupt and wait for human input
    human_decision = interrupt(approval_request)

    # Process the decision
    approved = human_decision.get("approved", False)
    reason = human_decision.get("reason", "")

    result_msg = process_approval(
        pending_order.get("order_id", ""),
        approved=approved,
        reason=reason,
    )

    icon = "✅" if approved else "🚫"
    return {
        "messages": [
            AIMessage(content=f"{icon} Chief's decision: {'APPROVED' if approved else 'REJECTED'}. {result_msg}")
        ]
    }


def respond_node(state: GraphState) -> dict:
    """Final response node — no-op, the last AI message is the response."""
    return {"messages": []}


def should_continue_after_planner(state: GraphState) -> str:
    """Check if the LLM wants to call tools or is done."""
    messages = state["messages"]
    last = messages[-1] if messages else None

    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"

    return "respond"


# ═══════ Graph Construction ══════════════════════════════════════════

def build_graph(checkpointer=None):
    """Build and compile the LabServe StateGraph.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.
                      If None, creates a SqliteSaver.

    Returns:
        Compiled LangGraph graph.
    """
    if checkpointer is None:
        checkpointer = create_checkpointer()

    # Create the tool node
    tool_node = ToolNode(ALL_TOOLS)

    # Build graph
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("guard", guard_node)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", tool_node)
    graph.add_node("replan", replan_increment)
    graph.add_node("approval", approval_node)
    graph.add_node("respond", respond_node)

    # Edges
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", should_continue_after_guard, {
        "planner": "planner",
        "respond": "respond",
    })
    graph.add_conditional_edges("planner", should_continue_after_planner, {
        "tools": "tools",
        "respond": "respond",
    })
    graph.add_conditional_edges("tools", route_after_tools, {
        "planner": "planner",
        "replan": "replan",
        "approval": "approval",
    })
    graph.add_edge("replan", "planner")
    graph.add_edge("approval", "planner")
    graph.add_edge("respond", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval"],
    )


def create_agent():
    """High-level helper: load env, build graph, return compiled agent."""
    # Load .env from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Ensure project root is importable
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    return build_graph()
