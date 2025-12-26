"""
Claude prompts for Pluma agent
Optimized prompts for email drafting, tone analysis, and executive assistance
"""

# Email drafting prompts

EMAIL_TONE_ANALYSIS_PROMPT = """Analyze these email samples to identify the user's writing tone and style patterns:

{email_samples}

Provide a JSON response with:
{{
    "overall_tone": "professional|casual|friendly|direct|formal|conversational",
    "formality_level": 1-5,
    "common_phrases": ["frequently used phrases and expressions"],
    "greeting_style": "typical greeting approach",
    "closing_style": "typical closing approach", 
    "sentence_structure": "short|medium|long|mixed",
    "communication_style": "direct|diplomatic|detailed|concise",
    "key_characteristics": ["notable style elements"],
    "industry_language": ["domain-specific terms or jargon used"],
    "emotional_tone": "warm|neutral|business-focused|enthusiastic",
    "response_patterns": ["typical ways of addressing requests or questions"]
}}

Focus on actionable patterns that would help generate consistent, authentic email drafts that match the user's established communication style."""

EMAIL_DRAFT_GENERATION_PROMPT = """You are drafting a reply email that must match the user's established writing style and tone.

USER'S WRITING STYLE:
{tone_profile}

ORIGINAL EMAIL:
From: {sender}
Subject: {subject}
Body: {original_body}

CONTEXT:
- Reply should acknowledge the original message appropriately
- Address all questions or requests in the original email
- Match the established tone and formality level
- Use similar greeting/closing patterns
- Maintain the user's typical sentence structure and phrases

Generate a reply that feels authentic to the user's voice:

{{
    "subject": "Re: [appropriate subject]",
    "body": "[complete email body matching user's style]",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of approach taken",
    "tone_match": "how well this matches the user's style",
    "key_elements": ["specific style elements incorporated"]
}}

Priority: Authenticity over perfection. The email should sound like it came from the user, not a generic AI assistant."""

EMAIL_PRIORITY_CLASSIFICATION_PROMPT = """Analyze this email and classify its priority level and required action type:

EMAIL:
From: {sender}
Subject: {subject}
Body: {body}
Received: {timestamp}

Classify this email:

{{
    "priority": "urgent|high|medium|low",
    "action_required": "immediate_response|response_within_day|response_within_week|acknowledge_only|no_response|forward_to_someone",
    "category": "work_critical|meeting_scheduling|project_update|information_only|marketing|personal|administrative",
    "urgency_indicators": ["words or phrases that indicate urgency"],
    "deadline_mentioned": "specific deadline if any",
    "sender_importance": "high|medium|low based on sender context",
    "content_complexity": "simple|moderate|complex",
    "estimated_response_time": "time needed to craft appropriate response in minutes",
    "suggested_action": "specific recommended next step"
}}

Consider:
- Explicit urgency words (urgent, ASAP, deadline, etc.)
- Sender's role or relationship
- Request complexity
- Time sensitivity
- Required follow-up actions"""

EMAIL_AUTO_RESPONSE_PROMPT = """Generate an appropriate auto-response for this email based on the context and urgency:

EMAIL DETAILS:
From: {sender}
Subject: {subject}
Priority: {priority}
Category: {category}

USER CONTEXT:
- Currently: {current_status}
- Typical response time: {response_time_expectation}
- Communication style: {tone_style}

Generate an auto-response:

{{
    "should_send_auto_response": true|false,
    "response_type": "out_of_office|acknowledgment|redirect|delay_notification",
    "subject": "appropriate auto-response subject",
    "body": "brief, professional auto-response message",
    "delay_human_response": "suggested delay before human review in hours"
}}

Keep auto-responses brief, professional, and helpful. Only suggest auto-responses for appropriate situations."""

# Meeting analysis prompts

