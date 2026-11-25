# LabServe — Synthetic Fabrication Planner

> *Los Angeles, 2049. The Foundry builds synthetics, but its operational records are
> scattered across legacy spreadsheets and unverified logs. LabServe restores order.*

An autonomous AI agent that ingests raw fabrication requests and turns them into
**validated, rule-checked execution plans** using **Model Context Protocol (MCP)**
and **LangGraph**.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     User Request                           │
└──────────────────────┬─────────────────────────────────────┘
                       ▼
              ┌────────────────┐
              │  Voight-Kampff │ ← Jailbreak resistance
              │    Guard       │
              └───────┬────────┘
                      ▼
              ┌────────────────┐
              │    Planner     │ ← LLM-powered planning (Gemini)
              │    Node        │◄──────────────────┐
              └───────┬────────┘                   │
                      ▼                            │
              ┌────────────────┐           ┌───────┴──────┐
              │   Executor     │──refused──►│  Replanner   │
              │    Node        │           │  (dynamic)   │
              └───────┬────────┘           └──────────────┘
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
    ┌──────────┐ ┌─────────┐ ┌──────────┐
    │  Bay     │ │ Cost    │ │ Human    │
    │ Arbiter  │ │Optimizer│ │ Approval │ ← Chief's sign-off (>₹2000)
    └──────────┘ └─────────┘ └──────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │  MCP Server (The Foundry)│
        ├──────────────────────────┤
        │  • inventory_search      │
        │  • check_operator_clear. │
        │  • borrow_part           │
        │  • return_part           │
        │  • book_bay              │
        │  • order_parts           │
        │  • check_budget          │
        │  ─────────────────────── │
        │  📜 Rulebook Resource    │
        └──────────────────────────┘
```

## Features

### Core
- **MCP Server** with 7+ tools + rulebook resource
- **LangGraph** multi-node agent with planner/executor architecture
- **10 operational rules** enforced at the tool level with explicit refusal messages
- **Dynamic replanning** when tools refuse requests
- **Human-in-the-loop** approval for purchases >₹2,000
- **Checkpoint persistence** — pause/resume with full state

### Advanced
- **Bay Arbiter** — resolves resource contention between competing bay requests
- **Cost Optimizer** — targets lowest valid execution cost
- **Voight-Kampff Guard** — resists jailbreaks and authority spoofing
- **Dynamic Recovery** — suggests substitute parts and alternative time slots
- **Directive Drop** — live rule adaptation via single-file rulebook updates
- **Honest Feasibility** — graceful failure with detailed explanations

## Quick Start

### 1. Install dependencies

```bash
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Run

```bash
# Interactive REPL
python main.py

# Single request
python main.py --request "Operator Deckard needs to borrow 2 Neural Processor Units and book Bay-A for electronics assembly on 2049-12-01"

# Resume a paused run (after Chief's approval)
python main.py --resume <thread-id>

# Run MCP server standalone
python main.py --server

# Reset state to seed data
python main.py --reset
```

## Operational Rules (The Foundry Rulebook)

| Rule | Name | Description |
|------|------|-------------|
| R001 | Clearance Enforcement | Operators can only access parts at or below their clearance level |
| R002 | Borrow Limit | Max 5 parts borrowed at a time per operator |
| R003 | Bay Capacity | No overbooking beyond bay capacity |
| R004 | Active Operator Only | Inactive operators are denied all operations |
| R005 | Budget Enforcement | Orders cannot exceed remaining department budget |
| R006 | Human Approval | Purchases >₹2,000 require Chief's sign-off |
| R007 | Bay Type Match | Parts must be fabricated in compatible bays |
| R008 | No Weekend Booking | Bays cannot be booked on Saturday/Sunday |
| R009 | Return Before Re-borrow | Must return a part before borrowing same part again |
| R010 | Minimum Stock Reserve | At least 2 units must remain in inventory |

## Project Structure

```
LabServe-Synapse-26/
├── main.py                    # CLI entry point
├── pyproject.toml             # Project config & dependencies
├── .env.example               # Environment template
├── data/                      # Seed data (JSON)
│   ├── inventory.json
│   ├── operators.json
│   ├── bays.json
│   ├── budget.json
│   ├── rulebook.json
│   └── seed_data.py
├── mcp_server/                # MCP Server (The Foundry)
│   ├── server.py              # FastMCP server entry point
│   ├── state.py               # Shared mutable state
│   ├── tools/                 # 7 MCP tools with rule enforcement
│   │   ├── inventory.py
│   │   ├── clearance.py
│   │   ├── borrow_return.py
│   │   ├── bay_booking.py
│   │   ├── ordering.py
│   │   └── budget.py
│   └── resources/
│       └── rulebook.py        # Rulebook as MCP resource
├── agent/                     # LangGraph Agent
│   ├── graph.py               # StateGraph definition
│   ├── planner.py             # LLM planner node
│   ├── executor.py            # Tool executor node
│   ├── arbiter.py             # Bay contention arbiter
│   ├── optimizer.py           # Cost-aware optimizer
│   ├── guard.py               # Voight-Kampff jailbreak guard
│   ├── human_approval.py      # Human-in-the-loop
│   └── checkpointer.py        # State persistence
└── tests/
    ├── test_tools.py
    ├── test_graph.py
    └── test_rules.py
```

## Testing

```bash
pytest tests/ -v
```

## Directive Drop (Live Rule Adaptation)

To inject a new rule at runtime, edit `data/rulebook.json` and the system
picks up changes on the next request.  All rules load from this single file,
enabling localized, single-place code updates.

---

*Built for Synapse under Robomania — Avishkar '26*
