"""
Pluma Agent Integration for Yanay.ai
Add these methods to the yanay.py file to enable email and meeting routing
"""

# Add to yanay.py imports
import json
import aiohttp
from typing import Dict, Any, Optional

class PlumaIntegration:
    """Integration methods for Pluma agent in Yanay.ai orchestration"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.pluma_url = "http://demestihas-pluma:8080"  # Container network URL
    
    async def route_to_pluma(self, message: str, user_id: str) -> str:
        """Route message to Pluma agent for email/meeting processing"""
        try:
            # Determine Pluma task type
            task_type = self._classify_pluma_task(message)
            
            # Call appropriate Pluma method
            if task_type == "email_draft":
                return await self._handle_email_draft(message, user_id)
            elif task_type == "meeting_notes":
                return await self._handle_meeting_notes(message, user_id)
            elif task_type == "inbox_management":
                return await self._handle_inbox_management(message, user_id)
            else:
                return "I can help with email drafts, meeting notes, and inbox management. What would you like to do?"
                
        except Exception as e:
            logger.error(f"Pluma routing failed: {e}")
            return "I encountered an issue with email processing. Please try again or contact support."
    
    def _classify_pluma_task(self, message: str) -> str:
        """Classify message for appropriate Pluma handling"""
        message_lower = message.lower()
        
        # Email draft keywords
        if any(word in message_lower for word in ['draft', 'reply', 'email', 'respond to']):
            return "email_draft"
        
        # Meeting notes keywords  
        if any(word in message_lower for word in ['meeting notes', 'transcribe', 'summarize meeting', 'action items']):
            return "meeting_notes"
            
        # Inbox management keywords
        if any(word in message_lower for word in ['inbox', 'organize', 'priority', 'unread']):
            return "inbox_management"
        
        return "general"
    
    async def _handle_email_draft(self, message: str, user_id: str) -> str:
        """Handle email drafting requests"""
        try:
            # Extract email ID if provided, otherwise use latest
            email_id = self._extract_email_id(message)
            
            if not email_id:
                # Get latest email ID from Pluma
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.pluma_url}/latest-email") as response:
                        if response.status == 200:
                            data = await response.json()
                            email_id = data.get('email_id')
            
            if not email_id:
                return "I couldn't find a recent email to draft a reply for. Please specify which email you'd like me to help with."
            
            # Request draft from Pluma
            async with aiohttp.ClientSession() as session:
                payload = {
                    "email_id": email_id,
                    "user_id": user_id
                }
                
                async with session.post(f"{self.pluma_url}/draft-reply", json=payload) as response:
                    if response.status == 200:
                        draft_data = await response.json()
                        return self._format_draft_response(draft_data)
                    else:
                        return f"I couldn't create a draft for that email. Error: {response.status}"
                        
        except Exception as e:
            logger.error(f"Email draft handling failed: {e}")
            return "I encountered an issue creating your email draft. Please try again."
    
    async def _handle_meeting_notes(self, message: str, user_id: str) -> str:
        """Handle meeting notes processing"""
        try:
            # Extract audio URL if provided
            audio_url = self._extract_audio_url(message)
            
            if not audio_url:
                return "Please provide the audio file URL or upload the meeting recording for me to process."
            
            # Send to Pluma for processing
            async with aiohttp.ClientSession() as session:
                payload = {
                    "audio_url": audio_url,
                    "user_id": user_id,
                    "title": self._extract_meeting_title(message)
                }
                
                async with session.post(f"{self.pluma_url}/process-meeting", json=payload) as response:
                    if response.status == 200:
                        notes_data = await response.json()
                        return self._format_meeting_notes_response(notes_data)
                    else:
                        return f"I couldn't process the meeting notes. Error: {response.status}"
                        
        except Exception as e:
            logger.error(f"Meeting notes handling failed: {e}")
            return "I encountered an issue processing the meeting notes. Please try again."
    
    async def _handle_inbox_management(self, message: str, user_id: str) -> str:
        """Handle inbox organization requests"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"user_id": user_id}
                
                async with session.post(f"{self.pluma_url}/manage-inbox", json=payload) as response:
                    if response.status == 200:
                        result_data = await response.json()
                        return self._format_inbox_management_response(result_data)
                    else:
                        return f"I couldn't manage your inbox right now. Error: {response.status}"
                        
        except Exception as e:
            logger.error(f"Inbox management failed: {e}")
            return "I encountered an issue managing your inbox. Please try again."
    
    def _extract_email_id(self, message: str) -> Optional[str]:
        """Extract email ID from message if provided"""
        # Look for patterns like "email 123456" or message ID formats
        import re
        patterns = [
            r'email\s+([a-zA-Z0-9]+)',
            r'message\s+([a-zA-Z0-9]+)',
            r'id\s*:\s*([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        return None
    
    def _extract_audio_url(self, message: str) -> Optional[str]:
        """Extract audio URL from message"""
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        match = re.search(url_pattern, message)
        return match.group(0) if match else None
    
    def _extract_meeting_title(self, message: str) -> str:
        """Extract meeting title from message"""
        # Look for patterns like "meeting: title" or "title meeting"
        import re
        patterns = [
            r'meeting:?\s*(.+?)(?:\s+audio|\s+recording|$)',
            r'(.+?)\s+meeting\s+notes',
            r'notes\s+for\s+(.+?)(?:\s+meeting|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).strip().title()
        
        return "Meeting Notes"
    
    def _format_draft_response(self, draft_data: Dict) -> str:
        """Format email draft response for user"""
        subject = draft_data.get('subject', 'Reply')
        confidence = draft_data.get('confidence', 0.5)
        body_preview = draft_data.get('body', '')[:200] + "..."
        
        confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
        
        response = f"""📧 **Email Draft Created** {confidence_emoji}

**Subject:** {subject}
**Confidence:** {confidence:.1%}

**Preview:**
{body_preview}

The draft has been saved. Would you like me to:
• Show the full draft
• Make revisions
• Send it directly
• Create a different version"""

        return response
    
    def _format_meeting_notes_response(self, notes_data: Dict) -> str:
        """Format meeting notes response for user"""
        title = notes_data.get('title', 'Meeting Notes')
        summary = notes_data.get('summary', 'Summary unavailable')
        action_count = len(notes_data.get('action_items', []))
        decision_count = len(notes_data.get('key_decisions', []))
        
        response = f"""📝 **Meeting Notes Generated**

**Meeting:** {title}
**Summary:** {summary[:150]}{'...' if len(summary) > 150 else ''}

**Extracted:**
• {action_count} action items
• {decision_count} key decisions
• Follow-up items identified

Would you like me to:
• Show detailed notes
• Create follow-up emails
• Export to Notion
• Share with participants"""

        return response
    
    def _format_inbox_management_response(self, result_data: Dict) -> str:
        """Format inbox management response"""
        processed = result_data.get('processed_count', 0)
        high_priority = result_data.get('high_priority_count', 0)
        archived = result_data.get('archived_count', 0)
        
        response = f"""📮 **Inbox Management Complete**

**Processed:** {processed} emails
**High Priority:** {high_priority} emails flagged
**Auto-archived:** {archived} newsletters/updates

Your inbox is now organized! 

High priority emails are marked for your attention. Would you like me to:
• Show priority email summaries
• Draft responses for urgent items
• Set up auto-rules for future emails
• Schedule email review time"""

        return response

# Add to yanay.py routing logic in process_message method:

def should_route_to_pluma(self, message: str) -> bool:
    """Determine if message should be routed to Pluma agent"""
    pluma_keywords = [
        'email', 'draft', 'reply', 'inbox', 'unread', 
        'meeting notes', 'transcribe', 'summarize meeting',
        'action items', 'organize emails', 'priority'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in pluma_keywords)

# Integration in main process_message method:
async def process_message(self, message: str, user_id: str) -> str:
    """Enhanced message processing with Pluma integration"""
    # ... existing code ...
    
    # Check for Pluma routing
    if self.should_route_to_pluma(message):
        pluma_integration = PlumaIntegration(self.redis_client)
        return await pluma_integration.route_to_pluma(message, user_id)
    
    # ... rest of existing routing logic ...
