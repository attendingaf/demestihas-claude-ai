"""
Lyco 2.0 Redis Connector
Handles PubSub for real-time signal updates
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any, Callable
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisConnector:
    """Manages Redis PubSub connections for ambient capture"""

    def __init__(self):
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = os.environ.get("REDIS_PORT", "6379")
        redis_url = os.environ.get("REDIS_URL", f"redis://{redis_host}:{redis_port}")
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = None
        self.subscriptions = {}
        self.running = False

    async def connect(self):
        """Establish Redis connection"""
        try:
            await self.client.ping()
            logger.info("Redis connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to Redis channel"""
        try:
            message_str = json.dumps(message)
            await self.client.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {message_str[:100]}...")
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")

    async def subscribe_to_channels(self):
        """Subscribe to relevant channels for signal coordination"""
        try:
            self.pubsub = self.client.pubsub()

            # Subscribe to channels from other agents
            channels = [
                'pluma:new_email',      # Email from Pluma
                'huata:new_event',      # Calendar from Huata
                'yanay:command',        # Commands from orchestrator
                'lyco:signal_created',  # Internal signal events
                'lyco:task_ready'       # Internal task events
            ]

            for channel in channels:
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to channel: {channel}")

            # Start listening in background
            asyncio.create_task(self._listen_for_messages())

        except Exception as e:
            logger.error(f"Error subscribing to channels: {e}")

    async def _listen_for_messages(self):
        """Background task to listen for Redis messages"""
        self.running = True

        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']

                    try:
                        # Parse JSON data
                        if isinstance(data, str):
                            data = json.loads(data)

                        # Handle different channel messages
                        await self._handle_message(channel, data)

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from {channel}: {data}")
                    except Exception as e:
                        logger.error(f"Error handling message from {channel}: {e}")

        except Exception as e:
            logger.error(f"Error in message listener: {e}")
        finally:
            self.running = False

    async def _handle_message(self, channel: str, data: Dict[str, Any]):
        """Handle messages from different channels"""
        logger.debug(f"Received message on {channel}: {data}")

        if channel == 'pluma:new_email':
            # Email signal from Pluma
            await self._handle_pluma_email(data)

        elif channel == 'huata:new_event':
            # Calendar event from Huata
            await self._handle_huata_event(data)

        elif channel == 'yanay:command':
            # Command from orchestrator
            await self._handle_yanay_command(data)

        elif channel == 'lyco:signal_created':
            # Internal signal created event
            logger.info(f"Signal created: {data.get('signal_id')}")

        elif channel == 'lyco:task_ready':
            # Internal task ready event
            logger.info(f"Tasks ready: {data.get('count')}")

    async def _handle_pluma_email(self, data: Dict[str, Any]):
        """Handle email signal from Pluma agent"""
        try:
            # Extract email details
            email_from = data.get('from', '')
            email_to = data.get('to', '')
            subject = data.get('subject', '')
            body = data.get('body', '')

            # Check if it's from/to our user
            work_email = os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
            home_email = os.environ.get('USER_HOME_EMAIL', 'menelaos4@gmail.com')
            user_emails = [work_email, home_email]

            is_user_email = any(
                email in email_from.lower() or email in email_to.lower()
                for email in user_emails
            )

            if is_user_email:
                # Publish for ambient capture to process
                await self.publish('lyco:email_to_process', {
                    'from': email_from,
                    'to': email_to,
                    'subject': subject,
                    'body': body,
                    'timestamp': data.get('timestamp')
                })

        except Exception as e:
            logger.error(f"Error handling Pluma email: {e}")

    async def _handle_huata_event(self, data: Dict[str, Any]):
        """Handle calendar event from Huata agent"""
        try:
            # Extract event details
            event_title = data.get('title', '')
            event_time = data.get('start_time', '')
            attendees = data.get('attendees', [])

            # Check if event needs preparation
            needs_prep = (
                'board' in event_title.lower() or
                'interview' in event_title.lower() or
                '1:1' in event_title.lower() or
                len(attendees) > 3
            )

            if needs_prep:
                # Publish for ambient capture to process
                await self.publish('lyco:calendar_to_process', {
                    'title': event_title,
                    'start_time': event_time,
                    'attendees': attendees,
                    'location': data.get('location', ''),
                    'timestamp': data.get('timestamp')
                })

        except Exception as e:
            logger.error(f"Error handling Huata event: {e}")

    async def _handle_yanay_command(self, data: Dict[str, Any]):
        """Handle command from Yanay orchestrator"""
        try:
            command = data.get('command', '')

            if command == 'refresh_signals':
                # Trigger immediate signal capture
                logger.info("Received refresh command from Yanay")
                await self.publish('lyco:trigger_capture', {'source': 'yanay'})

            elif command == 'status':
                # Report status back
                await self.publish('lyco:status_response', {
                    'agent': 'lyco',
                    'status': 'active',
                    'version': '2.0'
                })

        except Exception as e:
            logger.error(f"Error handling Yanay command: {e}")

    async def get_cached_value(self, key: str) -> Any:
        """Get cached value from Redis"""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value) if isinstance(value, str) else value
        except Exception as e:
            logger.error(f"Error getting cached value for {key}: {e}")
        return None

    async def set_cached_value(self, key: str, value: Any, ttl: int = 300):
        """Set cached value in Redis with TTL"""
        try:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            await self.client.setex(key, ttl, value_str)
        except Exception as e:
            logger.error(f"Error setting cached value for {key}: {e}")

    async def close(self):
        """Close Redis connections"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        await self.client.close()
        logger.info("Redis connections closed")
