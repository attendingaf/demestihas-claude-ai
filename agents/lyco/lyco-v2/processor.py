#!/usr/bin/env python3
"""
Lyco 2.0 Background Processor
Runs continuously to process signals and integrate with other agents
"""
import asyncio
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import redis
from dotenv import load_dotenv

from src.database import DatabaseManager
from src.processor import IntelligenceEngine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackgroundProcessor:
    """Continuous background processing for Lyco 2.0"""

    def __init__(self):
        self.db = DatabaseManager()
        self.redis_client = self._init_redis()
        self.engine = self._init_engine()
        self.running = False

    def _init_redis(self) -> redis.Redis:
        """Initialize Redis connection"""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        return redis.from_url(redis_url, decode_responses=True)

    def _init_engine(self) -> IntelligenceEngine:
        """Initialize the intelligence engine"""
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        return IntelligenceEngine(anthropic_key, openai_key)

    async def capture_pluma_signals(self):
        """Capture email signals from Pluma agent"""
        try:
            # Get recent emails from Pluma via Redis
            pluma_data = self.redis_client.get("pluma:recent_emails")
            if not pluma_data:
                return

            emails = json.loads(pluma_data)

            # Get user emails
            work_email = os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
            home_email = os.environ.get('USER_HOME_EMAIL', '')
            user_emails = [work_email]
            if home_email:
                user_emails.append(home_email)

            for email in emails:
                from_email = email.get('from', '').lower()
                # Check if this is a commitment by or request of the user
                if any(user_email.lower() in from_email for user_email in user_emails):
                    # User sending email - check for commitments
                    # Determine which email was used
                    user_id = work_email if work_email.lower() in from_email else home_email

                    await self.db.create_signal(
                        source='pluma',
                        raw_content=f"Sent email: {email.get('subject', '')}\n{email.get('body', '')}",
                        metadata={
                            'thread_id': email.get('thread_id'),
                            'to': email.get('to'),
                            'timestamp': email.get('timestamp')
                        },
                        user_id=user_id
                    )
                else:
                    # Email to user - check for requests
                    # Determine which user email received it
                    to_email = email.get('to', '').lower()
                    user_id = work_email if work_email.lower() in to_email else (home_email if home_email.lower() in to_email else work_email)

                    await self.db.create_signal(
                        source='pluma',
                        raw_content=f"Received from {email.get('from')}: {email.get('subject', '')}\n{email.get('body', '')}",
                        metadata={
                            'thread_id': email.get('thread_id'),
                            'from': email.get('from'),
                            'timestamp': email.get('timestamp')
                        },
                        user_id=user_id
                    )

            logger.info(f"Captured {len(emails)} email signals from Pluma")

        except Exception as e:
            logger.error(f"Error capturing Pluma signals: {e}")

    async def capture_huata_signals(self):
        """Capture calendar signals from Huata agent"""
        try:
            # Get upcoming events from Huata via Redis
            huata_data = self.redis_client.get("huata:upcoming_events")
            if not huata_data:
                return

            events = json.loads(huata_data)

            for event in events:
                # Check if event needs preparation
                if event.get('prep_needed'):
                    await self.db.create_signal(
                        source='huata',
                        raw_content=f"Prepare for: {event.get('title')}\n{event.get('description', '')}",
                        metadata={
                            'event_id': event.get('id'),
                            'start_time': event.get('start'),
                            'attendees': event.get('attendees', []),
                            'location': event.get('location')
                        }
                    )

            logger.info(f"Captured {len(events)} calendar signals from Huata")

        except Exception as e:
            logger.error(f"Error capturing Huata signals: {e}")

    async def publish_status(self):
        """Publish Lyco status to Redis for other agents"""
        try:
            pending_count = await self.db.get_pending_tasks_count()

            status = {
                'agent': 'lyco',
                'version': '2.0',
                'pending_tasks': pending_count,
                'timestamp': datetime.now().isoformat(),
                'health': 'healthy'
            }

            self.redis_client.setex(
                "lyco:status",
                300,  # 5 minute TTL
                json.dumps(status)
            )

            # Publish to Redis pub/sub
            self.redis_client.publish("agent:status", json.dumps(status))

        except Exception as e:
            logger.error(f"Error publishing status: {e}")

    async def process_loop(self):
        """Main processing loop"""
        self.running = True
        logger.info("Lyco 2.0 processor started")

        while self.running:
            try:
                # Capture signals from other agents
                await self.capture_pluma_signals()
                await self.capture_huata_signals()

                # Process pending signals
                results = await self.engine.process_all_signals()

                if results['processed'] > 0:
                    logger.info(f"Processed {results['processed']} signals, created {results['tasks_created']} tasks")

                # Publish status
                await self.publish_status()

                # Wait 5 minutes before next cycle
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def cleanup_old_tasks(self):
        """Clean up old completed/skipped tasks"""
        # This would run daily to archive old tasks
        pass

    async def generate_insights(self):
        """Generate weekly insights from task patterns"""
        # This would run weekly to analyze patterns
        pass

    def stop(self):
        """Stop the processor"""
        self.running = False
        logger.info("Lyco 2.0 processor stopping")


async def main():
    """Run the background processor"""
    processor = BackgroundProcessor()

    try:
        await processor.process_loop()
    except KeyboardInterrupt:
        processor.stop()
        logger.info("Processor stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
