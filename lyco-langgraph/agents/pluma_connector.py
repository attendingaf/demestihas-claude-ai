"""
Pluma email connector for Lyco LangGraph.

Captures email signals and feeds them into the workflow.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from email.mime.text import MIMEText
import smtplib
import os


class PlumaConnector:
    """
    Connector for email signal capture via Pluma integration.

    Monitors:
    - mene@beltlineconsulting.co
    - menelaos4@gmail.com
    """

    def __init__(self, webhook_url: str = "http://localhost:8000/api/task/process"):
        self.webhook_url = webhook_url
        self.monitored_emails = [
            os.getenv("EMAIL_ADDRESS_MENE", "mene@beltlineconsulting.co"),
            os.getenv("EMAIL_ADDRESS_PERSONAL", "menelaos4@gmail.com")
        ]
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming email and extract task information.

        Args:
            email_data: Email metadata and content

        Returns:
            Processed task data for workflow
        """
        # Extract key information
        sender = email_data.get("from", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        received_at = email_data.get("received_at", datetime.now().isoformat())

        # Determine if this is actionable
        actionable_keywords = [
            "action required", "please", "can you", "need", "urgent",
            "asap", "deadline", "review", "approve", "schedule"
        ]

        is_actionable = any(
            keyword in subject.lower() or keyword in body.lower()
            for keyword in actionable_keywords
        )

        # Build task text
        task_text = f"Email from {sender}: {subject}"
        if body:
            # Include first 500 chars of body
            task_text += f"\n\n{body[:500]}"

        # Prepare workflow input
        workflow_input = {
            "raw_input": task_text,
            "source": "email",
            "user_id": email_data.get("to", self.monitored_emails[0]),
            "source_metadata": {
                "from": sender,
                "subject": subject,
                "received_at": received_at,
                "is_actionable": is_actionable,
                "has_attachments": email_data.get("has_attachments", False)
            }
        }

        return workflow_input

    async def send_to_workflow(self, task_data: Dict[str, Any]) -> bool:
        """
        Send extracted task to LangGraph workflow.

        Args:
            task_data: Processed task data

        Returns:
            Success status
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=task_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Error sending to workflow: {e}")
            return False

    async def monitor_inbox(self, poll_interval: int = 60):
        """
        Monitor email inbox for new messages.

        Args:
            poll_interval: Seconds between inbox checks
        """
        print(f"Starting email monitoring for: {', '.join(self.monitored_emails)}")

        while True:
            try:
                # In production, would use IMAP or email API
                # For now, this is a placeholder
                await asyncio.sleep(poll_interval)

                # Simulate checking for new emails
                # In real implementation, would:
                # 1. Connect to email server
                # 2. Fetch unread messages
                # 3. Process each message
                # 4. Mark as processed

            except Exception as e:
                print(f"Error in email monitoring: {e}")
                await asyncio.sleep(poll_interval)

    def send_notification(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None
    ) -> bool:
        """
        Send email notification back to user.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            from_addr: Sender address

        Returns:
            Success status
        """
        if not self.smtp_username or not self.smtp_password:
            print("SMTP credentials not configured")
            return False

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = from_addr or self.smtp_username
            msg["To"] = to

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False


# Example usage
async def main():
    """Example of using Pluma connector"""
    connector = PlumaConnector()

    # Process a sample email
    sample_email = {
        "from": "client@example.com",
        "to": "mene@beltlineconsulting.co",
        "subject": "Urgent: Please review proposal",
        "body": "Hi Mene, Can you please review the attached proposal by EOD? Thanks!",
        "received_at": datetime.now().isoformat(),
        "has_attachments": True
    }

    # Process and send to workflow
    task_data = await connector.process_email(sample_email)
    print(f"Extracted task: {json.dumps(task_data, indent=2)}")

    success = await connector.send_to_workflow(task_data)
    print(f"Sent to workflow: {success}")


if __name__ == "__main__":
    asyncio.run(main())