MEETING_COMPREHENSIVE_ANALYSIS_PROMPT = """Analyze this meeting transcript and provide a comprehensive structured summary:

TRANSCRIPT:
{transcript}

Provide detailed JSON analysis:

{{
    "meeting_metadata": {{
        "suggested_title": "descriptive meeting title based on content",
        "meeting_type": "standup|planning|review|decision|brainstorm|client_call|team_sync|other",
        "estimated_duration": "duration in minutes (integer)",
        "confidence_score": "0.0-1.0 confidence in analysis quality"
    }},
    "content_summary": {{
        "executive_summary": "2-3 sentence high-level summary",
        "key_topics": ["main discussion topics in order"],
        "primary_purpose": "what the meeting was intended to accomplish",
        "outcomes_achieved": ["concrete results or conclusions reached"]
    }},
    "participants": {{
        "identified_speakers": ["names of people who spoke"],
        "mentioned_individuals": ["people referenced but not speaking"],
        "roles_and_context": ["any titles or roles mentioned"]
    }},
    "decisions_and_actions": {{
        "key_decisions": ["concrete decisions made during meeting"],
        "action_items": [
            {{
                "task": "specific actionable item",
                "owner": "person responsible (if clearly stated)",
                "due_date": "deadline or timeframe (if mentioned)",
                "priority": "high|medium|low",
                "context": "why this action is needed"
            }}
        ],
        "follow_up_meetings": ["any scheduled follow-ups"],
        "escalations": ["items requiring management attention"]
    }},
    "content_analysis": {{
        "concerns_raised": ["problems or risks discussed"],
        "opportunities_identified": ["positive opportunities mentioned"],
        "blockers_or_issues": ["obstacles preventing progress"],
        "resource_needs": ["people, tools, or resources requested"],
        "timeline_discussions": ["important dates or deadlines mentioned"]
    }},
    "communication_insights": {{
        "engagement_level": "high|medium|low",
        "consensus_areas": ["topics where agreement was reached"],
        "disagreement_areas": ["topics with differing opinions"],
        "key_quotes": ["important statements or commitments (max 3)"],
        "tone_and_mood": "collaborative|tense|productive|rushed|thorough"
    }},
    "next_steps": {{
        "immediate_actions": ["what needs to happen right away"],
        "communication_needs": ["who needs to be informed about what"],
        "documentation_required": ["what should be documented or shared"],
        "success_metrics": ["how to measure if outcomes are achieved"]
    }}
}}

Guidelines:
- Be specific and actionable in your analysis
- Only include information that's clearly stated or strongly implied
- If transcript quality is poor, note this in confidence_score
- Focus on business-relevant insights and actionable outcomes
- Extract exact quotes only for truly important statements"""

MEETING_FOLLOW_UP_EMAIL_PROMPT = """Based on these comprehensive meeting notes, generate follow-up email drafts for different stakeholder groups:

MEETING: {title}
DATE: {date}
SUMMARY: {summary}
KEY DECISIONS: {decisions}
ACTION ITEMS: {action_items}
PARTICIPANTS: {participants}

Create targeted follow-up communications:

[
    {{
        "audience": "all_participants|action_item_owners|management|absent_stakeholders",
        "subject": "clear, specific subject line",
        "body": "complete email body with appropriate tone and detail level",
        "priority": "high|medium|low",
        "send_timing": "immediate|end_of_day|next_morning|before_deadline",
        "purpose": "summary|action_items|decisions|status_update",
        "includes": ["action_items", "decisions", "next_steps", "resources"]
    }}
]

Email requirements:
- Professional but warm tone matching user's style
- Clear action items with owners and deadlines
- Reference specific meeting outcomes
- Include context for people who weren't present
- Provide clear next steps
- End with helpful contact information or resources

Generate 1-3 targeted emails based on the meeting content and stakeholder needs."""

