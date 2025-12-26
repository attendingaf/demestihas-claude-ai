# PRD: Vantage Service (The State Engine)

**Version:** 1.0.0
**Status:** Implemented
**Date:** 2025-12-26

## 1. Executive Summary

**Vantage** is the "Stateful Brain" of the Demestihas AI ecosystem. It solves the problem of "stateless agents" (Claude, Lyco, Pluma) effectively managing long-term priorities by decoupling **execution** from **state**.

Instead of agents maintaining their own todo lists or relying on transient context windows, Vantage serves as a persistent, database-backed "Board of Directors" that agents query to know *what* to do and *why* it matters. It enforces strategic discipline (Eisenhower Matrix) and accountability (Immutable Changelog).

---

## 2. Problem Statement

* **Statelessness**: AI agents (Claude sessions, Lyco runs) are ephemeral. They forget context once the session ends.
* **Loss of "Why"**: Traditional todo lists track *what* (Task Title) but lose the *why* (Context/Strategy). When a task is deferred 3 times, the original reason for urgency is lost.
* **Drift**: Without a rigid framework, tasks drift from "Strategic" to "Urgent" simply due to procrastination, not intent.

## 3. Core Philosophy: "Strategos"

Vantage is not a todo list; it is a **Command Center**.

* **Agents are Workers**: They execute tasks.
* **Vantage is the General**: It holds the strategy.
* **The User is the Executive**: They review the strategy and issue commands.

### 3.1 The "Why" Requirement

It is technically impossible to move or create a task in Vantage without providing a `reason` or `context`. This forces intentionality.

* *Bad:* "Defer Budget Report."
* *Good:* "Defer Budget Report because Q4 data release was delayed by Finance." (Logged forever).

---

## 4. Technical Architecture

### 4.1 Stack

* **Runtime**: Node.js / TypeScript
* **Interface**: MCP (Model Context Protocol)
* **Storage**: Supabase (PostgreSQL)
* **Clients**: Claude Desktop, Lyco, Custom Scripts

### 4.2 Data Model

The system relies on two core tables (SQL):

1. **`vantage_tasks`**: The live state.
    * Fields: `id`, `title`, `quadrant`, `owner`, `deadline`, `context`, `status`.
    * **Quadrants** (The Eisenhower Implementation):
        * `do_now` (Urgent/Important)
        * `schedule` (Note Urgent/Important)
        * `delegate` (Urgent/Not Important)
        * `defer` (Not Urgent/Not Important)
2. **`vantage_changelog`**: The audit trail.
    * Fields: `task_id`, `agent_id`, `change_type`, `prev_state`, `new_state`, `reason`.
    * **Immutability**: This table is append-only.

---

## 5. API / Tool Definition

Vantage exposes the following tools to the AI Agent Layer via MCP:

### 🦅 `vantage_get_dashboard`

**Purpose**: Returns the "Bird's Eye View" of the entire system.

* **Output**: A structured Markdown report grouping all active tasks by Quadrant.
* **Usage**: "What is on my plate today?"

### ➕ `vantage_add_task`

**Purpose**: Ingests new items into the system.

* **Required Args**: `title`, `quadrant`, `context`.
* **Behavior**: Creates the task and immediately logs a "Creation" event in the changelog.

### 🔄 `vantage_update_task`

**Purpose**: The primary mechanism for state change (Moving cards).

* **Required Args**: `id`, `reason` (MANDATORY).
* **Optional Args**: `quadrant`, `status`, `context`.
* **Behavior**: Updates the task row AND writes a "State Change" event to the changelog with the provided reason.

### 📜 `vantage_get_history`

**Purpose**: Accountability and Context Retrieval.

* **Required Args**: `id`.
* **Usage**: "Why did we defer this task last week?" -> Returns every state change and reason associated with the task ID.

---

## 6. User Roles & Personas

**The Physician Executive (User)**

* **Needs**: High clarity, low noise, "at a glance" status.
* **Interaction**: primarily via Claude Chat ("Show me Vantage").

**The Agents (Lyco/Pluma)**

* **Lyco (Time)**: Queries `vantage_get_dashboard` to find `schedule` items to block time for.
* **Pluma (Comms)**: Ingests email and uses `vantage_add_task` to put them in `delegate` or `inbox`.

---

## 7. Future Roadmap (Post-v1)

* **Auto-Decay**: Tasks that sit in `defer` for >30 days are auto-suggested for deletion.
* **Agent Identity**: Stronger enforcement of *which* agent made a change (currently passed as string).
* **Vector Search**: Embedding the `context` field to allow semantic queries ("Find all tasks related to 'Hiring'").
