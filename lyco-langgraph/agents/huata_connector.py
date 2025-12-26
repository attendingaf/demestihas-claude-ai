"""
Huata calendar connector for Lyco LangGraph.

Captures calendar events and converts them to tasks.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
import os
from dateutil import parser


class HuataConnector:
    """
    Connector for calendar signal capture via Huata integration.

    Monitors Google Calendar for:
    - New events
    - Event updates
    - Meeting requests
    - Deadlines
    """

    def __init__(self, webhook_url: str = "http://localhost:8000/api/task/process"):
        self.webhook_url = webhook_url
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        self.api_key = os.getenv("GOOGLE_CALENDAR_API_KEY")
        self.lookahead_days = 7  # Look ahead 1 week

    async def process_calendar_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process calendar event and extract task information.

        Args:
            event: Calendar event data

        Returns:
            Processed task data for workflow
        """
        # Extract event details
        title = event.get("summary", "Calendar Event")
        description = event.get("description", "")
        start = event.get("start", {})
        end = event.get("end", {})
        location = event.get("location", "")
        attendees = event.get("attendees", [])

        # Parse start time
        start_time = None
        if "dateTime" in start:
            start_time = parser.parse(start["dateTime"])
        elif "date" in start:
            start_time = parser.parse(start["date"])

        # Parse end time
        end_time = None
        if "dateTime" in end:
            end_time = parser.parse(end["dateTime"])
        elif "date" in end:
            end_time = parser.parse(end["date"])

        # Extract attendee emails
        attendee_emails = [
            a.get("email", "") for a in attendees
            if a.get("email")
        ]

        # Determine task type
        task_type = "meeting"
        if "deadline" in title.lower() or "due" in title.lower():
            task_type = "deadline"
        elif "review" in title.lower():
            task_type = "review"
        elif "1:1" in title or "one on one" in title.lower():
            task_type = "one_on_one"

        # Build task text
        task_text = f"Calendar: {title}"
        if description:
            task_text += f"\n{description}"

        # Add preparation tasks if needed
        preparation_needed = []
        if task_type == "meeting" and len(attendee_emails) > 2:
            preparation_needed.append("Prepare agenda")
            preparation_needed.append("Review previous notes")
        elif task_type == "review":
            preparation_needed.append("Gather materials for review")

        # Calculate urgency based on time until event
        urgency = "normal"
        if start_time:
            time_until = start_time - datetime.now(start_time.tzinfo)
            if time_until < timedelta(hours=24):
                urgency = "high"
            elif time_until < timedelta(days=3):
                urgency = "medium"

        # Prepare workflow input
        workflow_input = {
            "raw_input": task_text,
            "source": "calendar",
            "user_id": os.getenv("EMAIL_ADDRESS_MENE", "mene@beltlineconsulting.co"),
            "deadline": start_time.isoformat() if start_time else None,
            "source_metadata": {
                "event_id": event.get("id"),
                "title": title,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "location": location,
                "attendees": attendee_emails,
                "task_type": task_type,
                "urgency": urgency,
                "preparation_needed": preparation_needed
            }
        }

        return workflow_input

    async def fetch_upcoming_events(self) -> List[Dict[str, Any]]:
        """
        Fetch upcoming calendar events.

        Returns:
            List of upcoming events
        """
        if not self.calendar_id or not self.api_key:
            print("Calendar credentials not configured")
            return []

        # Calculate time range
        time_min = datetime.now().isoformat() + "Z"
        time_max = (datetime.now() + timedelta(days=self.lookahead_days)).isoformat() + "Z"

        # In production, would use Google Calendar API
        # For now, return mock data for testing
        mock_events = [
            {
                "id": "evt_001",
                "summary": "Team Standup",
                "description": "Daily team sync",
                "start": {"dateTime": (datetime.now() + timedelta(hours=2)).isoformat()},
                "end": {"dateTime": (datetime.now() + timedelta(hours=2, minutes=30)).isoformat()},
                "attendees": [
                    {"email": "team@example.com"},
                    {"email": "mene@beltlineconsulting.co"}
                ]
            },
            {
                "id": "evt_002",
                "summary": "Project Deadline: Q4 Report",
                "description": "Submit quarterly report to board",
                "start": {"date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")},
                "end": {"date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")}
            }
        ]

        return mock_events

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

    async def monitor_calendar(self, poll_interval: int = 300):
        """
        Monitor calendar for events requiring action.

        Args:
            poll_interval: Seconds between calendar checks (default 5 minutes)
        """
        print(f"Starting calendar monitoring (checking every {poll_interval}s)")
        processed_events = set()

        while True:
            try:
                # Fetch upcoming events
                events = await self.fetch_upcoming_events()

                for event in events:
                    event_id = event.get("id")

                    # Skip if already processed
                    if event_id in processed_events:
                        continue

                    # Process event
                    task_data = await self.process_calendar_event(event)

                    # Send to workflow
                    success = await self.send_to_workflow(task_data)

                    if success:
                        processed_events.add(event_id)
                        print(f"Processed calendar event: {event.get('summary')}")

                await asyncio.sleep(poll_interval)

            except Exception as e:
                print(f"Error in calendar monitoring: {e}")
                await asyncio.sleep(poll_interval)

    def create_calendar_block(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 30,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a calendar block for task execution.

        Args:
            title: Event title
            start_time: Start time
            duration_minutes: Duration in minutes
            description: Event description

        Returns:
            Created event data
        """
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"[Lyco] {title}",
            "description": description or "Time blocked by Lyco for task execution",
            "start": {"dateTime": start_time.isoformat()},
            "end": {"dateTime": end_time.isoformat()},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 10}
                ]
            }
        }

        # In production, would create via Google Calendar API
        print(f"Would create calendar block: {title} at {start_time}")

        return event


# Example usage
async def main():
    """Example of using Huata connector"""
    connector = HuataConnector()

    # Fetch and process upcoming events
    events = await connector.fetch_upcoming_events()

    for event in events:
        task_data = await connector.process_calendar_event(event)
        print(f"\nProcessed event: {event.get('summary')}")
        print(f"Task data: {json.dumps(task_data, indent=2)}")

        # Send to workflow
        success = await connector.send_to_workflow(task_data)
        print(f"Sent to workflow: {success}")


if __name__ == "__main__":
    asyncio.run(main())
