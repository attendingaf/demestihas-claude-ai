# Tool Routing Matrix
## Mandatory Tool-Specific Routing Configuration

### TOOL REGISTRY
```yaml
AVAILABLE_TOOLS:
  pluma:
    name: "Pluma - Email Manager"
    capability: "email_communication"
    priority: "MANDATORY"
    patterns:
      - "email"
      - "send message"
      - "draft"
      - "reply"
      - "forward"
      - "inbox"
      - "unread"
    cache_strategy: "aggressive"
    
  huata:
    name: "Huata - Calendar System"
    capability: "calendar_scheduling"
    priority: "MANDATORY"
    patterns:
      - "calendar"
      - "schedule"
      - "meeting"
      - "appointment"
      - "event"
      - "when is"
      - "book time"
      - "check availability"
      - "conflict"
    cache_strategy: "real_time"
    
  lyco:
    name: "Lyco - Task & Time Manager"
    capability: "task_project_time_management"
    priority: "MANDATORY"
    patterns:
      # Task management
      - "task"
      - "todo"
      - "project"
      - "milestone"
      - "deadline"
      - "assign"
      - "complete"
      - "priority"
      - "workflow"
      # Time management (moved from Kairos)
      - "optimize time"
      - "time block"
      - "focus time"
      - "ADHD"
      - "productivity"
      - "distraction"
      - "break time"
      - "pomodoro"
      - "energy level"
      - "hyperfocus"
      - "executive dysfunction"
    cache_strategy: "moderate"
    
  kairos:
    name: "Kairos - Networking Agent"
    capability: "networking_relationship_management"
    priority: "MANDATORY"
    patterns:
      - "contact"
      - "networking"
      - "LinkedIn"
      - "relationship"
      - "follow up"
      - "introduction"
      - "connection"
      - "meeting prep"
      - "CRM"
      - "professional network"
      - "last talked"
      - "relationship score"
    cache_strategy: "relationship_optimized"
    
  smart_memory:
    name: "Smart Memory - Context Engine"
    capability: "pattern_learning"
    priority: "ALWAYS_ACTIVE"
    patterns:
      - "*" # Monitors all patterns
    cache_strategy: "persistent"
```

### ROUTING DECISION TREE
```yaml
ROUTING_PRIORITY:
  level_1_mandatory:  # Check first, no fallback
    - condition: "has_tool('pluma') AND matches_email_pattern"
      action: "ROUTE_TO_PLUMA"
      fallback: "NONE"
      log: "TOOL|PLUMA|email_request"
      
    - condition: "has_tool('huata') AND matches_calendar_pattern"
      action: "ROUTE_TO_HUATA"
      fallback: "NONE"
      log: "TOOL|HUATA|calendar_request"
      
    - condition: "has_tool('lyco') AND (matches_task_pattern OR matches_time_pattern)"
      action: "ROUTE_TO_LYCO"
      fallback: "NONE"
      log: "TOOL|LYCO|task_time_request"
      
    - condition: "has_tool('kairos') AND matches_networking_pattern"
      action: "ROUTE_TO_KAIROS"
      fallback: "NONE"
      log: "TOOL|KAIROS|networking_request"
      
  level_2_contextual:  # Smart Memory always active
    - condition: "pattern_recognized"
      action: "ENHANCE_WITH_MEMORY"
      parallel: true
      log: "MEMORY|PATTERN|recognized"
      
  level_3_generic:  # Only if no tool match
    - condition: "no_tool_match"
      action: "USE_GENERIC_ROUTING"
      optimize: true
      log: "ROUTING|GENERIC|no_tool_match"
```

