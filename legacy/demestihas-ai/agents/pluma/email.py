"""
Email handling module for Pluma agent
Provides Gmail API integration and email processing utilities
"""

import os
import json
import base64
import email
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    """Structured email message data"""
    id: str
    subject: str
    sender: str
    body: str
    thread_id: str
    labels: List[str]
    timestamp: str
    has_attachments: bool = False

class EmailHandler:
    """Gmail API wrapper for Pluma agent"""
    
    def __init__(self, credentials_path: str = '/app/credentials.json', 
                 token_path: str = '/app/token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._initialize_service()
        self.user_email = self._get_user_email()
    
    def _initialize_service(self):
        """Initialize Gmail service with OAuth2 credentials"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path)
            
            # Refresh if needed
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    logger.error("Gmail credentials expired or missing")
                    return None
            
            # Build service
            service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail service initialized")
            return service
            
        except Exception as e:
            logger.error(f"❌ Gmail service initialization failed: {e}")
            return None
    
    def _get_user_email(self) -> str:
        """Get authenticated user's email address"""
        if not self.service:
            return ""
            
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', '')
        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return ""
    
    def get_recent_emails(self, query: str = 'in:inbox', max_results: int = 10) -> List[EmailMessage]:
        """Get recent emails matching query"""
        if not self.service:
            return []
        
        try:
            # Get message IDs
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            email_list = []
            
            # Fetch detailed message data
            for msg_info in messages:
                try:
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg_info['id'],
                        format='full'
                    ).execute()
                    
                    email_msg = self._parse_email_message(message)
                    if email_msg:
                        email_list.append(email_msg)
                        
                except Exception as e:
                    logger.debug(f"Failed to fetch message {msg_info['id']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(email_list)} emails")
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            return []
    
    def _parse_email_message(self, message: Dict) -> Optional[EmailMessage]:
        """Parse Gmail API message into EmailMessage object"""
        try:
            payload = message['payload']
            headers = {h['name']: h['value'] for h in payload.get('headers', [])}
            
            # Extract basic info
            subject = headers.get('Subject', '(No Subject)')
            sender = headers.get('From', '(Unknown Sender)')
            thread_id = message.get('threadId', '')
            labels = message.get('labelIds', [])
            timestamp = headers.get('Date', '')
            
            # Extract body
            body = self._extract_email_body(payload)
            
            # Check for attachments
            has_attachments = self._has_attachments(payload)
            
            return EmailMessage(
                id=message['id'],
                subject=subject,
                sender=sender,
                body=body,
                thread_id=thread_id,
                labels=labels,
                timestamp=timestamp,
                has_attachments=has_attachments
            )
            
        except Exception as e:
            logger.error(f"Failed to parse email message: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract plain text body from email payload"""
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    elif part['mimeType'] == 'multipart/alternative' and 'parts' in part:
                        # Recursively check nested parts
                        nested_body = self._extract_email_body(part)
                        if nested_body:
                            return nested_body
            
            # Handle simple messages
            elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.debug(f"Body extraction failed: {e}")
        
        return "(Could not extract email body)"
    
    def _has_attachments(self, payload: Dict) -> bool:
        """Check if email has attachments"""
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if 'filename' in part and part['filename']:
                        return True
                    # Check nested parts
                    if 'parts' in part:
                        if self._has_attachments(part):
                            return True
            return False
        except:
            return False
    
    def get_sent_emails(self, max_results: int = 100) -> List[EmailMessage]:
        """Get sent emails for tone learning"""
        return self.get_recent_emails(query='in:sent', max_results=max_results)
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email (for draft implementation)"""
        if not self.service:
            logger.error("Gmail service not available")
            return False
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # Encode for Gmail API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            send_result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"✅ Email sent successfully: {send_result['id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def create_draft(self, to: str, subject: str, body: str) -> Optional[str]:
        """Create email draft"""
        if not self.service:
            return None
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # Encode for Gmail API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Create draft
            draft_result = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {'raw': raw_message}
                }
            ).execute()
            
            draft_id = draft_result['id']
            logger.info(f"✅ Draft created: {draft_id}")
            return draft_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create draft: {e}")
            return None
    
    def apply_labels(self, message_id: str, add_labels: List[str] = None, 
                    remove_labels: List[str] = None) -> bool:
        """Apply or remove labels from email"""
        if not self.service:
            return False
        
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels
            
            if not body:
                return True  # Nothing to do
            
            result = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            
            logger.info(f"✅ Labels updated for message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply labels: {e}")
            return False
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        return self.apply_labels(message_id, remove_labels=['UNREAD'])
    
    def archive_email(self, message_id: str) -> bool:
        """Archive email (remove from inbox)"""
        return self.apply_labels(message_id, remove_labels=['INBOX'])
    
    def get_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """Get specific email by ID"""
        if not self.service:
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_email_message(message)
            
        except Exception as e:
            logger.error(f"Failed to get email {message_id}: {e}")
            return None
    
    def search_emails(self, query: str, max_results: int = 20) -> List[EmailMessage]:
        """Search emails with Gmail query syntax"""
        return self.get_recent_emails(query=query, max_results=max_results)
    
    def get_unread_count(self) -> int:
        """Get count of unread emails"""
        if not self.service:
            return 0
        
        try:
            result = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1
            ).execute()
            
            return result.get('resultSizeEstimate', 0)
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
