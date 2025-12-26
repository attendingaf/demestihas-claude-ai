# Pluma Handler - Email Integration
## Why This Works: Smart Email Management

### HANDLER OVERVIEW
```yaml
PLUMA_INTEGRATION:
  purpose: "Intelligent email composition and management"
  philosophy: "Why This Works format for clarity"
  performance_target: "< 50ms response"
  cache_usage: "aggressive"
```

### TRIGGER PATTERNS
```yaml
EMAIL_TRIGGERS:
  high_confidence:
    - "send email to {recipient}"
    - "reply to {sender}"
    - "draft message about {topic}"
    - "forward {email} to {recipient}"
    - "check inbox"
    - "unread emails"
    
  medium_confidence:
    - "message {person}"
    - "write to {recipient}"
    - "respond to {sender}"
    - "email about {topic}"
    
  contextual:
    - "@" symbol with domain
    - "RE:" or "FW:" prefixes
    - email addresses detected
```

### WHY THIS WORKS
```markdown
## Email Intelligence Design

### The Problem
Emails require context, tone matching, and relationship awareness. Generic 
responses fail because they lack the nuance of human communication patterns.

### The Solution
Pluma integrates with:
1. **Smart Memory** - Learns email patterns per recipient
2. **Templates** - Cached responses by relationship type
3. **Family Context** - Knows who's who and their preferences

### The Magic
When you say "email Mom about Sunday dinner", Pluma:
- Recognizes "Mom" → Angela → warm, casual tone
- Checks calendar for Sunday availability
- Drafts in her preferred style
- Suggests sending time (she checks email at 10am)

This works because we're not just sending text - we're maintaining relationships.
```

### HANDLER IMPLEMENTATION
```yaml
PLUMA_HANDLER:
  initialization:
    - load_email_templates
    - connect_smtp_client
    - warm_recipient_cache
    - load_signature_blocks
    
  process_request:
    steps:
      1: parse_email_intent
      2: identify_recipient
      3: determine_tone
      4: generate_content
      5: add_signature
      6: queue_or_send
      
  cache_strategy:
    templates: "L1_cache"
    recipients: "L2_cache"
    drafts: "L3_cache"
    sent_items: "cold_storage"
```

### EMAIL TEMPLATES
```yaml
TEMPLATE_LIBRARY:
  professional:
    greeting: "Dear {name},"
    closing: "Best regards,"
    tone: "formal"
    
  casual:
    greeting: "Hi {name},"
    closing: "Thanks,"
    tone: "friendly"
    
  family:
    greeting: "Hey {name}!"
    closing: "Love,"
    tone: "warm"
    
  urgent:
    greeting: "{name},"
    closing: "Please advise ASAP."
    tone: "direct"
```

### RECIPIENT INTELLIGENCE
```yaml
RECIPIENT_PROFILES:
  learned_patterns:
    - preferred_greeting
    - typical_response_time
    - communication_style
    - topic_interests
    - scheduling_preferences
    
  relationship_mapping:
    family:
      - angela@example.com → wife → casual
      - mom@example.com → mother → warm
      
    professional:
      - client@company.com → client → formal
      - partner@firm.com → colleague → professional
      
    service:
      - support@service.com → vendor → direct
```

### SMART COMPOSITION
```yaml
COMPOSITION_ENGINE:
  analyze_request:
    - extract_recipient
    - determine_purpose
    - check_context
    - select_template
    
  enhance_content:
    - personalize_greeting
    - match_tone
    - add_context
    - suggest_attachments
    
  pre_send_checks:
    - verify_recipient
    - check_attachments
    - scan_sensitive_info
    - confirm_if_needed
```

### INTEGRATION WITH CACHE
```yaml
CACHE_INTEGRATION:
  aggressive_caching:
    email_templates:
      location: "L1"
      ttl: "permanent"
      size: "100KB"
      
    recipient_data:
      location: "L2"
      ttl: "1_day"
      size: "500KB"
      
    draft_storage:
      location: "L3"
      ttl: "1_hour"
      size: "2MB"
      
  performance_optimization:
    template_preload: true
    recipient_prefetch: true
    draft_autosave: "30_seconds"
```

### FALLBACK BEHAVIOR
```yaml
FALLBACK_STRATEGY:
  when_pluma_unavailable:
    action: "queue_for_later"
    notify: "Email queued for sending"
    retry: "5_minutes"
    
  when_recipient_unknown:
    action: "request_confirmation"
    suggest: "similar_recipients"
    learn: true
    
  when_network_error:
    action: "save_draft"
    retry: "exponential_backoff"
    max_retries: 3
```

### PERFORMANCE TARGETS
```yaml
PERFORMANCE:
  targets:
    parse_request: "< 5ms"
    template_selection: "< 3ms"
    content_generation: "< 20ms"
    pre_send_checks: "< 10ms"
    total_response: "< 50ms"
    
  optimization:
    - precompiled_templates
    - cached_recipients
    - async_sending
    - batch_operations
```

### MONITORING & LOGGING
```yaml
LOGGING:
  events:
    - email_sent
    - draft_saved
    - recipient_learned
    - template_used
    - error_occurred
    
  metrics:
    - emails_per_day
    - average_response_time
    - template_hit_rate
    - send_success_rate
    
  format: |
    timestamp|PLUMA|action|recipient|status|duration_ms
```

### API INTERFACE
```yaml
PLUMA_API:
  send_email:
    input:
      to: "recipient"
      subject: "subject"
      body: "content"
      tone: "casual|formal"
    output:
      status: "sent|queued|failed"
      message_id: "unique_id"
      
  save_draft:
    input:
      content: "draft_content"
      metadata: "draft_metadata"
    output:
      draft_id: "unique_id"
      saved_at: "timestamp"
      
  check_inbox:
    input:
      filter: "unread|all|sender"
    output:
      emails: []
      count: "number"
```# Handler references: agents/pluma/pluma.py
