import json
import logging
from typing import Dict, List, Optional
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re

load_dotenv()
logger = logging.getLogger(__name__)

class EnhancedTaskParser:
    """Enhanced AI task parser with family context and ADHD optimizations"""
    
    def __init__(self, anthropic_api_key=None):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-3-haiku-20240307"
        
        # Enhanced system prompt with family awareness
        self.system_prompt = """You are an ADHD-optimized task extraction system for a physician executive's family.

FAMILY CONTEXT:
- Mene: Project owner, ER physician executive, ADHD hyperactive type
- Cindy: Wife, ER physician, ADHD inattentive type, native Spanish speaker
- Persy: 11yo, 6th grade at Sutton, loves reading and weather
- Stelios: 8yo, 4th grade at E. Rivers, soccer enthusiast, Arsenal fan
- Franci: 5yo, kindergarten at E. Rivers, loves singing and dancing
- Viola: Au pair from Germany

EISENHOWER MATRIX RULES:
1. DO_NOW (Urgent + Important): Deadlines <24hrs, health/safety, "urgent", "ASAP", "emergency", medical appointments
2. SCHEDULE (Important + Not Urgent): Goals, planning, "important", "this week", health routines, work projects
3. DELEGATE (Urgent + Not Important): "ask [person]", "have [person]", routine admin, kid transportation
4. SOMEDAY (Neither): "maybe", "someday", "eventually", wishlist items, non-urgent learning

CONTEXT DETECTION PATTERNS:
- Shopping/groceries/store → ["Shopping", "Errand"]
- Doctor/dentist/vet/appointment → ["Appointment", "Call"]
- Kids/school/activities → ["Family"]
- Work/meeting/report → ["Work", "Deep Work"]
- Bills/paperwork/forms → ["Admin"]
- Exercise/gym/physical → ["Physical"]
- Home repair/cleaning → ["Household"]
- Research/learning → ["Research"]

FAMILY ASSIGNMENT LOGIC:
- Default: mene (task creator)
- "wife"/"Cindy"/"mom" → cindy
- "au pair"/"Viola"/"nanny" → viola
- "oldest"/"Persy" → persy
- "middle"/"Stelios" → stelios
- "youngest"/"Franci" → franci
- Transportation for kids → typically viola (delegate)
- Spanish-related tasks → cindy
- Soccer-related → stelios (but transportation to viola)

OUTPUT REQUIREMENTS:
Return ONLY valid JSON in this exact structure:
{
  "tasks": [
    {
      "name": "Clear, action-oriented task name starting with verb",
      "eisenhower": "DO_NOW|SCHEDULE|DELEGATE|SOMEDAY",
      "context": ["tag1", "tag2"],
      "energy": "Low|Medium|High",
      "time_estimate": "Quick|Short|Deep|Multi_hour",
      "assigned_to": "mene|cindy|viola|persy|stelios|franci",
      "due_date": "YYYY-MM-DD or null",
      "confidence": 0.0-1.0
    }
  ],
  "reasoning": "Brief explanation of categorization decisions"
}"""
    
    async def extract_tasks(self, message: str, user_context: Dict = None) -> Dict:
        """Extract and categorize tasks with family awareness and ADHD optimization"""
        try:
            # Build context-aware prompt
            user_prompt = self._build_user_prompt(message, user_context)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,  # Increased for detailed responses
                temperature=0.2,  # Lower for consistency in categorization
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse JSON response with error handling
            response_text = response.content[0].text.strip()
            
            # Clean up response if needed (remove markdown code blocks)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(response_text)
            
            # Validate and enhance result
            result = self._validate_and_enhance_tasks(result)
            
            # Log for monitoring
            avg_confidence = self._calculate_avg_confidence(result)
            logger.info(f"Extracted {len(result['tasks'])} tasks with avg confidence {avg_confidence:.2f}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}, Response: {response_text[:200]}")
            return self._fallback_extraction(message)
        except Exception as e:
            logger.error(f"Task extraction failed: {e}")
            return self._fallback_extraction(message)
    
    def _build_user_prompt(self, message: str, context: Dict = None) -> str:
        """Build context-aware prompt with time and user information"""
        prompt = f"Extract tasks from this message: \"{message}\"\n\n"
        
        # Add temporal context
        current_time = datetime.now()
        prompt += f"Current date/time: {current_time.strftime('%Y-%m-%d %H:%M')} (Monday)\n"
        prompt += f"Time of day context: {'Morning' if current_time.hour < 12 else 'Afternoon' if current_time.hour < 18 else 'Evening'}\n"
        
        # Add user context if available
        if context:
            if context.get('user_name'):
                prompt += f"Message from: {context['user_name']}\n"
            if context.get('recent_tasks'):
                prompt += f"Recent tasks for pattern recognition: {', '.join(context['recent_tasks'][:3])}\n"
            if context.get('family_context'):
                prompt += f"Family context: {context['family_context']}\n"
        
        prompt += "\nReturn JSON only, no additional text."
        return prompt
    
    def _validate_and_enhance_tasks(self, result: Dict) -> Dict:
        """Validate parsed result and apply family-specific rules"""
        if not isinstance(result, dict) or 'tasks' not in result:
            logger.warning("Invalid result structure, applying fallback")
            return self._fallback_extraction("Invalid parsing result")
        
        enhanced_tasks = []
        
        for task in result.get('tasks', []):
            # Ensure all required fields with smart defaults
            task = self._ensure_required_fields(task)
            
            # Apply family-specific business rules
            task = self._apply_family_rules(task)
            
            # Apply ADHD-specific optimizations
            task = self._apply_adhd_optimizations(task)
            
            enhanced_tasks.append(task)
        
        result['tasks'] = enhanced_tasks
        
        # Ensure reasoning field
        if 'reasoning' not in result:
            result['reasoning'] = "Enhanced with family context and ADHD optimizations"
        
        return result
    
    def _ensure_required_fields(self, task: Dict) -> Dict:
        """Ensure all required fields are present with sensible defaults"""
        defaults = {
            'name': 'Untitled task',
            'eisenhower': 'SCHEDULE',
            'context': [],
            'energy': 'Medium',
            'time_estimate': 'Short',
            'assigned_to': 'mene',
            'due_date': None,
            'confidence': 0.7
        }
        
        for field, default_value in defaults.items():
            if field not in task or not task[field]:
                task[field] = default_value
        
        # Ensure context is a list
        if isinstance(task['context'], str):
            task['context'] = [task['context']]
        
        return task
    
    def _apply_family_rules(self, task: Dict) -> Dict:
        """Apply family-specific business logic and overrides"""
        name_lower = task['name'].lower()
        
        # Urgency keyword overrides
        urgent_keywords = ['urgent', 'asap', 'emergency', 'now', 'immediately']
        if any(keyword in name_lower for keyword in urgent_keywords):
            task['eisenhower'] = 'DO_NOW'
            task['confidence'] = min(0.95, task['confidence'] + 0.2)
        
        # Family member detection and smart assignment
        family_mappings = {
            'viola': 'viola', 'au pair': 'viola', 'nanny': 'viola',
            'cindy': 'cindy', 'wife': 'cindy', 'mom': 'cindy',
            'persy': 'persy', 'oldest': 'persy',
            'stelios': 'stelios', 'middle': 'stelios', 'soccer': 'stelios',
            'franci': 'franci', 'youngest': 'franci', 'baby': 'franci'
        }
        
        for keyword, assignee in family_mappings.items():
            if keyword in name_lower:
                if keyword in ['viola', 'au pair'] or 'ask' in name_lower or 'have' in name_lower:
                    task['eisenhower'] = 'DELEGATE'
                    task['assigned_to'] = assignee
                elif assignee in ['cindy', 'persy', 'stelios', 'franci']:
                    task['assigned_to'] = assignee
                break
        
        # Kid transportation logic
        transport_keywords = ['pick up', 'drop off', 'take to', 'bring to']
        kid_names = ['persy', 'stelios', 'franci']
        
        if (any(transport in name_lower for transport in transport_keywords) and 
            any(kid in name_lower for kid in kid_names)):
            task['eisenhower'] = 'DELEGATE'
            task['assigned_to'] = 'viola'
            task['context'].append('Family')
        
        # Spanish language tasks
        if 'spanish' in name_lower or 'español' in name_lower:
            task['assigned_to'] = 'cindy'
            if task['eisenhower'] not in ['DO_NOW']:
                task['eisenhower'] = 'DELEGATE'
        
        return task
    
    def _apply_adhd_optimizations(self, task: Dict) -> Dict:
        """Apply ADHD-specific task optimizations"""
        name_lower = task['name'].lower()
        
        # Break down large tasks (ADHD optimization)
        if len(task['name']) > 80:
            task['name'] = task['name'][:77] + "..."
            task['confidence'] = max(0.3, task['confidence'] - 0.2)
        
        # Ensure action-oriented naming
        action_verbs = ['buy', 'call', 'schedule', 'review', 'send', 'book', 'order', 'pick', 'drop']
        if not any(verb in name_lower for verb in action_verbs):
            if not task['name'][0].isupper():
                task['name'] = task['name'].capitalize()
        
        # Context tag enrichment for ADHD clarity
        context_patterns = {
            'shopping': ['Shopping', 'Errand'],
            'grocery': ['Shopping', 'Errand'],
            'doctor': ['Appointment', 'Call'],
            'dentist': ['Appointment', 'Call'],
            'school': ['Family'],
            'work': ['Work'],
            'meeting': ['Meeting', 'Work'],
            'bill': ['Admin'],
            'exercise': ['Physical'],
            'clean': ['Household']
        }
        
        for pattern, tags in context_patterns.items():
            if pattern in name_lower:
                for tag in tags:
                    if tag not in task['context']:
                        task['context'].append(tag)
        
        # Energy level adjustment based on context
        if 'deep work' in task['context'] or 'creative' in name_lower:
            task['energy'] = 'High'
        elif 'errand' in task['context'] or 'quick' in name_lower:
            task['energy'] = 'Low'
        
        return task
    
    def _calculate_avg_confidence(self, result: Dict) -> float:
        """Calculate average confidence score for monitoring"""
        tasks = result.get('tasks', [])
        if not tasks:
            return 0.0
        
        total_confidence = sum(task.get('confidence', 0) for task in tasks)
        return total_confidence / len(tasks)
    
    def _fallback_extraction(self, message: str) -> Dict:
        """Enhanced fallback when AI parsing fails"""
        # Try to extract basic patterns
        name = message[:100].strip()
        
        # Basic urgency detection
        eisenhower = 'DO_NOW' if any(word in message.lower() for word in ['urgent', 'asap', 'emergency']) else 'SCHEDULE'
        
        # Basic assignment detection
        assigned_to = 'mene'
        if 'viola' in message.lower() or 'au pair' in message.lower():
            assigned_to = 'viola'
        elif 'cindy' in message.lower() or 'wife' in message.lower():
            assigned_to = 'cindy'
        
        return {
            "tasks": [{
                "name": name,
                "eisenhower": eisenhower,
                "context": ["Uncategorized"],
                "energy": "Medium",
                "time_estimate": "Short",
                "assigned_to": assigned_to,
                "due_date": None,
                "confidence": 0.3
            }],
            "reasoning": "Fallback extraction due to AI parsing error - requires manual review"
        }

# Backward compatibility
class TaskParser(EnhancedTaskParser):
    """Alias for backward compatibility"""
    pass

# Export for easy importing
__all__ = ['EnhancedTaskParser', 'TaskParser']
