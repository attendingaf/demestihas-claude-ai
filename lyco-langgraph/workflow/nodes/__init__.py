"""
Node implementations for Lyco LangGraph workflow.

Each node wraps existing v2 functionality for reuse.
"""

from .capture import (
    capture_email_signal,
    capture_calendar_signal,
    capture_terminal_input,
    capture_api_request,
    capture_webhook
)

from .parser import parse_with_llm

from .classifier import (
    determine_energy_level,
    apply_eisenhower_matrix
)

from .skip_handler import (
    detect_skip_patterns,
    process_skip_intelligence
)

from .router import (
    route_by_priority,
    process_rounds_mode
)

from .actions import (
    send_notification,
    block_calendar_time,
    assign_to_family,
    park_for_later,
    move_to_archive
)

from .learning import update_learning_model

from .storage import (
    update_redis_cache,
    persist_to_database,
    synchronize_with_notion
)

from .monitoring import (
    track_health_metrics,
    update_performance_stats
)

__all__ = [
    # Capture
    "capture_email_signal",
    "capture_calendar_signal",
    "capture_terminal_input",
    "capture_api_request",
    "capture_webhook",

    # Processing
    "parse_with_llm",
    "determine_energy_level",
    "apply_eisenhower_matrix",

    # Skip Intelligence
    "detect_skip_patterns",
    "process_skip_intelligence",

    # Routing
    "route_by_priority",
    "process_rounds_mode",

    # Actions
    "send_notification",
    "block_calendar_time",
    "assign_to_family",
    "park_for_later",
    "move_to_archive",

    # Learning
    "update_learning_model",

    # Storage
    "update_redis_cache",
    "persist_to_database",
    "synchronize_with_notion",

    # Monitoring
    "track_health_metrics",
    "update_performance_stats"
]