MEETING_ACTION_ITEM_EXTRACTION_PROMPT = """Extract and structure action items from this meeting content:

CONTENT: {content}

Create structured action items:

{{
    "action_items": [
        {{
            "id": "unique identifier",
            "task": "clear, specific task description",
            "owner": "responsible person (if mentioned)",
            "due_date": "deadline (if specified)",
            "priority": "high|medium|low",
            "category": "follow_up|deliverable|decision|communication|research",
            "context": "why this task is needed",
            "success_criteria": "how to know when it's done",
            "dependencies": ["what must happen first"],
            "estimated_effort": "quick|medium|substantial",
            "status": "not_started"
        }}
    ],
    "unassigned_tasks": ["tasks without clear owners"],
    "unclear_items": ["items that need clarification"],
    "deadline_conflicts": ["overlapping or unrealistic deadlines"]
}}

Focus on:
- Actionable, specific tasks
- Clear ownership when mentioned
- Realistic deadlines and priorities
- Dependencies between tasks
- Items needing clarification"""

# Executive assistance prompts

CONTEXT_ANALYSIS_PROMPT = """Analyze the context and intent of this executive request:

REQUEST: {request}
USER PROFILE: {user_profile}
CURRENT CONTEXT: {current_context}

Analyze and respond:

{{
    "request_type": "email_draft|calendar|task_management|information_research|decision_support|meeting_prep",
    "urgency_level": "immediate|today|this_week|flexible",
    "complexity": "simple|moderate|complex|multi_step",
    "required_information": ["additional info needed to fulfill request"],
    "suggested_approach": "recommended way to handle this request", 
    "estimated_time": "time needed to complete in minutes",
    "potential_issues": ["obstacles or complications to consider"],
    "success_criteria": "how to measure successful completion",
    "follow_up_needed": true|false
}}

Consider the executive's typical preferences, time constraints, and communication style."""

SMART_SUGGESTION_PROMPT = """Based on the user's patterns and current context, suggest proactive assistance:

USER PATTERNS: {user_patterns}
RECENT ACTIVITY: {recent_activity}
CALENDAR CONTEXT: {calendar_context}
EMAIL TRENDS: {email_trends}

Generate helpful suggestions:

{{
    "proactive_suggestions": [
        {{
            "type": "email_draft|calendar_block|task_reminder|meeting_prep|follow_up",
            "suggestion": "specific suggestion",
            "reasoning": "why this would be helpful now",
            "effort_required": "minimal|moderate|significant",
            "potential_impact": "high|medium|low",
            "timing": "now|today|this_week"
        }}
    ],
    "pattern_insights": ["observations about user's work patterns"],
    "efficiency_opportunities": ["ways to save time or improve workflow"],
    "upcoming_needs": ["anticipated future assistance needs"]
}}

Focus on suggestions that save time, reduce cognitive load, and align with the executive's priorities."""

# Prompt templates for different contexts

def get_email_draft_prompt(sender: str, subject: str, body: str, tone_profile: dict) -> str:
    """Get formatted email draft prompt"""
    return EMAIL_DRAFT_GENERATION_PROMPT.format(
        tone_profile=format_tone_profile(tone_profile),
        sender=sender,
        subject=subject,
        original_body=body[:1500] + ("..." if len(body) > 1500 else "")
    )

def get_meeting_analysis_prompt(transcript: str) -> str:
    """Get formatted meeting analysis prompt"""
    return MEETING_COMPREHENSIVE_ANALYSIS_PROMPT.format(
        transcript=transcript[:8000] + ("..." if len(transcript) > 8000 else "")
    )

def get_priority_classification_prompt(sender: str, subject: str, body: str, timestamp: str) -> str:
    """Get formatted priority classification prompt"""
    return EMAIL_PRIORITY_CLASSIFICATION_PROMPT.format(
        sender=sender,
        subject=subject,
        body=body[:1000] + ("..." if len(body) > 1000 else ""),
        timestamp=timestamp
    )

