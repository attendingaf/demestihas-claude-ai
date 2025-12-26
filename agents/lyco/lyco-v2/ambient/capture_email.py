"""
Lyco 2.0 Gmail Signal Capture
Extracts commitments and requests from email
"""
import os
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import base64
from email.mime.text import MIMEText

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

logger = logging.getLogger(__name__)

# Commitment patterns to look for
COMMITMENT_PATTERNS = [
    r"(?i)\b(i will|i'll|i am going to|i can|let me)\b.*",
    r"(?i)\b(will send|will review|will prepare|will schedule|will call)\b.*",
    r"(?i)\b(by|before|until|on)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|next week|\d{1,2}[/-]\d{1,2})",
    r"(?i)\b(send|review|prepare|schedule|call|follow up|check|update|finish|complete)\b.*\b(by|before|tomorrow|today|this week|next week)\b",
    r"(?i)\b(action item|todo|task|followup|follow-up):\s*.*",
    r"(?i)^(?:i need to|need to|have to|must|should)\b.*",
]

# Request patterns (things requested OF the user)
REQUEST_PATTERNS = [
    r"(?i)\b(can you|could you|would you|please)\b.*",
    r"(?i)\b(need you to|need your|requesting|request that you)\b.*",
    r"(?i)\b(please send|please review|please prepare|please schedule)\b.*",
    r"(?i)\b(urgent|asap|immediately|by eod|by end of day)\b.*",
    r"(?i)\?\s*$",  # Questions often imply requests
]


class EmailCapture:
    """Captures commitment signals from Gmail"""

    def __init__(self):
        self.service = None
        self.credentials = None
        self._init_gmail_service()

    def _init_gmail_service(self):
        """Initialize Gmail API service"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            creds = None

            # Token file path
            token_path = os.path.join(
                os.path.dirname(__file__),
                '../credentials/gmail_token.json'
            )
            creds_path = os.path.join(
                os.path.dirname(__file__),
                '../credentials/gmail_credentials.json'
            )

            # Load token if exists
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if os.path.exists(creds_path):
                        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.warning(f"Gmail credentials file not found at {creds_path}")
                        return

                # Save credentials for next time
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized")

        except Exception as e:
            logger.error(f"Error initializing Gmail service: {e}")

    async def capture_signals(self, email_address: str) -> List[Dict[str, Any]]:
        """Capture commitment signals from Gmail for a specific email address"""
        if not self.service:
            logger.warning("Gmail service not initialized")
            return []

        signals = []

        try:
            # Query for recent emails (last 24 hours)
            after_date = (datetime.now() - timedelta(hours=24)).strftime('%Y/%m/%d')

            # Search for sent emails (commitments BY user)
            sent_query = f'from:{email_address} after:{after_date}'
            sent_emails = self._search_emails(sent_query)

            for email in sent_emails:
                content = self._extract_email_content(email)
                if content and self._contains_commitment(content):
                    signals.append({
                        'content': f"Sent email: {content}",
                        'user_email': email_address,
                        'metadata': {
                            'message_id': email['id'],
                            'thread_id': email.get('threadId'),
                            'to': self._extract_recipients(email),
                            'subject': self._extract_subject(email),
                            'timestamp': datetime.now().isoformat(),
                            'type': 'commitment'
                        }
                    })

            # Search for received emails (requests OF user)
            received_query = f'to:{email_address} after:{after_date}'
            received_emails = self._search_emails(received_query)

            for email in received_emails:
                content = self._extract_email_content(email)
                if content and self._contains_request(content):
                    signals.append({
                        'content': f"Request from {self._extract_sender(email)}: {content}",
                        'user_email': email_address,
                        'metadata': {
                            'message_id': email['id'],
                            'thread_id': email.get('threadId'),
                            'from': self._extract_sender(email),
                            'subject': self._extract_subject(email),
                            'timestamp': datetime.now().isoformat(),
                            'type': 'request'
                        }
                    })

            logger.info(f"Captured {len(signals)} signals from {email_address}")

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")

        return signals

    def _search_emails(self, query: str, max_results: int = 50) -> List[Dict]:
        """Search for emails matching query"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            # Fetch full message details
            full_messages = []
            for msg in messages:
                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                full_messages.append(full_msg)

            return full_messages

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def _extract_email_content(self, message: Dict) -> str:
        """Extract text content from email message"""
        try:
            payload = message.get('payload', {})

            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # Handle simple messages
            elif payload.get('body', {}).get('data'):
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # Extract snippet as fallback
            return message.get('snippet', '')

        except Exception as e:
            logger.error(f"Error extracting email content: {e}")
            return message.get('snippet', '')

    def _extract_subject(self, message: Dict) -> str:
        """Extract subject from email headers"""
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'subject':
                return header['value']
        return ''

    def _extract_sender(self, message: Dict) -> str:
        """Extract sender from email headers"""
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'from':
                return header['value']
        return 'Unknown'

    def _extract_recipients(self, message: Dict) -> str:
        """Extract recipients from email headers"""
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'to':
                return header['value']
        return ''

    def _contains_commitment(self, content: str) -> bool:
        """Check if email contains a commitment pattern"""
        # Limit to first 500 chars for efficiency
        content_sample = content[:500].lower()

        for pattern in COMMITMENT_PATTERNS:
            if re.search(pattern, content_sample):
                return True
        return False

    def _contains_request(self, content: str) -> bool:
        """Check if email contains a request pattern"""
        # Limit to first 500 chars for efficiency
        content_sample = content[:500].lower()

        for pattern in REQUEST_PATTERNS:
            if re.search(pattern, content_sample):
                return True
        return False
