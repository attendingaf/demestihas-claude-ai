def contains_calendar_intent(self, message):
    """
    Improved calendar intent detection - fixes routing issues
    
    QA CORRECTED: Added missing singular keywords (appointment, meeting, event)
    Expanded from ~11 keywords to 40+ patterns to catch:
    - "what on my calendar" variants
    - Day-of-week references with calendar context  
    - Time-based availability queries
    - Direct calendar references
    """
    message_lower = message.lower()
    
    # Expanded keyword list - comprehensive coverage
    calendar_keywords = [
        # Availability queries
        'free', 'available', 'busy', 'schedule',
        
        # Direct calendar references - CRITICAL MISSING PATTERNS
        'calendar', 'my calendar', 'on my calendar',
        'what on my calendar', 'whats on my calendar',
        'show my calendar', 'check my calendar',
        'on calendar', 'calendar today', 'calendar tomorrow',
        
        # Event/meeting references - QA FIX: Added singular forms
        'event', 'events', 'meeting', 'meetings', 'appointment', 'appointments',
        'events today', 'events tomorrow', 'events this week',
        'meetings today', 'meetings tomorrow', 'my meetings',
        'appointments today', 'appointments tomorrow', 'my appointments',
        
        # Time references with calendar context
        'today', 'tomorrow', 'this week', 'next week',
        'monday', 'tuesday', 'wednesday', 'thursday', 
        'friday', 'saturday', 'sunday',
        'this afternoon', 'this morning', 'this evening',
        'tomorrow morning', 'tomorrow afternoon', 'tomorrow evening',
        
        # Action queries - availability focused
        'when am i', 'what time', 'do i have', 'have i got',
        'am i free', 'am i busy', 'am i available',
        'can i', 'could i', 'would i be free',
        
        # Meeting scheduling context
        'find time', 'schedule meeting', 'book time',
        'open slots', 'free slots', 'available times'
    ]
    
    # Check for any keyword match
    for keyword in calendar_keywords:
        if keyword in message_lower:
            # Additional context check - avoid false positives for task creation
            task_indicators = [
                'create task', 'add task', 'make task', 'new task',
                'remind me', 'todo', 'to do', 'task for',
                'buy', 'get', 'pick up', 'call', 'email'  # Common task actions
            ]
            
            # Only exclude if it's clearly a task creation request
            if any(task_ind in message_lower for task_ind in task_indicators):
                # Special case: calendar-related tasks should still route to calendar
                calendar_task_indicators = [
                    'schedule', 'meeting', 'appointment', 'calendar'
                ]
                if any(cal_task in message_lower for cal_task in calendar_task_indicators):
                    return True
                return False
            
            return True
    
    return False