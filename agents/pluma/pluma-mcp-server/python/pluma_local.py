#!/usr/bin/env python3
"""Local Pluma Agent implementation for Claude Desktop testing."""

import os
import json
import logging

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import base64
from email.mime.text import MIMEText
from dotenv import load_dotenv
import anthropic
from gmail_auth import GmailAuthenticator
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pluma_local.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LocalPlumaAgent:
    """Local implementation of Pluma email agent."""
    
    def __init__(self):
        """Initialize the local Pluma agent."""
        # Gmail authentication
        self.gmail_auth = GmailAuthenticator()
        self.gmail_service = None
        
        # Redis connection (local)
        self.redis_client = self._setup_redis()
        
        # Claude API
        self.claude_client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Configuration
        self.max_results = 10
        self.draft_style = os.getenv('PLUMA_DRAFT_STYLE', 'professional')
        
    def _setup_redis(self) -> Optional['redis.Redis']:
        """Set up local Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("⚠ Redis module not installed - running without caching")
            return None
            
        try:
            # Connect to local Redis (default port 6379)
            client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            # Test connection
            client.ping()
            logger.info("✓ Connected to local Redis")
            return client
        except redis.ConnectionError:
            logger.warning("⚠ Redis not available - running without caching")
            return None
    
    def initialize(self) -> bool:
        """Initialize Gmail service."""
        self.gmail_service = self.gmail_auth.get_service()
        return self.gmail_service is not None
    
    def fetch_latest_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch the latest emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        if not self.gmail_service:
            logger.error("Gmail service not initialized")
            return []
        
        try:
            # Fetch emails from the last 7 days
            query = f'after:{(datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")}'
            
            results = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                # Get full message details
                message = self.gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                # Parse email data
                email_data = self._parse_email(message)
                emails.append(email_data)
                
                # Cache in Redis if available
                if self.redis_client:
                    cache_key = f"email:{msg['id']}"
                    self.redis_client.setex(
                        cache_key,
                        3600,  # 1 hour TTL
                        json.dumps(email_data)
                    )
            
            logger.info(f"✓ Fetched {len(emails)} emails")
            return emails
            
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            return []
    
    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message into structured format."""
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract body
        body = self._get_email_body(message['payload'])
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': subject,
            'from': sender,
            'to': to,
            'date': date,
            'snippet': message.get('snippet', ''),
            'body': body,
            'labels': message.get('labelIds', [])
        }
    
    def _get_email_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8', errors='ignore')
        
        return body
    
    def generate_draft_reply(self, email: Dict[str, Any], instructions: str = "") -> str:
        """
        Generate a draft reply using Claude API.
        
        Args:
            email: Email dictionary to reply to
            instructions: Optional specific instructions for the reply
            
        Returns:
            Generated draft reply text
        """
        # Prepare context for Claude
        prompt = f"""You are helping draft an email reply. Please generate a {self.draft_style} response.

Original Email:
From: {email['from']}
Subject: {email['subject']}
Date: {email['date']}

Body:
{email['body'][:2000]}  # Limit to prevent token overflow

{f"Additional Instructions: {instructions}" if instructions else ""}

Please generate an appropriate reply. Keep it concise and professional."""
        
        try:
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            draft = response.content[0].text
            logger.info("✓ Generated draft reply using Claude")
            
            # Cache draft if Redis available
            if self.redis_client:
                cache_key = f"draft:{email['id']}"
                self.redis_client.setex(cache_key, 3600, draft)
            
            return draft
            
        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            return "Failed to generate draft reply."
    
    def create_gmail_draft(self, email: Dict[str, Any], draft_body: str) -> Optional[str]:
        """
        Create a draft in Gmail.
        
        Args:
            email: Original email to reply to
            draft_body: Draft reply body
            
        Returns:
            Draft ID if successful, None otherwise
        """
        if not self.gmail_service:
            logger.error("Gmail service not initialized")
            return None
        
        try:
            # Extract sender email
            from_email = email['from']
            if '<' in from_email:
                from_email = from_email.split('<')[1].rstrip('>')
            
            # Create message
            message = MIMEText(draft_body)
            message['to'] = from_email
            message['subject'] = f"Re: {email['subject']}"
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Create draft
            draft = self.gmail_service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': raw_message,
                        'threadId': email['thread_id']
                    }
                }
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"✓ Created Gmail draft: {draft_id}")
            return draft_id
            
        except HttpError as error:
            logger.error(f"Error creating draft: {error}")
            return None
    
    def get_email_stats(self) -> Dict[str, Any]:
        """Get email statistics from cache."""
        if not self.redis_client:
            return {"status": "Redis not available"}
        
        try:
            # Get all cached email keys
            email_keys = self.redis_client.keys("email:*")
            draft_keys = self.redis_client.keys("draft:*")
            
            return {
                "cached_emails": len(email_keys),
                "cached_drafts": len(draft_keys),
                "redis_status": "connected"
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Clear all cached data."""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("✓ Cache cleared")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")

if __name__ == "__main__":
    # Test the local Pluma agent
    agent = LocalPlumaAgent()
    
    if agent.initialize():
        print("\n✓ Pluma Local Agent initialized successfully!")
        print("\nFetching latest emails...")
        
        emails = agent.fetch_latest_emails(max_results=5)
        if emails:
            print(f"\nFound {len(emails)} emails:")
            for i, email in enumerate(emails, 1):
                print(f"\n{i}. From: {email['from'][:50]}...")
                print(f"   Subject: {email['subject']}")
                print(f"   Date: {email['date']}")
        
        # Show stats
        stats = agent.get_email_stats()
        print(f"\n📊 Stats: {stats}")
    else:
        print("\n❌ Failed to initialize Pluma agent")
        print("Please check your credentials and try again")