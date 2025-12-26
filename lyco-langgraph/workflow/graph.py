"""
Main LangGraph workflow for Lyco v2 task management.

This graph orchestrates the entire task processing pipeline,
from signal capture through intelligent routing to storage.
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, Literal
import os
import sys
from pathlib import Path

# Add src directory to path to reuse v2 code
lyco_v2_path = Path(__file__).parent.parent.parent / "lyco-v2"
if lyco_v2_path.exists():
    sys.path.insert(0, str(lyco_v2_path))

from .state import LycoGraphState
from .nodes import (
    # Capture nodes
    capture_email_signal,
    capture_calendar_signal,
    capture_terminal_input,
    capture_api_request,
    capture_webhook,

    # Processing nodes
    parse_with_llm,
    determine_energy_level,
    apply_eisenhower_matrix,
    detect_skip_patterns,
    process_skip_intelligence,

    # Decision nodes
    route_by_priority,
    process_rounds_mode,

    # Action nodes
    send_notification,
    block_calendar_time,
    assign_to_family,
    park_for_later,
    move_to_archive,
    update_learning_model,

    # Storage nodes
    update_redis_cache,
    persist_to_database,
    synchronize_with_notion,

    # Monitoring nodes
    track_health_metrics,
    update_performance_stats
)


def determine_entry_point(state: LycoGraphState) -> str:
    """Determine which capture node to use based on source"""
    source = state.get("source", "terminal")

    source_map = {
        "email": "capture_email",
        "calendar": "capture_calendar",
        "terminal": "capture_terminal",
        "api": "capture_api",
        "webhook": "capture_webhook",
        "rounds": "capture_api",  # Rounds uses API capture
        "notion": "capture_webhook"  # Notion webhooks
    }

    return source_map.get(source, "capture_terminal")


def determine_skip_action(state: LycoGraphState) -> str:
    """Determine action based on skip intelligence analysis"""
    if state.get("should_park"):
        return "park"
    elif state.get("delegation_signal"):
        return "delegate"
    elif state.get("skip_count", 0) > 7:
        return "archive"
    else:
        return "learn"


def route_by_quadrant_and_energy(state: LycoGraphState) -> str:
    """Route task based on Eisenhower quadrant and energy level"""
    quadrant = state.get("quadrant")
    energy_level = state.get("energy_level")
    current_user_energy = state.get("current_user_energy", "medium")
    energy_mismatch = state.get("energy_mismatch", False)

    # Energy mismatch handling
    if energy_mismatch:
        if energy_level == "high" and current_user_energy == "low":
            return "park"  # Park high-energy tasks when tired
        elif energy_level == "low" and current_user_energy == "high":
            return "rounds"  # Quick decisions when energized

    # Quadrant-based routing
    routing_map = {
        "DO_FIRST": "do_first",
        "SCHEDULE": "schedule",
        "DELEGATE": "delegate",
        "ELIMINATE": "eliminate"
    }

    return routing_map.get(quadrant, "rounds")


def process_rounds_decision(state: LycoGraphState) -> str:
    """Process rounds mode decision"""
    decision = state.get("rounds_decision")

    decision_map = {
        "do_now": "do_now",
        "delegate": "delegate",
        "defer": "defer",
        "delete": "delete"
    }

    return decision_map.get(decision, "defer")


def should_learn(state: LycoGraphState) -> bool:
    """Determine if we should update the learning model"""
    patterns = state.get("patterns_detected", [])
    skip_count = state.get("skip_count", 0)
    confidence = state.get("confidence_score", 0)

    return len(patterns) > 0 or skip_count > 3 or confidence < 0.7


def create_lyco_workflow() -> StateGraph:
    """
    Create the main Lyco workflow graph.

    This graph implements the complete v2 functionality:
    - Multi-source signal capture
    - LLM parsing with Claude Haiku
    - Energy-based routing
    - Eisenhower Matrix classification
    - Skip intelligence with pattern learning
    - Rounds mode for rapid decisions
    - Redis caching and PostgreSQL persistence
    - Notion synchronization
    - Health monitoring
    """

    # Initialize workflow with state schema
    workflow = StateGraph(LycoGraphState)

    # ===== CAPTURE NODES =====
    workflow.add_node("capture_email", capture_email_signal)
    workflow.add_node("capture_calendar", capture_calendar_signal)
    workflow.add_node("capture_terminal", capture_terminal_input)
    workflow.add_node("capture_api", capture_api_request)
    workflow.add_node("capture_webhook", capture_webhook)

    # ===== PROCESSING NODES =====
    workflow.add_node("parse_task", parse_with_llm)
    workflow.add_node("classify_energy", determine_energy_level)
    workflow.add_node("assign_quadrant", apply_eisenhower_matrix)
    workflow.add_node("check_patterns", detect_skip_patterns)
    workflow.add_node("analyze_skip", process_skip_intelligence)

    # ===== DECISION NODES =====
    workflow.add_node("route_action", route_by_priority)
    workflow.add_node("rounds_decision", process_rounds_mode)

    # ===== ACTION NODES =====
    workflow.add_node("notify_user", send_notification)
    workflow.add_node("schedule_calendar", block_calendar_time)
    workflow.add_node("delegate_task", assign_to_family)
    workflow.add_node("park_task", park_for_later)
    workflow.add_node("archive_task", move_to_archive)
    workflow.add_node("learn_pattern", update_learning_model)

    # ===== STORAGE NODES =====
    workflow.add_node("cache_task", update_redis_cache)
    workflow.add_node("save_database", persist_to_database)
    workflow.add_node("sync_notion", synchronize_with_notion)

    # ===== MONITORING NODES =====
    workflow.add_node("track_health", track_health_metrics)
    workflow.add_node("update_stats", update_performance_stats)

    # ===== ENTRY ROUTING =====
    workflow.add_conditional_edges(
        START,
        determine_entry_point,
        {
            "capture_email": "capture_email",
            "capture_calendar": "capture_calendar",
            "capture_terminal": "capture_terminal",
            "capture_api": "capture_api",
            "capture_webhook": "capture_webhook"
        }
    )

    # ===== CAPTURE → PARSING =====
    for capture_node in ["capture_email", "capture_calendar", "capture_terminal",
                        "capture_api", "capture_webhook"]:
        workflow.add_edge(capture_node, "parse_task")

    # ===== PARSING → CLASSIFICATION =====
    workflow.add_edge("parse_task", "classify_energy")
    workflow.add_edge("classify_energy", "assign_quadrant")
    workflow.add_edge("assign_quadrant", "check_patterns")

    # ===== PATTERN CHECK → SKIP OR ROUTE =====
    workflow.add_conditional_edges(
        "check_patterns",
        lambda x: "analyze_skip" if x.get("skip_count", 0) > 2 else "route_action",
        {
            "analyze_skip": "analyze_skip",
            "route_action": "route_action"
        }
    )

    # ===== SKIP ANALYSIS → ACTIONS =====
    workflow.add_conditional_edges(
        "analyze_skip",
        determine_skip_action,
        {
            "park": "park_task",
            "delegate": "delegate_task",
            "archive": "archive_task",
            "learn": "learn_pattern"
        }
    )

    # ===== MAIN ROUTING → ACTIONS =====
    workflow.add_conditional_edges(
        "route_action",
        route_by_quadrant_and_energy,
        {
            "do_first": "notify_user",
            "schedule": "schedule_calendar",
            "delegate": "delegate_task",
            "eliminate": "archive_task",
            "rounds": "rounds_decision",
            "park": "park_task"
        }
    )

    # ===== ROUNDS MODE → ACTIONS =====
    workflow.add_conditional_edges(
        "rounds_decision",
        process_rounds_decision,
        {
            "do_now": "notify_user",
            "delegate": "delegate_task",
            "defer": "park_task",
            "delete": "archive_task"
        }
    )

    # ===== ACTIONS → CACHE =====
    action_nodes = ["notify_user", "schedule_calendar", "delegate_task",
                   "park_task", "archive_task", "learn_pattern"]
    for action_node in action_nodes:
        workflow.add_edge(action_node, "cache_task")

    # ===== STORAGE CHAIN =====
    workflow.add_edge("cache_task", "save_database")
    workflow.add_edge("save_database", "sync_notion")

    # ===== MONITORING =====
    workflow.add_edge("sync_notion", "track_health")
    workflow.add_edge("track_health", "update_stats")
    workflow.add_edge("update_stats", END)

    # Compile with checkpointing for state persistence
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Create the app instance for LangServe
app = create_lyco_workflow()


# Additional utility functions for Studio debugging
def get_graph_structure():
    """Return graph structure for visualization"""
    return {
        "nodes": list(app.nodes.keys()),
        "edges": [
            {"from": e[0], "to": e[1], "condition": e[2] if len(e) > 2 else None}
            for e in app.edges
        ]
    }


def validate_graph():
    """Validate graph structure and connections"""
    try:
        # Check all nodes are connected
        orphan_nodes = []
        for node in app.nodes:
            has_incoming = any(e[1] == node for e in app.edges)
            has_outgoing = any(e[0] == node for e in app.edges)
            if not (has_incoming or has_outgoing) and node != START:
                orphan_nodes.append(node)

        return {
            "valid": len(orphan_nodes) == 0,
            "orphan_nodes": orphan_nodes,
            "total_nodes": len(app.nodes),
            "total_edges": len(app.edges)
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
