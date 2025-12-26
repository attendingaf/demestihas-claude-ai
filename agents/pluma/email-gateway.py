#!/usr/bin/env python3
"""
Email Gateway for Task Capture
Monitors Gmail for tasks and forwards them to Lyco
"""

import asyncio
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import aiohttp
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from dotenv import load_dotenv

load_dotenv()

# Configuration
GMAIL_CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL", "60"))
GMAIL_TASKS_LABEL = os.getenv("GMAIL_TASKS_LABEL", "tasks@demestihas.ai")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "menelaos4@gmail.com")
LYCO_API_URL = os.getenv("LYCO_API_URL", "http://localhost:8000")
LOG_DIR = Path("/Users/menedemestihas/Projects/demestihas-ai/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"email_gateway_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmailGateway:
    """Email monitoring and task extraction service"""

    def __init__(self):
        self.gmail_service = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_emails = set()
        self.credentials_path = Path(__file__).parent / "credentials"
        self.credentials_path.mkdir(exist_ok=True)

    async def initialize(self):
        """Initialize Gmail service and HTTP session"""
        self.gmail_service = self._get_gmail_service()
        self.session = aiohttp.ClientSession()
        await self._load_processed_emails()
        logger.info("Email gateway initialized")

    def _get_gmail_service(self):
        """Authenticate and return Gmail service"""
        creds = None
        token_file = self.credentials_path / "token.pickle"

        if token_file.exists():
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path / 'gmail_credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        return build('gmail', 'v1', credentials=creds)

    async def _load_processed_emails(self):
        """Load set of already processed email IDs"""
        processed_file = LOG_DIR / "processed_emails.json"
        if processed_file.exists():
            with open(processed_file, "r") as f:
                self.processed_emails = set(json.load(f))

    async def _save_processed_emails(self):
        """Save set of processed email IDs"""
        processed_file = LOG_DIR / "processed_emails.json"
        with open(processed_file, "w") as f:
            json.dump(list(self.processed_emails), f)

    def _extract_tasks_from_email(self, email_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tasks from email content using patterns and LLM"""
        tasks = []

        # Get email details
        subject = email_content.get("subject", "")
        body = email_content.get("body", "")
        sender = email_content.get("sender", "")

        # Combine subject and body for analysis
        full_text = f"Subject: {subject}\n\n{body}"

        # Pattern-based extraction for common formats
        patterns = [
            r"(?:todo|task|action):\s*(.+)",  # TODO: task description
            r"(?:^|\n)[-*]\s+(.+)",  # Bullet points
            r"(?:^|\n)\d+\.\s+(.+)",  # Numbered lists
            r"(?:please|could you|can you|need to|must|should)\s+(.+?)(?:\.|$)",  # Action requests
        ]

        extracted_items = []

        for pattern in patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                item = match.group(1).strip()
                if len(item) > 10 and len(item) < 500:  # Basic validation
                    extracted_items.append(item)

        # Deduplicate while preserving order
        seen = set()
        unique_items = []
        for item in extracted_items:
            item_lower = item.lower()
            if item_lower not in seen:
                seen.add(item_lower)
                unique_items.append(item)

        # Create task objects
        for item in unique_items:
            task = {
                "title": item[:200],  # Limit title length
                "context": f"From email: {sender}\nSubject: {subject}",
                "source": "email_gateway",
                "email_id": email_content.get("id"),
                "sender": sender,
                "received_at": email_content.get("date")
            }

            # Try to extract additional metadata
            if "urgent" in item.lower() or "asap" in item.lower():
                task["priority"] = "high"
            elif "whenever" in item.lower() or "someday" in item.lower():
                task["priority"] = "low"
            else:
                task["priority"] = "medium"

            # Estimate duration based on keywords
            if "quick" in item.lower() or "simple" in item.lower():
                task["estimated_duration"] = 15
            elif "meeting" in item.lower() or "review" in item.lower():
                task["estimated_duration"] = 60
            elif "project" in item.lower() or "research" in item.lower():
                task["estimated_duration"] = 120

            tasks.append(task)

        # If no pattern matches, treat entire email as single task if it's short enough
        if not tasks and len(body) < 500:
            tasks.append({
                "title": subject if subject else body[:100],
                "context": body,
                "source": "email_gateway",
                "email_id": email_content.get("id"),
                "sender": sender,
                "priority": "medium"
            })

        return tasks

    async def send_to_lyco(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Send extracted task to Lyco for processing"""
        try:
            # First try the capture endpoint for LLM processing
            async with self.session.post(
                f"{LYCO_API_URL}/api/capture",
                json={
                    "text": task["title"],
                    "context": task.get("context", ""),
                    "source": "email_gateway",
                    "metadata": {
                        "sender": task.get("sender"),
                        "email_id": task.get("email_id"),
                        "priority": task.get("priority", "medium")
                    }
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # Fallback to direct task creation
                    async with self.session.post(
                        f"{LYCO_API_URL}/api/tasks",
                        json=task
                    ) as fallback_response:
                        if fallback_response.status in [200, 201]:
                            return await fallback_response.json()
                        else:
                            return {"error": f"Failed to create task: {response.status}"}

        except Exception as e:
            logger.error(f"Error sending to Lyco: {e}")
            return {"error": str(e)}

    def _send_confirmation_email(self, to_email: str, tasks: List[Dict[str, Any]], original_subject: str):
        """Send confirmation email back to sender"""
        try:
            # Create message
            message = MIMEMultipart()
            message['To'] = to_email
            message['From'] = "Lyco Task System <noreply@demestihas.ai>"
            message['Subject'] = f"Re: {original_subject} - Tasks Captured"

            # Build email body
            body_lines = ["Your email has been processed and the following tasks were captured:\n"]

            for i, task in enumerate(tasks, 1):
                if "error" in task:
                    body_lines.append(f"{i}. ❌ Error: {task.get('title', 'Unknown')} - {task['error']}")
                else:
                    task_data = task.get("task", task)
                    body_lines.append(f"{i}. ✅ {task_data.get('title', 'Untitled')}")
                    if task_data.get("priority"):
                        body_lines.append(f"   Priority: {task_data['priority']}")
                    if task_data.get("estimated_duration"):
                        body_lines.append(f"   Duration: {task_data['estimated_duration']} min")

            body_lines.append("\n---")
            body_lines.append("Tasks are now available in your Lyco dashboard.")
            body_lines.append("Reply with additional tasks anytime.")

            body = "\n".join(body_lines)
            message.attach(MIMEText(body, 'plain'))

            # Send via Gmail API
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            logger.info(f"Confirmation sent to {to_email}")

        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")

    def _send_error_notification(self, error: str, email_data: Dict[str, Any]):
        """Send error notification to admin"""
        try:
            message = MIMEMultipart()
            message['To'] = ADMIN_EMAIL
            message['From'] = "Lyco Task System <noreply@demestihas.ai>"
            message['Subject'] = "Error Processing Task Email"

            body = f"""
Error processing email:

From: {email_data.get('sender', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Date: {email_data.get('date', 'Unknown')}

Error: {error}

Please check the logs for more details.
            """

            message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")

    async def process_email(self, message_id: str) -> bool:
        """Process a single email message"""
        try:
            # Get email details
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract email content
            headers = message['payload'].get('headers', [])
            email_data = {
                "id": message_id,
                "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                "sender": next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                "date": next((h['value'] for h in headers if h['name'] == 'Date'), '')
            }

            # Extract body
            body = self._extract_body(message['payload'])
            email_data['body'] = body

            logger.info(f"Processing email from {email_data['sender']}: {email_data['subject']}")

            # Extract tasks
            tasks = self._extract_tasks_from_email(email_data)

            if not tasks:
                logger.info("No tasks found in email")
                return True

            # Send tasks to Lyco
            results = []
            for task in tasks:
                result = await self.send_to_lyco(task)
                results.append(result)

            # Send confirmation
            sender_email = re.search(r'<(.+?)>', email_data['sender'])
            if sender_email:
                sender_email = sender_email.group(1)
            else:
                sender_email = email_data['sender']

            self._send_confirmation_email(sender_email, results, email_data['subject'])

            # Mark email as read
            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            # Add to processed set
            self.processed_emails.add(message_id)
            await self._save_processed_emails()

            logger.info(f"Successfully processed {len(tasks)} tasks from email {message_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing email {message_id}: {e}")
            self._send_error_notification(str(e), {"id": message_id})
            return False

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from email payload"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
                elif part['mimeType'] == 'multipart/alternative':
                    body = self._extract_body(part)
                    if body:
                        break
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        return body

    async def check_emails(self):
        """Check for new task emails"""
        try:
            # Search for unread emails with the tasks label
            query = f'is:unread label:{GMAIL_TASKS_LABEL}' if GMAIL_TASKS_LABEL else 'is:unread subject:task'

            results = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()

            messages = results.get('messages', [])

            if messages:
                logger.info(f"Found {len(messages)} new task emails")

                for message in messages:
                    if message['id'] not in self.processed_emails:
                        await self.process_email(message['id'])
                        await asyncio.sleep(1)  # Rate limiting

        except Exception as e:
            logger.error(f"Error checking emails: {e}")

    async def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info(f"Starting email monitoring (checking every {GMAIL_CHECK_INTERVAL} seconds)")

        while True:
            try:
                await self.check_emails()
                await asyncio.sleep(GMAIL_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        await self._save_processed_emails()


async def main():
    """Main entry point"""
    gateway = EmailGateway()

    try:
        await gateway.initialize()
        await gateway.run_monitoring_loop()
    finally:
        await gateway.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Email gateway stopped by user")
