"""
Enhanced state definition for Lyco LangGraph workflow.

This state schema captures all aspects of task processing from v2,
including energy levels, skip intelligence, and pattern learning.
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any, Annotated
from datetime import datetime
from uuid import UUID
from langgraph.graph.message import add_messages


class LycoGraphState(TypedDict):
    """
    Complete state for Lyco task management workflow.

    This state tracks a task through its entire lifecycle:
    1. Signal capture (email, calendar, terminal, API)
    2. LLM parsing and extraction
    3. Energy and priority classification
    4. Skip pattern detection and learning
    5. Routing and action decisions
    6. Storage and synchronization
    """

    # ========== Signal Input ==========
    signal_id: Optional[str]  # UUID as string for serialization
    raw_input: str
    source: Literal["email", "terminal", "calendar", "notion", "api", "rounds", "webhook"]
    timestamp: str  # ISO format datetime string
    user_id: str  # mene@beltlineconsulting.co or menelaos4@gmail.com
    source_metadata: Dict[str, Any]  # Email headers, calendar event ID, etc.

    # ========== Parsed Task ==========
    task_id: Optional[str]  # UUID as string
    task_title: Optional[str]
    task_description: Optional[str]
    context_required: List[str]
    extracted_entities: Dict[str, Any]  # People, dates, locations, etc.

    # ========== Energy Classification ==========
    energy_level: Optional[Literal["high", "medium", "low"]]
    current_user_energy: Optional[str]  # Real-time energy detection
    energy_mismatch: bool
    energy_recommendation: Optional[str]

    # ========== Eisenhower Matrix ==========
    urgency: Optional[int]  # 1-5 scale
    importance: Optional[int]  # 1-5 scale
    quadrant: Optional[Literal["DO_FIRST", "SCHEDULE", "DELEGATE", "ELIMINATE"]]
    priority_score: Optional[float]  # Composite score for sorting

    # ========== Skip Intelligence (from v2) ==========
    skip_count: int
    skip_reasons: List[str]  # ["too_tired", "no_context", "needs_cindy", "blocked", "not_ready"]
    skip_pattern: Optional[str]  # Detected pattern name
    should_park: bool
    park_until: Optional[str]  # ISO format datetime
    delegation_signal: Optional[Dict[str, Any]]
    auto_skip_confidence: Optional[float]

    # ========== Assignment & Scheduling ==========
    assigned_to: Optional[Literal["mene", "cindy", "both", "elena", "aris", "team"]]
    deadline: Optional[str]  # ISO format datetime
    time_estimate: Optional[int]  # minutes
    rescheduled_for: Optional[str]  # ISO format datetime
    calendar_block_id: Optional[str]  # Google Calendar event ID

    # ========== Pattern Learning ==========
    patterns_detected: List[Dict[str, Any]]
    learning_adjustments: Dict[str, Any]
    prompt_version: int
    model_feedback: Optional[str]

    # ========== Performance Metrics ==========
    processing_time_ms: int
    cache_hit: bool
    confidence_score: float
    tokens_used: Optional[int]
    model_used: Optional[str]  # claude-haiku, gpt-4, etc.

    # ========== Routing Decision ==========
    action: Optional[Literal[
        "notify",      # Send notification to user
        "schedule",    # Block calendar time
        "delegate",    # Assign to family member
        "archive",     # Move to completed/eliminated
        "skip",        # Skip with intelligence
        "park",        # Park for later
        "rounds",      # Enter rounds mode
        "learn",       # Update learning model
        "escalate",    # Escalate to urgent
        "batch"        # Batch with similar tasks
    ]]
    action_reason: Optional[str]
    alternative_actions: List[str]

    # ========== Output & Sync ==========
    notification_sent: bool
    notification_channel: Optional[Literal["email", "sms", "slack", "terminal"]]
    calendar_blocked: bool
    notion_synced: bool
    notion_page_id: Optional[str]
    redis_published: bool
    database_saved: bool

    # ========== Rounds Mode (from v2) ==========
    rounds_session_id: Optional[str]  # UUID as string
    rounds_decision: Optional[Literal["do_now", "delegate", "defer", "delete"]]
    rounds_decision_time_ms: Optional[int]
    rounds_position: Optional[int]  # Position in rounds queue

    # ========== Error Handling ==========
    error: Optional[str]
    error_type: Optional[str]
    retry_count: int
    should_retry: bool

    # ========== Messages (for LangGraph) ==========
    messages: Annotated[List[Dict], add_messages]

    # ========== Health & Monitoring ==========
    health_status: Optional[Dict[str, Any]]
    performance_metrics: Optional[Dict[str, Any]]

    # ========== Weekly Insights Data ==========
    weekly_stats: Optional[Dict[str, Any]]
    skip_trends: Optional[List[Dict]]
    productivity_score: Optional[float]


class RoundsState(TypedDict):
    """State for Rounds Mode workflow"""
    session_id: str
    tasks: List[Dict[str, Any]]
    current_index: int
    decisions: List[Dict[str, Any]]
    start_time: str
    total_time_ms: int
    user_energy: str
    completed: bool


class InsightsState(TypedDict):
    """State for Weekly Insights workflow"""
    week_start: str
    week_end: str
    total_tasks: int
    completed_tasks: int
    skipped_tasks: int
    delegated_tasks: int
    skip_patterns: Dict[str, int]
    energy_distribution: Dict[str, int]
    productivity_by_day: Dict[str, float]
    top_blockers: List[str]
    recommendations: List[str]
    email_html: Optional[str]
    sent: bool
