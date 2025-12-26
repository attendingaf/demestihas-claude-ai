"""
Statefulness Extensions for DemestiChat
Adds: Conversation persistence, temporal queries, contradiction detection
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import re
import os
import json
import requests

try:
    import tiktoken
except ImportError:
    tiktoken = None
    logging.warning("tiktoken not installed - token counting will be disabled")

logger = logging.getLogger(__name__)


from postgres_client import get_postgres_client

class ConversationManager:
    """Manages conversation storage and retrieval in PostgreSQL using PostgresClient"""

    def __init__(self):
        self.client = get_postgres_client()
        self.default_model = "gpt-4o"  # For token counting
        self.summary_model = "gpt-4o-mini"  # Cheap model for summarization

    def store_conversation(
        self,
        user_id: str,
        session_id: str,
        message: str,
        response: str,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Store conversation in PostgreSQL (as separate messages)"""
        if not self.client:
            return False

        try:
            # Store user message
            self.client.store_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=message
            )
            
            # Store assistant response
            self.client.store_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response,
                routing_agent=agent_type,
                confidence_score=metadata.get("confidence_score") if metadata else None
            )
            
            logger.info(f"Stored conversation in session {session_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return False

    def get_conversation_history(
        self,
        user_id: str,
        time_filter: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history with optional temporal filtering"""
        if not self.client:
            return []

        try:
            with self.client.get_cursor() as cursor:
                query = """
                    SELECT role, content, timestamp, routing_agent, session_id
                    FROM messages
                    WHERE user_id = %s
                """
                params = [user_id]

                # Add temporal filter
                if time_filter:
                    time_filter_lower = time_filter.lower()
                    if "yesterday" in time_filter_lower:
                        query += " AND timestamp >= NOW() - INTERVAL '1 day' AND timestamp < NOW() - INTERVAL '0 days'"
                    elif "today" in time_filter_lower:
                        query += " AND timestamp >= CURRENT_DATE"
                    elif "week" in time_filter_lower:
                        query += " AND timestamp >= NOW() - INTERVAL '7 days'"
                    elif "month" in time_filter_lower:
                        query += " AND timestamp >= NOW() - INTERVAL '30 days'"

                # Add session filter
                if session_id:
                    query += " AND session_id = %s"
                    params.append(session_id)

                query += " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit * 2) # Fetch more because we have separate messages now

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {e}")
            return []

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            model: Model name (default: self.default_model)
        
        Returns:
            Token count (0 if tiktoken not available)
        """
        if not tiktoken:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
        
        try:
            model = model or self.default_model
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using character estimate")
            return len(text) // 4

    def summarize_conversation_chunk(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        """
        Summarize a chunk of conversation messages using LLM.
        
        Args:
            messages: List of message dicts with role/content
            model: LLM model for summarization (default: gpt-4o-mini)
        
        Returns:
            Summary string
        """
        if not messages:
            return ""
        
        model = model or self.summary_model
        
        # Format messages for summarization
        conversation_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages]
        )
        
        summary_prompt = f"""Summarize the following conversation concisely, preserving key facts, decisions, and context. Focus on:
- Important information shared
- Decisions made
- Action items or commitments
- Key topics discussed

Conversation:
{conversation_text}

Concise Summary:"""
        
        try:
            # Call OpenAI API for summarization
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": summary_prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result["choices"][0]["message"]["content"]
                logger.info(
                    f"Summarized {len(messages)} messages into "
                    f"{self.count_tokens(summary)} tokens"
                )
                return summary
            else:
                logger.error(
                    f"Summarization API failed: {response.status_code} - {response.text}"
                )
                return "[Summary unavailable - API error]"
        
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "[Summary unavailable - error occurred]"

    def generate_session_title(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
        """
        Generate a short 3-5 word title for the session.
        """
        if not messages:
            return "New Chat"

        model = model or self.summary_model
        
        # Format messages
        conversation_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages[:5]] # Use first 5 messages
        )

        prompt = f"""Generate a very short, concise title (3-5 words max) for this conversation. 
Do not use quotes. Do not use "Chat about...". Just the topic.

Conversation:
{conversation_text}

Title:"""

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 20,
                },
                timeout=10,
            )

            if response.status_code == 200:
                title = response.json()["choices"][0]["message"]["content"].strip()
                # Remove quotes if present
                title = title.replace('"', '').replace("'", "")
                return title
            else:
                return "New Chat"
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return "New Chat"

    def update_session_summary(self, session_id: str, summary: str) -> bool:
        """Update session summary in database"""
        if not self.client:
            return False
        try:
            self.client.update_session_summary(session_id, summary)
            return True
        except Exception as e:
            logger.error(f"Failed to update session summary: {e}")
            return False

    def trim_history(
        self,
        user_id: str,
        session_id: str,
        token_limit: int = 2500,
        keep_recent: int = 10,
    ) -> Dict[str, Any]:
        """
        Trim conversation history using summary buffer pattern.
        
        Logic:
        1. Fetch full conversation history
        2. Count total tokens
        3. If > token_limit:
           - Keep last `keep_recent` messages raw
           - Summarize older messages
           - Return {summary: str, recent_messages: List}
        4. Else: Return all messages raw
        
        Args:
            user_id: User ID
            session_id: Session ID
            token_limit: Max tokens before summarization (default: 2500)
            keep_recent: Number of recent messages to keep raw (default: 10)
        
        Returns:
            {
                "summary": str or None,
                "recent_messages": List[Dict],
                "total_tokens": int,
                "summarized": bool,
                "message_count": int
            }
        """
        # Fetch all messages for session (reverse order - newest first)
        all_messages = self.get_conversation_history(
            user_id=user_id, session_id=session_id, limit=1000
        )
        
        if not all_messages:
            return {
                "summary": None,
                "recent_messages": [],
                "total_tokens": 0,
                "summarized": False,
                "message_count": 0,
            }
        
        # Reverse to chronological order (oldest first)
        all_messages = list(reversed(all_messages))
        
        # Count total tokens
        total_text = " ".join([msg.get("content", "") for msg in all_messages])
        total_tokens = self.count_tokens(total_text)
        
        logger.info(
            f"Conversation history: {len(all_messages)} messages, {total_tokens} tokens"

        )
        
        # Check if summarization needed
        if total_tokens <= token_limit:
            return {
                "summary": None,
                "recent_messages": list(reversed(all_messages)),  # Back to newest first
                "total_tokens": total_tokens,
                "summarized": False,
                "message_count": len(all_messages),
            }
        
        # Split into old (to summarize) and recent (keep raw)
        if len(all_messages) <= keep_recent:
            # Not enough messages to split, return all
            return {
                "summary": None,
                "recent_messages": list(reversed(all_messages)),
                "total_tokens": total_tokens,
                "summarized": False,
                "message_count": len(all_messages),
            }
        
        # Split: older messages to summarize, recent to keep
        split_index = len(all_messages) - keep_recent
        old_messages = all_messages[:split_index]
        recent_messages = all_messages[split_index:]
        
        # Summarize old messages
        summary = self.summarize_conversation_chunk(old_messages)
        
        # Calculate final token count
        recent_text = " ".join([msg.get("content", "") for msg in recent_messages])
        final_tokens = self.count_tokens(summary) + self.count_tokens(recent_text)
        
        logger.info(
            f"✅ Summary buffer: {len(old_messages)} messages summarized, "
            f"{len(recent_messages)} kept raw. "
            f"Tokens: {total_tokens} → {final_tokens} "
            f"({int((1 - final_tokens/total_tokens) * 100)}% reduction)"
        )
        
        return {
            "summary": summary,
            "recent_messages": list(reversed(recent_messages)),  # Newest first for display
            "total_tokens": final_tokens,
            "summarized": True,
            "message_count": len(all_messages),
            "old_message_count": len(old_messages),
        }

    def get_conversation_count(self, user_id: str) -> int:
        """Get total conversation count for a user"""
        if not self.client:
            return 0

        try:
            with self.client.get_cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM conversation_sessions WHERE user_id = %s", (user_id,)
                )
                result = cursor.fetchone()
                return result['count'] if result else 0
        except:
            return 0

    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent sessions for a user"""
        if not self.client:
            return []
        
        try:
            return self.client.get_recent_sessions(user_id, limit)
        except Exception as e:
            logger.error(f"Failed to retrieve user sessions: {e}")
            return []


class TemporalParser:
    """Parse temporal references in natural language queries"""

    @staticmethod
    def extract_time_reference(query: str) -> Dict[str, Any]:
        """Extract temporal information from query"""
        query_lower = query.lower()
        now = datetime.now()

        temporal_patterns = {
            "yesterday": {
                "start": (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                "end": (now - timedelta(days=1)).replace(hour=23, minute=59, second=59),
                "marker": "yesterday",
            },
            "today": {
                "start": now.replace(hour=0, minute=0, second=0),
                "end": now,
                "marker": "today",
            },
            "last week": {
                "start": now - timedelta(days=7),
                "end": now,
                "marker": "last week",
            },
            "this week": {
                "start": now - timedelta(days=now.weekday()),
                "end": now,
                "marker": "this week",
            },
            "last month": {
                "start": now - timedelta(days=30),
                "end": now,
                "marker": "last month",
            },
        }

        for pattern, info in temporal_patterns.items():
            if pattern in query_lower:
                return {
                    "has_temporal": True,
                    "marker": info["marker"],
                    "start": info["start"],
                    "end": info["end"],
                    "raw_query": query,
                }

        return {"has_temporal": False, "marker": None}

    @staticmethod
    def format_temporal_context(messages: List[Dict]) -> str:
        """Format past messages for context"""
        if not messages:
            return "No previous conversations found for that time period."

        context = f"Found {len(messages)} messages:\n\n"
        # Sort by timestamp asc for readability
        sorted_msgs = sorted(messages, key=lambda x: x['timestamp'])
        
        for msg in sorted_msgs:
            timestamp = msg.get("timestamp", "Unknown time")
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")[:200]
            context += f"[{timestamp}] {role}: {content}\n"

        return context


class ContradictionDetector:
    """Detect and handle contradictions in knowledge"""

    def __init__(self, falkordb_manager):
        self.falkordb = falkordb_manager

        # Define predicates that should be unique (only one value allowed)
        self.exclusive_predicates = {
            "LIVES_IN",
            "WORKS_AT",
            "IS",
            "HAS_AGE",
            "IS_MARRIED_TO",
            "IS_EMPLOYED_BY",
            "HAS_PHONE",
            "HAS_EMAIL",
            "STUDIES_AT",
        }

    async def check_contradiction(
        self, user_id: str, new_fact: Dict[str, str]
    ) -> Optional[Dict]:
        """Check if new fact contradicts existing knowledge"""

        subject = new_fact.get("subject", "")
        predicate = new_fact.get("predicate", "")
        new_object = new_fact.get("object", "")

        # Only check for exclusive predicates
        if predicate not in self.exclusive_predicates:
            return None

        try:
            # Query for existing facts with same subject and predicate
            query = f"""
            MATCH (u:User {{id: '{user_id}'}})-[:KNOWS_ABOUT]->(e:Entity {{name: '{subject}'}})
            -[r:{predicate}]->(obj:Entity)
            RETURN obj.name AS existing_value,
                   r.timestamp AS when,
                   r.confidence AS confidence
            LIMIT 1
            """

            result = await self.falkordb.execute_query(query, readonly=True)

            if result and len(result) > 0:
                existing_value = result[0][0] if len(result[0]) > 0 else None

                # Check if values differ
                if existing_value and existing_value != new_object:
                    return {
                        "detected": True,
                        "subject": subject,
                        "predicate": predicate,
                        "old_value": existing_value,
                        "new_value": new_object,
                        "severity": self._calculate_severity(predicate),
                        "action": "update",  # Default action
                    }

            return None

        except Exception as e:
            logger.error(f"Contradiction check failed: {e}")
            return None

    def _calculate_severity(self, predicate: str) -> str:
        """Determine contradiction severity"""
        critical_predicates = {"HAS_ALLERGY", "HAS_CONDITION", "TAKES_MEDICATION"}

        if predicate in critical_predicates:
            return "critical"
        elif predicate in {"HAS_AGE"}:
            return "normal"  # Age changes are expected
        else:
            return "moderate"

    def format_contradiction_message(self, contradiction: Dict) -> str:
        """Format contradiction for user notification"""
        severity = contradiction.get("severity", "moderate")
        subject = contradiction.get("subject")
        predicate = contradiction.get("predicate", "").replace("_", " ").lower()
        old_value = contradiction.get("old_value")
        new_value = contradiction.get("new_value")

        if severity == "critical":
            return f"⚠️ **Important Update Detected**: I previously recorded that {subject} {predicate} {old_value}, but you now mentioned {new_value}. I've updated this information."
        elif severity == "normal":
            return (
                f"Updated: {subject} {predicate} {new_value} (previously: {old_value})"
            )
        else:
            return f"Note: I've updated that {subject} {predicate} {new_value}"


# Global instances (to be initialized in main.py)
conversation_manager = None
temporal_parser = TemporalParser()
contradiction_detector = None


def initialize_statefulness_extensions(falkordb_mgr):
    """Initialize all statefulness components"""
    global conversation_manager, contradiction_detector

    try:
        conversation_manager = ConversationManager()
        contradiction_detector = ContradictionDetector(falkordb_mgr)
        logger.info("✅ Statefulness extensions initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize statefulness extensions: {e}")
        return False

def get_conversation_manager():
    """Get the global conversation manager instance"""
    global conversation_manager
    return conversation_manager
