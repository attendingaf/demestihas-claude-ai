import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from anthropic import AsyncAnthropic
import os

logger = logging.getLogger(__name__)

# Initialize Anthropic client
anthropic_client = AsyncAnthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

async def parse_email_to_tasks(email_data: Dict) -> List[Dict]:
    """Parse email content and extract actionable tasks using AI"""
    try:
        # Extract email components
        sender = email_data.get('sender', '')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        timestamp = email_data.get('timestamp', '')
        
        logger.info(f"🧠 Parsing email from {sender}: {subject[:50]}")
        
        # Quick pre-filter - skip if no actionable content
        if not contains_actionable_content(subject + ' ' + body):
            logger.info(f"📭 No actionable content found in email")
            return []
        
        # Build AI prompt for task extraction
        prompt = build_task_extraction_prompt(sender, subject, body)
        
        # Use Anthropic for intelligent parsing
        response = await anthropic_client.messages.create(
            model="claude-3-haiku-20240307",  # Fast and cost-effective for parsing
            max_tokens=1000,
            temperature=0,  # Deterministic for task extraction
            system="You are an expert email parser that extracts actionable tasks from emails. Always respond with valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse AI response
        response_text = response.content[0].text.strip()
        
        # Extract JSON from response (handle potential markdown formatting)
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            tasks_json = json_match.group(0)
        else:
            tasks_json = response_text
        
        tasks = json.loads(tasks_json)
        
        # Post-process and validate tasks
        processed_tasks = []
        for task in tasks:
            processed_task = post_process_task(task, email_data)
            if processed_task:
                processed_tasks.append(processed_task)
        
        logger.info(f"✨ Extracted {len(processed_tasks)} tasks from email")
        return processed_tasks
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        # Fallback: create single task with full email content
        return [create_fallback_task(email_data)]
        
    except Exception as e:
        logger.error(f"Email parsing error: {e}")
        # Fallback: create single task with full email content  
        return [create_fallback_task(email_data)]

def contains_actionable_content(text: str) -> bool:
    """Quick check if email contains actionable content"""
    actionable_keywords = [
        # Direct actions
        'please', 'could you', 'can you', 'would you', 'need to', 'should',
        'review', 'check', 'update', 'schedule', 'call', 'meeting', 'deadline',
        'by', 'before', 'until', 'asap', 'urgent', 'priority',
        # Project terms
        'task', 'action', 'todo', 'follow up', 'follow-up', 'complete',
        'finish', 'deliver', 'send', 'prepare', 'draft', 'create'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in actionable_keywords)

def build_task_extraction_prompt(sender: str, subject: str, body: str) -> str:
    """Build optimized prompt for task extraction"""
    
    return f"""Extract actionable tasks from this email. Focus on specific actions that need to be taken.

EMAIL DETAILS:
From: {sender}
Subject: {subject}
Body: {body[:2000]}  # Limit to avoid token overuse

TASK EXTRACTION RULES:
1. Only extract tasks that require specific action from the recipient
2. Ignore pleasantries, FYI information, or completed actions
3. For each task, identify:
   - title: Brief action description (2-5 words)
   - description: Full context from email
   - due_date: Extract from phrases like "by Friday", "next week", "ASAP" (use YYYY-MM-DD format or null)
   - priority: High (urgent/ASAP), Medium (has deadline), Low (no deadline)
   - category: infer from content (Meeting, Review, Project, Admin, etc.)

EXAMPLES:
"Please review the Q3 report by Friday" → {{"title": "Review Q3 report", "due_date": "2025-09-06", "priority": "High"}}
"Can we schedule a call about X?" → {{"title": "Schedule call about X", "due_date": null, "priority": "Medium"}}
"FYI - meeting moved to Tuesday" → No task (FYI only)

Return ONLY a JSON array of tasks. If no actionable tasks exist, return [].

"""

def post_process_task(task: Dict, email_data: Dict) -> Optional[Dict]:
    """Post-process and validate extracted task"""
    try:
        # Required fields
        if not task.get('title'):
            return None
        
        # Clean and format task
        processed = {
            'title': task.get('title', '').strip()[:100],  # Notion title limit
            'description': build_task_description(task, email_data),
            'due_date': parse_due_date(task.get('due_date')),
            'priority': normalize_priority(task.get('priority', 'Medium')),
            'category': task.get('category', 'Email Task').strip()[:50],
            'source': 'email',
            'created_at': datetime.now().isoformat()
        }
        
        return processed
        
    except Exception as e:
        logger.error(f"Task post-processing error: {e}")
        return None

def build_task_description(task: Dict, email_data: Dict) -> str:
    """Build comprehensive task description with email context"""
    description_parts = []
    
    # Add AI-extracted description
    if task.get('description'):
        description_parts.append(task['description'])
    
    # Add email context
    description_parts.append(f"\n**Email Context:**")
    description_parts.append(f"From: {email_data.get('sender', 'Unknown')}")
    description_parts.append(f"Subject: {email_data.get('subject', 'No Subject')}")
    description_parts.append(f"Received: {email_data.get('timestamp', 'Unknown')}")
    
    # Add original content snippet if helpful
    body = email_data.get('body', '')
    if body and len(body) > 50:
        preview = body[:200].strip() + ('...' if len(body) > 200 else '')
        description_parts.append(f"\n**Original Message:**\n{preview}")
    
    return '\n'.join(description_parts)

def parse_due_date(due_date_str: Optional[str]) -> Optional[str]:
    """Parse and normalize due date string"""
    if not due_date_str or due_date_str == 'null':
        return None
    
    try:
        # If already in YYYY-MM-DD format
        if re.match(r'\d{4}-\d{2}-\d{2}', due_date_str):
            return due_date_str
        
        # Handle relative dates
        today = datetime.now().date()
        
        if 'today' in due_date_str.lower():
            return today.strftime('%Y-%m-%d')
        elif 'tomorrow' in due_date_str.lower():
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'friday' in due_date_str.lower():
            # Find next Friday
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7  # Next Friday if today is Friday
            friday_date = today + timedelta(days=days_until_friday)
            return friday_date.strftime('%Y-%m-%d')
        elif 'next week' in due_date_str.lower():
            return (today + timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'end of week' in due_date_str.lower():
            days_until_friday = (4 - today.weekday()) % 7
            friday_date = today + timedelta(days=days_until_friday)
            return friday_date.strftime('%Y-%m-%d')
        else:
            # Return as-is for manual review
            return due_date_str
            
    except Exception as e:
        logger.warning(f"Due date parsing error: {e}")
        return None

def normalize_priority(priority_str: str) -> str:
    """Normalize priority to standard values"""
    priority_lower = priority_str.lower()
    
    if any(word in priority_lower for word in ['high', 'urgent', 'asap', 'critical']):
        return 'High'
    elif any(word in priority_lower for word in ['low', 'someday', 'whenever']):
        return 'Low'
    else:
        return 'Medium'

def create_fallback_task(email_data: Dict) -> Dict:
    """Create fallback task when AI parsing fails"""
    return {
        'title': f"Review Email: {email_data.get('subject', 'No Subject')[:50]}",
        'description': f"""**AI parsing failed - manual review needed**

From: {email_data.get('sender', 'Unknown')}
Subject: {email_data.get('subject', 'No Subject')}
Received: {email_data.get('timestamp', 'Unknown')}

**Original Message:**
{email_data.get('body', 'No content')[:500]}
""",
        'due_date': None,
        'priority': 'Medium',
        'category': 'Email Review',
        'source': 'email_fallback',
        'created_at': datetime.now().isoformat()
    }

# Test function for development
async def test_email_parsing():
    """Test function for email parsing"""
    test_email = {
        'sender': 'test@example.com',
        'subject': 'Review Q3 report',
        'body': 'Hi, please review the attached Q3 report by Friday. Let me know if you have questions.',
        'timestamp': datetime.now().isoformat()
    }
    
    tasks = await parse_email_to_tasks(test_email)
    print(f"Extracted tasks: {json.dumps(tasks, indent=2)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_email_parsing())