def format_tone_profile(tone_profile: dict) -> str:
    """Format tone profile for prompt inclusion"""
    if not tone_profile:
        return "Professional, concise communication style"
    
    return f"""
- Overall tone: {tone_profile.get('overall_tone', 'professional')}
- Formality level: {tone_profile.get('formality_level', 3)}/5
- Typical greeting: {tone_profile.get('greeting_style', 'Hi')}
- Typical closing: {tone_profile.get('closing_style', 'Best regards')}
- Communication style: {tone_profile.get('communication_style', 'direct')}
- Key characteristics: {', '.join(tone_profile.get('key_characteristics', []))}
- Common phrases: {', '.join(tone_profile.get('common_phrases', [])[:3])}
    """.strip()

# Utility functions for prompt customization

def truncate_content(content: str, max_length: int = 2000) -> str:
    """Safely truncate content for prompts"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "\n\n[Content truncated for analysis...]"

def format_email_for_prompt(email_data: dict) -> str:
    """Format email data for prompt inclusion"""
    return f"""
From: {email_data.get('sender', 'Unknown')}
Subject: {email_data.get('subject', 'No Subject')}
Date: {email_data.get('timestamp', 'Unknown')}

{truncate_content(email_data.get('body', ''), 1500)}
    """.strip()

def create_custom_prompt(template: str, **kwargs) -> str:
    """Create custom prompt with variable substitution"""
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required prompt variable: {e}")

# Prompt validation helpers

def validate_prompt_length(prompt: str, max_tokens: int = 4000) -> bool:
    """Validate prompt length (rough token estimation)"""
    # Rough estimation: 4 chars per token on average
    estimated_tokens = len(prompt) // 4
    return estimated_tokens <= max_tokens

def optimize_prompt_for_model(prompt: str, model: str = "claude-3-sonnet") -> str:
    """Optimize prompt based on target model capabilities"""
    if "haiku" in model.lower():
        # Haiku works best with shorter, more focused prompts
        return truncate_content(prompt, 3000)
    elif "opus" in model.lower():
        # Opus can handle longer, more detailed prompts
        return prompt
    else:
        # Sonnet - balanced approach
        return truncate_content(prompt, 6000)

# Context-aware prompt builders

class PromptBuilder:
    """Builder class for creating context-aware prompts"""
    
    def __init__(self, user_profile: dict = None):
        self.user_profile = user_profile or {}
    
    def build_email_prompt(self, email_data: dict, task: str = "draft_reply") -> str:
        """Build email-specific prompt"""
        base_prompts = {
            "draft_reply": EMAIL_DRAFT_GENERATION_PROMPT,
            "classify_priority": EMAIL_PRIORITY_CLASSIFICATION_PROMPT,
            "auto_response": EMAIL_AUTO_RESPONSE_PROMPT
        }
        
        template = base_prompts.get(task, EMAIL_DRAFT_GENERATION_PROMPT)
        return self._customize_prompt(template, email_data)
    
    def build_meeting_prompt(self, meeting_data: dict, task: str = "comprehensive_analysis") -> str:
        """Build meeting-specific prompt"""
        if task == "comprehensive_analysis":
            return get_meeting_analysis_prompt(meeting_data.get('transcript', ''))
        elif task == "action_items":
            return MEETING_ACTION_ITEM_EXTRACTION_PROMPT.format(
                content=meeting_data.get('transcript', '')
            )
        elif task == "follow_up_emails":
            return MEETING_FOLLOW_UP_EMAIL_PROMPT.format(**meeting_data)
        
        return get_meeting_analysis_prompt(meeting_data.get('transcript', ''))
    
    def _customize_prompt(self, template: str, data: dict) -> str:
        """Customize prompt with user profile and data"""
        customized_data = {**data}
        
        # Add user profile context if available
        if self.user_profile:
            customized_data['tone_profile'] = format_tone_profile(self.user_profile.get('tone_profile', {}))
            customized_data['user_profile'] = self.user_profile
        
        return create_custom_prompt(template, **customized_data)
