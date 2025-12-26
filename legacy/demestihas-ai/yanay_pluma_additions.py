"""
Pluma Integration additions for yanay.py
Add these methods and routing logic to the existing YanayOrchestrator class
"""

import aiohttp
import json
import re
from typing import Optional

class PlumaIntegration:
    """Pluma agent integration for email and meeting processing"""
    
    def __init__(self, redis_client, logger):
        self.redis_client = redis_client
        self.logger = logger
        self.pluma_url = "http://demestihas-pluma:8080"  # Container network URL
    
    def should_route_to_pluma(self, message: str) -> bool:
        """Determine if message should be routed to Pluma agent"""
        pluma_keywords = [
            'email', 'draft', 'reply', 'inbox', 'unread', 
            'meeting notes', 'transcribe', 'summarize meeting',
            'action items', 'organize emails', 'priority',
            'gmail', 'compose', 'send email', 'email status'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in pluma_keywords)
    
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
    
    async def route_to_pluma(self, message: str, user_id: str) -> str:
        """Route message to Pluma agent for email/meeting processing"""
        try:
            self.logger.info(f"Routing to Pluma agent: {message[:50]}...")
            
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
                return """📧 **Pluma Agent Available**

I can help you with:
• **Email Drafting**: "draft reply to latest email"
• **Inbox Management**: "organize my inbox" or "check unread emails"  
• **Meeting Notes**: "process meeting notes [audio_url]"
• **Email Status**: "gmail connection status"

What would you like me to help with?"""
                
        except Exception as e:
            self.logger.error(f"Pluma routing failed: {e}")
            return "I encountered an issue with email processing. The Pluma agent may be unavailable. Please try again in a moment."
    
    async def _handle_email_draft(self, message: str, user_id: str) -> str:
        """Handle email drafting requests"""
        try:
            # Extract email ID if provided, otherwise use latest
            email_id = self._extract_email_id(message)
            
            payload = {
                "task": "draft_reply",
                "email_id": email_id,
                "user_id": user_id,
                "message": message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.pluma_url}/process", 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._format_draft_response(result)
                    elif response.status == 404:
                        return "🔧 Pluma agent is not yet deployed. Please run the deployment script first."
                    else:
                        return f"I couldn't process your email request right now. (Error: {response.status})"
                        
        except aiohttp.ClientTimeout:
            return "Email processing is taking longer than expected. Please try again in a moment."
        except Exception as e:
            self.logger.error(f"Email draft handling failed: {e}")
            return "I encountered an issue creating your email draft. Please try again or check if the Pluma service is running."
    
    async def _handle_meeting_notes(self, message: str, user_id: str) -> str:
        """Handle meeting notes processing"""
        try:
            audio_url = self._extract_audio_url(message)
            
            if not audio_url:
                return """📝 **Meeting Notes Processing**

Please provide:
• Audio file URL for transcription
• Or upload audio file to process
• Example: "process meeting notes https://drive.google.com/audio.mp3"

I'll transcribe the audio and generate:
• Meeting summary
• Action items  
• Key decisions
• Follow-up emails"""
            
            payload = {
                "task": "meeting_notes",
                "audio_url": audio_url,
                "title": self._extract_meeting_title(message),
                "user_id": user_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.pluma_url}/process", 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 min for audio processing
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._format_meeting_notes_response(result)
                    else:
                        return f"I couldn't process the meeting notes. (Error: {response.status})"
                        
        except Exception as e:
            self.logger.error(f"Meeting notes handling failed: {e}")
            return "I encountered an issue processing the meeting notes. Please ensure the audio URL is accessible."
    
    async def _handle_inbox_management(self, message: str, user_id: str) -> str:
        """Handle inbox organization requests"""
        try:
            payload = {
                "task": "inbox_management",
                "user_id": user_id,
                "message": message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.pluma_url}/process", 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._format_inbox_management_response(result)
                    else:
                        return f"I couldn't manage your inbox right now. (Error: {response.status})"
                        
        except Exception as e:
            self.logger.error(f"Inbox management failed: {e}")
            return "I encountered an issue managing your inbox. Please ensure Gmail is properly connected."
    
    def _extract_email_id(self, message: str) -> Optional[str]:
        """Extract email ID from message if provided"""
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
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        match = re.search(url_pattern, message)
        return match.group(0) if match else None
    
    def _extract_meeting_title(self, message: str) -> str:
        """Extract meeting title from message"""
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
    
    def _format_draft_response(self, result_data: dict) -> str:
        """Format email draft response for user"""
        if result_data.get('success'):
            draft = result_data.get('draft', {})
            subject = draft.get('subject', 'Reply')
            confidence = draft.get('confidence', 0.5)
            preview = draft.get('body', '')[:200] + "..."
            
            confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
            
            return f"""📧 **Email Draft Created** {confidence_emoji}

**Subject:** {subject}
**Confidence:** {confidence:.1%}

**Preview:**
{preview}

The draft has been created and saved. Reply with:
• "show full draft" - See complete email
• "send draft" - Send the email
• "revise draft" - Make changes
• "create new draft" - Start over"""
        else:
            error = result_data.get('error', 'Unknown error')
            return f"❌ **Draft Creation Failed**\n\n{error}\n\nPlease try again or check your Gmail connection."
    
    def _format_meeting_notes_response(self, result_data: dict) -> str:
        """Format meeting notes response for user"""
        if result_data.get('success'):
            notes = result_data.get('notes', {})
            title = notes.get('title', 'Meeting Notes')
            summary = notes.get('summary', 'Summary unavailable')
            action_count = len(notes.get('action_items', []))
            decision_count = len(notes.get('key_decisions', []))
            
            return f"""📝 **Meeting Notes Generated**

**Meeting:** {title}
**Summary:** {summary[:150]}{'...' if len(summary) > 150 else ''}

**Extracted:**
• {action_count} action items
• {decision_count} key decisions
• Follow-up items identified

Reply with:
• "show detailed notes" - Full meeting summary
• "create follow-up emails" - Generate team communications
• "export to notion" - Save to your Notion workspace
• "share notes" - Send to participants"""
        else:
            error = result_data.get('error', 'Processing failed')
            return f"❌ **Meeting Processing Failed**\n\n{error}\n\nPlease verify the audio URL is accessible and try again."
    
    def _format_inbox_management_response(self, result_data: dict) -> str:
        """Format inbox management response"""
        if result_data.get('success'):
            stats = result_data.get('stats', {})
            processed = stats.get('processed_count', 0)
            high_priority = stats.get('high_priority_count', 0)
            archived = stats.get('archived_count', 0)
            
            return f"""📮 **Inbox Management Complete**

**Processed:** {processed} emails
**High Priority:** {high_priority} emails flagged  
**Auto-archived:** {archived} newsletters/updates

Your inbox is now organized! Reply with:
• "show priority emails" - View urgent messages
• "draft replies" - Generate responses for key emails  
• "inbox summary" - Detailed processing report
• "set email rules" - Configure auto-organization"""
        else:
            error = result_data.get('error', 'Management failed')
            return f"❌ **Inbox Management Failed**\n\n{error}\n\nPlease check your Gmail connection and try again."

