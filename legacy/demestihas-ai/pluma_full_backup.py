#!/usr/bin/env python3
"""
Pluma Agent - Email Management and Executive Assistant
Replaces Fyxer AI functionality with Gmail drafting and meeting notes
"""

import os
import json
import redis
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import anthropic
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import email
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailDraft:
    """Email draft with metadata"""
    subject: str
    body: str
    to: str
    confidence: float
    tone_style: str
    original_message_id: Optional[str] = None

class PlumaAgent:
    """
    Pluma Agent - Email drafting and executive assistant
    Integrates with Gmail API and Claude for intelligent email management
    """
    
    def __init__(self):
        self.redis_client = self._init_redis()
        self.gmail_service = self._init_gmail()
        self.claude = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.user_email = None
        self.tone_examples = {}
        
        # Initialize tone learning on startup
        asyncio.create_task(self.learn_email_tone())
        
    def _init_redis(self) -> redis.Redis:
        """Initialize Redis connection"""
        try:
            # Use container network name for Redis
            redis_url = os.getenv('REDIS_URL', 'redis://lyco-redis:6379')
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()  # Test connection
            logger.info("✅ Redis connection established")
            return client
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
            
    def _init_gmail(self):
        """Initialize Gmail API service"""
        try:
            # Check for existing credentials
            creds = None
            token_path = '/app/token.json'
            creds_path = '/app/credentials.json'
            
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path)
                
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    logger.warning("Gmail credentials not found - manual setup required")
                    return None
                    
            service = build('gmail', 'v1', credentials=creds)
            
            # Get user email for tone learning
            profile = service.users().getProfile(userId='me').execute()
            self.user_email = profile['emailAddress']
            
            logger.info(f"✅ Gmail API initialized for {self.user_email}")
            return service
            
        except Exception as e:
            logger.error(f"❌ Gmail initialization failed: {e}")
            return None
    
    async def learn_email_tone(self):
        """Learn writing tone from last 100 sent emails"""
        if not self.gmail_service:
            logger.warning("Gmail not available - skipping tone learning")
            return
            
        try:
            # Get sent emails
            result = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=['SENT'],
                maxResults=100
            ).execute()
            
            messages = result.get('messages', [])
            tone_samples = []
            
            logger.info(f"Learning tone from {len(messages)} sent emails...")
            
            for msg_info in messages[:20]:  # Process first 20 for speed
                try:
                    message = self.gmail_service.users().messages().get(
                        userId='me',
                        id=msg_info['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email content
                    payload = message['payload']
                    subject = next((h['value'] for h in payload.get('headers', []) 
                                  if h['name'] == 'Subject'), '')
                    
                    body = self._extract_email_body(payload)
                    if body and len(body) > 50:  # Meaningful content only
                        tone_samples.append({
                            'subject': subject,
                            'body': body[:500],  # First 500 chars
                            'length': len(body)
                        })
                        
                except Exception as e:
                    logger.debug(f"Failed to process sent email: {e}")
                    continue
            
            if tone_samples:
                # Use Claude to analyze tone patterns
                tone_analysis = await self._analyze_tone_patterns(tone_samples)
                
                # Store in Redis with expiry
                self.redis_client.setex(
                    f'pluma:tone:{self.user_email}', 
                    86400 * 7,  # 1 week
                    json.dumps(tone_analysis)
                )
                
                self.tone_examples = tone_analysis
                logger.info(f"✅ Learned tone patterns from {len(tone_samples)} emails")
            else:
                logger.warning("No suitable emails found for tone learning")
                
        except Exception as e:
            logger.error(f"❌ Tone learning failed: {e}")
    
    def _extract_email_body(self, payload) -> str:
        """Extract plain text body from email payload"""
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['mimeType'] == 'text/plain':
                    data = payload['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        except Exception:
            pass
        return ""
    
    async def _analyze_tone_patterns(self, tone_samples: List[Dict]) -> Dict:
        """Use Claude to analyze writing tone patterns"""
        try:
            sample_text = "\n\n---\n\n".join([
                f"Subject: {s['subject']}\nBody: {s['body']}" 
                for s in tone_samples[:10]
            ])
            
            prompt = f"""Analyze these email samples to identify the writing tone and style patterns:

{sample_text}

Provide a JSON response with:
- overall_tone: (professional, casual, friendly, direct, etc.)
- common_phrases: list of frequently used phrases
- greeting_style: typical greeting approach
- closing_style: typical closing approach
- formality_level: 1-5 scale
- key_characteristics: list of notable style elements

Focus on patterns that would help generate consistent email drafts."""

            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            tone_data = json.loads(response.content[0].text)
            return tone_data
            
        except Exception as e:
            logger.error(f"Failed to analyze tone: {e}")
            return {
                "overall_tone": "professional",
                "common_phrases": [],
                "greeting_style": "Hi",
                "closing_style": "Best regards",
                "formality_level": 3,
                "key_characteristics": ["Clear", "Concise"]
            }
    
    async def draft_reply(self, email_id: str) -> EmailDraft:
        """Generate reply draft for given email ID"""
        if not self.gmail_service:
            raise Exception("Gmail not available")
            
        try:
            # Get original email
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            # Extract email details
            payload = message['payload']
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
            body = self._extract_email_body(payload)
            
            # Get or load tone preferences
            tone_data = self.tone_examples or json.loads(
                self.redis_client.get(f'pluma:tone:{self.user_email}') or '{}'
            )
            
            # Generate draft with Claude
            draft = await self._generate_reply_draft(
                original_subject=subject,
                original_body=body,
                from_email=from_email,
                tone_style=tone_data
            )
            
            # Cache draft for quick access
            draft_key = f'pluma:draft:{email_id}'
            self.redis_client.setex(draft_key, 3600, json.dumps({
                'subject': draft.subject,
                'body': draft.body,
                'to': draft.to,
                'confidence': draft.confidence,
                'created_at': datetime.now().isoformat()
            }))
            
            logger.info(f"✅ Draft generated for email {email_id[:8]}...")
            return draft
            
        except Exception as e:
            logger.error(f"❌ Draft generation failed: {e}")
            raise
    
    async def _generate_reply_draft(self, original_subject: str, original_body: str, 
                                  from_email: str, tone_style: Dict) -> EmailDraft:
        """Use Claude to generate email reply draft"""
        
        # Prepare tone context
        tone_context = f"""
        Your writing style should match these patterns:
        - Overall tone: {tone_style.get('overall_tone', 'professional')}
        - Greeting: {tone_style.get('greeting_style', 'Hi')}
        - Closing: {tone_style.get('closing_style', 'Best regards')}
        - Formality level: {tone_style.get('formality_level', 3)}/5
        - Common phrases: {', '.join(tone_style.get('common_phrases', [])[:3])}
        """
        
        prompt = f"""You are drafting a reply email. Match the user's established writing tone and style.

{tone_context}

Original Email:
From: {from_email}
Subject: {original_subject}
Body: {original_body[:1000]}

Generate a reply that:
1. Acknowledges the original message appropriately  
2. Addresses key points requiring response
3. Matches the established tone and style
4. Is concise but complete
5. Uses appropriate greeting/closing for the relationship

Provide JSON response:
{{
    "subject": "Re: [subject]",
    "body": "[full email body]",
    "confidence": [0.0-1.0 confidence score],
    "reasoning": "[brief explanation of approach]"
}}"""

        try:
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            draft_data = json.loads(response.content[0].text)
            
            return EmailDraft(
                subject=draft_data['subject'],
                body=draft_data['body'],
                to=from_email,
                confidence=draft_data['confidence'],
                tone_style=tone_style.get('overall_tone', 'professional'),
                original_message_id=None
            )
            
        except Exception as e:
            logger.error(f"Claude draft generation failed: {e}")
            # Return fallback draft
            return EmailDraft(
                subject=f"Re: {original_subject}",
                body=f"{tone_style.get('greeting_style', 'Hi')},\n\nThank you for your message. I'll review this and get back to you.\n\n{tone_style.get('closing_style', 'Best regards')}",
                to=from_email,
                confidence=0.3,
                tone_style="fallback",
                original_message_id=None
            )
    
    async def get_latest_email_id(self) -> Optional[str]:
        """Get ID of most recent email for drafting"""
        if not self.gmail_service:
            return None
            
        try:
            result = self.gmail_service.users().messages().list(
                userId='me',
                maxResults=1,
                q='in:inbox'
            ).execute()
            
            messages = result.get('messages', [])
            return messages[0]['id'] if messages else None
            
        except Exception as e:
            logger.error(f"Failed to get latest email: {e}")
            return None
    
    async def smart_inbox_management(self):
        """Auto-label and prioritize emails"""
        if not self.gmail_service:
            return
            
        try:
            # Get recent unread emails
            result = self.gmail_service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=10
            ).execute()
            
            messages = result.get('messages', [])
            
            for msg_info in messages:
                try:
                    message = self.gmail_service.users().messages().get(
                        userId='me',
                        id=msg_info['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject']
                    ).execute()
                    
                    # Simple priority detection
                    headers = {h['name']: h['value'] for h in message['payload']['headers']}
                    subject = headers.get('Subject', '').lower()
                    from_addr = headers.get('From', '').lower()
                    
                    labels_to_add = []
                    
                    # Priority detection
                    if any(word in subject for word in ['urgent', 'asap', 'important', 'deadline']):
                        labels_to_add.append('IMPORTANT')
                    
                    # Newsletter detection  
                    if any(word in from_addr for word in ['noreply', 'newsletter', 'marketing']):
                        # Auto-archive newsletters (optional)
                        self.gmail_service.users().messages().modify(
                            userId='me',
                            id=msg_info['id'],
                            body={'removeLabelIds': ['INBOX']}
                        ).execute()
                    
                    # Apply labels
                    if labels_to_add:
                        self.gmail_service.users().messages().modify(
                            userId='me',
                            id=msg_info['id'],
                            body={'addLabelIds': labels_to_add}
                        ).execute()
                        
                except Exception as e:
                    logger.debug(f"Failed to process email {msg_info['id']}: {e}")
                    continue
                    
            logger.info(f"✅ Processed {len(messages)} emails for smart management")
            
        except Exception as e:
            logger.error(f"❌ Smart inbox management failed: {e}")
    
    async def process_meeting_notes(self, audio_url: str) -> Dict:
        """Process meeting audio through Hermes and generate notes"""
        try:
            # This would integrate with Hermes audio processing
            # For now, placeholder implementation
            
            # TODO: Call Hermes API for transcription
            # transcript = await hermes_api.transcribe(audio_url)
            
            # Placeholder transcript for testing
            transcript = "Meeting transcript would be here from Hermes integration"
            
            # Generate summary with Claude
            summary = await self._generate_meeting_summary(transcript)
            
            return {
                'transcript': transcript,
                'summary': summary['summary'],
                'action_items': summary['action_items'],
                'key_decisions': summary['key_decisions'],
                'follow_ups': summary['follow_ups']
            }
            
        except Exception as e:
            logger.error(f"❌ Meeting notes processing failed: {e}")
            return {
                'transcript': '',
                'summary': 'Failed to process meeting notes',
                'action_items': [],
                'key_decisions': [],
                'follow_ups': []
            }
    
    async def _generate_meeting_summary(self, transcript: str) -> Dict:
        """Generate meeting summary and action items"""
        prompt = f"""Analyze this meeting transcript and provide a structured summary:

Transcript:
{transcript}

Provide JSON response with:
{{
    "summary": "Brief 2-3 sentence meeting summary",
    "key_decisions": ["List of decisions made"],
    "action_items": [
        {{"task": "Action description", "owner": "Person responsible", "due": "Due date if mentioned"}}
    ],
    "follow_ups": ["List of follow-up items or questions"],
    "participants": ["List of people mentioned"],
    "duration_estimate": "Estimated meeting length"
}}"""

        try:
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Meeting summary generation failed: {e}")
            return {
                "summary": "Meeting summary unavailable",
                "key_decisions": [],
                "action_items": [],
                "follow_ups": [],
                "participants": [],
                "duration_estimate": "Unknown"
            }
    
    async def health_check(self) -> Dict:
        """Health check for Pluma agent"""
        status = {
            "service": "Pluma Agent",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check Redis
        try:
            self.redis_client.ping()
            status["components"]["redis"] = "connected"
        except:
            status["components"]["redis"] = "disconnected"
            status["status"] = "degraded"
        
        # Check Gmail
        if self.gmail_service:
            try:
                self.gmail_service.users().getProfile(userId='me').execute()
                status["components"]["gmail"] = "connected"
            except:
                status["components"]["gmail"] = "error"
                status["status"] = "degraded"
        else:
            status["components"]["gmail"] = "not_configured"
            status["status"] = "degraded"
        
        # Check Claude API
        try:
            # Simple API test
            test_response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            status["components"]["anthropic"] = "connected"
        except:
            status["components"]["anthropic"] = "error"
            status["status"] = "degraded"
        
        return status

async def main():
    """Main entry point for Pluma agent testing"""
    agent = PlumaAgent()
    
    # Test health check
    health = await agent.health_check()
    print(f"Health Status: {json.dumps(health, indent=2)}")
    
    # Test latest email draft (if available)
    try:
        latest_id = await agent.get_latest_email_id()
        if latest_id:
            print(f"\nTesting draft for latest email: {latest_id}")
            draft = await agent.draft_reply(latest_id)
            print(f"Draft confidence: {draft.confidence}")
            print(f"Subject: {draft.subject}")
            print(f"Body preview: {draft.body[:200]}...")
    except Exception as e:
        print(f"Draft test failed: {e}")
    
    # Test smart inbox management
    try:
        await agent.smart_inbox_management()
        print("\n✅ Smart inbox management completed")
    except Exception as e:
        print(f"Inbox management failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