### PATTERN MATCHING RULES
```yaml
PATTERN_DETECTION:
  email_patterns:
    strong_signals:
      - regex: "\\b(email|message|send|draft|reply)\\b"
      - regex: "\\b(inbox|unread|forward|attachment)\\b"
      - regex: "@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    confidence_required: 0.7
    
  calendar_patterns:
    strong_signals:
      - regex: "\\b(calendar|schedule|meeting|appointment)\\b"
      - regex: "\\b(book|available|conflict|reschedule)\\b"
      - regex: "\\b(Monday|Tuesday|Wednesday|Thursday|Friday)\\b"
      - regex: "\\b(tomorrow|next week|today)\\b"
      - time_expression: "HH:MM|H:MM|Ham|Hpm"
    confidence_required: 0.8
    
  task_patterns:
    strong_signals:
      - regex: "\\b(task|todo|project|milestone)\\b"
      - regex: "\\b(complete|assign|priority|deadline)\\b"
      - regex: "\\b(workflow|sprint|backlog)\\b"
    confidence_required: 0.75
    
  time_patterns:
    strong_signals:
      - regex: "\\b(optimize|focus|productivity|ADHD)\\b"
      - regex: "\\b(time block|pomodoro|break|energy)\\b"
      - regex: "\\b(distraction|concentrate|efficient)\\b"
    confidence_required: 0.7
```

### TOOL INTEGRATION HOOKS
```yaml
INTEGRATION_POINTS:
  pre_routing:
    - check_tool_availability
    - load_tool_preferences
    - warm_tool_cache
    
  routing_decision:
    - pattern_matching
    - confidence_scoring
    - tool_selection
    - log_decision
    
  post_routing:
    - execute_tool_handler
    - cache_result
    - learn_pattern
    - update_metrics
```

### PERFORMANCE REQUIREMENTS
```yaml
PERFORMANCE_TARGETS:
  tool_detection: "< 5ms"
  pattern_matching: "< 10ms"
  routing_decision: "< 15ms"
  total_overhead: "< 30ms"
  
  cache_requirements:
    tool_availability: "always_cached"
    pattern_cache: "L1_priority"
    decision_cache: "L2_storage"
```

### CONFLICT RESOLUTION
```yaml
CONFLICT_HANDLING:
  multiple_tools_match:
    strategy: "highest_confidence"
    tiebreaker: "user_preference"
    log: "CONFLICT|RESOLVED|tool_selected"
    
  no_tool_available:
    strategy: "graceful_degradation"
    action: "use_generic_with_warning"
    log: "WARNING|NO_TOOL|degraded_mode"
    
  tool_timeout:
    threshold: "100ms"
    action: "circuit_break"
    fallback: "generic_routing"
    log: "ERROR|TIMEOUT|circuit_opened"
```

### MANDATORY ROUTING ENFORCEMENT
```yaml
ENFORCEMENT:
  strict_mode: true
  
  rules:
    - "Email requests MUST route to Pluma if available"
    - "Calendar requests MUST route to Huata if available"
    - "Task requests MUST route to Lyco if available"
    - "Time optimization MUST route to Kairos if available"
    - "NO fallback to generic for tool-capable requests"
    
  violations:
    action: "log_error"
    alert: "monitoring_dashboard"
    metric: "routing_violation_count"
```

### TOOL-SPECIFIC CACHING
```yaml
CACHE_STRATEGIES:
  pluma:
    cache_drafts: true
    cache_templates: true
    ttl: "1_hour"
    
  huata:
    cache_availability: false  # Real-time required
    cache_conflicts: true
    ttl: "5_minutes"
    
  lyco:
    cache_projects: true
    cache_workflows: true
    ttl: "30_minutes"
    
  kairos:
    cache_patterns: true
    cache_suggestions: true
    ttl: "1_day"
```

### MONITORING & METRICS
```yaml
TOOL_METRICS:
  track:
    - tool_routing_accuracy
    - pattern_match_confidence
    - tool_response_time
    - cache_hit_rate_per_tool
    - fallback_frequency
    
  alerts:
    - tool_unavailable
    - routing_violation
    - performance_degradation
    - high_fallback_rate
```

### API INTERFACE
```yaml
TOOL_ROUTING_API:
  route_request:
    input: "user_request"
    output:
      tool: "selected_tool"
      confidence: "0.0-1.0"
      reasoning: "pattern_matched"
      cache_hit: "boolean"
    
  get_tool_status:
    input: "tool_name"
    output:
      available: "boolean"
      response_time: "ms"
      cache_status: "hot|warm|cold"
      
  force_tool_route:
    input: 
      request: "user_request"
      tool: "tool_name"
    output: "tool_response"
    override: true
```