#!/usr/bin/env python3
"""
Lyco 2.0 Ambient Capture Orchestrator
Main loop for automated signal collection from Gmail and Calendar
"""
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import DatabaseManager
from src.processor import IntelligenceEngine
from ambient.capture_email import EmailCapture
from ambient.capture_calendar import CalendarCapture
from ambient.redis_connector import RedisConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AmbientCaptureOrchestrator:
    """Main orchestrator for ambient signal capture"""

    def __init__(self):
        self.db = DatabaseManager()
        self.email_capture = EmailCapture()
        self.calendar_capture = CalendarCapture()
        self.redis = RedisConnector()
        self.engine = self._init_engine()
        self.running = False
        self.signal_cache = {}  # For deduplication

    def _init_engine(self) -> IntelligenceEngine:
        """Initialize the intelligence engine"""
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        return IntelligenceEngine(anthropic_key, openai_key)

    def _generate_signal_hash(self, content: str) -> str:
        """Generate hash for deduplication"""
        return hashlib.md5(content.encode()).hexdigest()

    async def _is_duplicate_signal(self, content: str) -> bool:
        """Check if signal already exists in last 24 hours"""
        signal_hash = self._generate_signal_hash(content)

        # Check in-memory cache
        if signal_hash in self.signal_cache:
            cache_time = self.signal_cache[signal_hash]
            # Make both datetimes timezone-aware for comparison
            now = datetime.now(timezone.utc)
            if hasattr(cache_time, 'tzinfo') and cache_time.tzinfo:
                time_diff = now - cache_time
            else:
                cache_time_utc = cache_time.replace(tzinfo=timezone.utc)
                time_diff = now - cache_time_utc
            if time_diff < timedelta(hours=24):
                return True

        # Check database for recent signals
        recent_signals = await self.db.get_recent_signals(hours=24)
        for signal in recent_signals:
            existing_hash = self._generate_signal_hash(signal.raw_content)
            if existing_hash == signal_hash:
                self.signal_cache[signal_hash] = signal.timestamp
                return True

        return False

    async def capture_email_signals(self):
        """Capture signals from Gmail"""
        try:
            logger.info("Starting email signal capture...")

            # Get emails from both accounts
            work_email = os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
            home_email = os.environ.get('USER_HOME_EMAIL', 'menelaos4@gmail.com')

            all_signals = []

            # Capture from work email
            work_signals = await self.email_capture.capture_signals(work_email)
            all_signals.extend(work_signals)

            # Capture from home email
            if home_email:
                home_signals = await self.email_capture.capture_signals(home_email)
                all_signals.extend(home_signals)

            # Process and create signals
            created_count = 0
            for signal_data in all_signals:
                # Check for duplicates
                if await self._is_duplicate_signal(signal_data['content']):
                    logger.debug(f"Skipping duplicate signal: {signal_data['content'][:50]}...")
                    continue

                # Create signal in database
                signal_id = await self.db.create_signal(
                    source='gmail',
                    raw_content=signal_data['content'],
                    metadata=signal_data.get('metadata', {}),
                    user_id=signal_data.get('user_email', work_email)
                )

                # Cache the signal
                signal_hash = self._generate_signal_hash(signal_data['content'])
                self.signal_cache[signal_hash] = datetime.now(timezone.utc)

                # Publish to Redis (if available)
                try:
                    await self.redis.publish('lyco:signal_created', {
                        'signal_id': str(signal_id),
                        'source': 'gmail',
                        'timestamp': datetime.now().isoformat()
                    })
                except:
                    pass  # Redis not critical for core function

                created_count += 1

            logger.info(f"Created {created_count} email signals from {len(all_signals)} candidates")

        except Exception as e:
            logger.error(f"Error capturing email signals: {e}")

    async def capture_calendar_signals(self):
        """Capture signals from Google Calendar"""
        try:
            logger.info("Starting calendar signal capture...")

            # Calendar IDs to check
            calendar_ids = [
                'menelaos4@gmail.com',  # Primary
                'mene@beltlineconsulting.co',  # Work
                '7dia35946hir6rbq10stda8hk4@group.calendar.google.com',  # Family
                'e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com'  # Limon y Sal
            ]

            all_signals = []

            # Capture from all calendars
            for calendar_id in calendar_ids:
                try:
                    calendar_signals = await self.calendar_capture.capture_signals(calendar_id)
                    all_signals.extend(calendar_signals)
                except Exception as e:
                    logger.warning(f"Error capturing from calendar {calendar_id}: {e}")

            # Process and create signals
            created_count = 0
            for signal_data in all_signals:
                # Check for duplicates
                if await self._is_duplicate_signal(signal_data['content']):
                    logger.debug(f"Skipping duplicate signal: {signal_data['content'][:50]}...")
                    continue

                # Create signal in database
                signal_id = await self.db.create_signal(
                    source='calendar',
                    raw_content=signal_data['content'],
                    metadata=signal_data.get('metadata', {}),
                    user_id=os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
                )

                # Cache the signal
                signal_hash = self._generate_signal_hash(signal_data['content'])
                self.signal_cache[signal_hash] = datetime.now(timezone.utc)

                # Publish to Redis (if available)
                try:
                    await self.redis.publish('lyco:signal_created', {
                        'signal_id': str(signal_id),
                        'source': 'calendar',
                        'timestamp': datetime.now().isoformat()
                    })
                except:
                    pass  # Redis not critical for core function

                created_count += 1

            logger.info(f"Created {created_count} calendar signals from {len(all_signals)} candidates")

        except Exception as e:
            logger.error(f"Error capturing calendar signals: {e}")

    async def process_signals(self):
        """Process captured signals into tasks"""
        try:
            results = await self.engine.process_all_signals()

            if results['processed'] > 0:
                logger.info(f"Processed {results['processed']} signals into {results['tasks_created']} tasks")

                # Publish to Redis when new tasks are created (if available)
                if results['tasks_created'] > 0:
                    try:
                        await self.redis.publish('lyco:task_ready', {
                            'count': results['tasks_created'],
                            'timestamp': datetime.now().isoformat()
                        })
                    except:
                        pass  # Redis not critical for core function

        except Exception as e:
            logger.error(f"Error processing signals: {e}")

    async def cleanup_old_cache(self):
        """Clean up old entries from signal cache"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        old_hashes = []
        for h, t in self.signal_cache.items():
            if hasattr(t, 'tzinfo') and t.tzinfo:
                if t < cutoff_time:
                    old_hashes.append(h)
            else:
                if t.replace(tzinfo=timezone.utc) < cutoff_time:
                    old_hashes.append(h)
        for h in old_hashes:
            del self.signal_cache[h]

        if old_hashes:
            logger.debug(f"Cleaned {len(old_hashes)} old entries from cache")

    async def capture_loop(self):
        """Main capture loop - runs every 5 minutes"""
        self.running = True
        logger.info("Ambient capture started - checking every 5 minutes")

        while self.running:
            try:
                start_time = datetime.now()
                logger.info(f"Starting capture cycle at {start_time.strftime('%I:%M %p')}")

                # Capture signals from all sources
                await asyncio.gather(
                    self.capture_email_signals(),
                    self.capture_calendar_signals()
                )

                # Process signals into tasks
                await self.process_signals()

                # Clean up old cache entries
                await self.cleanup_old_cache()

                # Calculate time taken
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"Capture cycle completed in {elapsed:.1f} seconds")

                # Wait 5 minutes before next cycle
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                # Wait 1 minute on error before retrying
                await asyncio.sleep(60)

    def stop(self):
        """Stop the capture loop"""
        self.running = False
        logger.info("Ambient capture stopping...")


async def main():
    """Run the ambient capture orchestrator"""
    orchestrator = AmbientCaptureOrchestrator()

    try:
        # Subscribe to Redis channels for real-time updates (if available)
        try:
            await orchestrator.redis.subscribe_to_channels()
        except:
            logger.info("Redis not available - continuing without real-time coordination")

        # Run the main capture loop
        await orchestrator.capture_loop()

    except KeyboardInterrupt:
        orchestrator.stop()
        logger.info("Ambient capture stopped by user")
    finally:
        try:
            await orchestrator.redis.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
