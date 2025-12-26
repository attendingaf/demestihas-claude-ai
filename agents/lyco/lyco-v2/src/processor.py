"""
Lyco 2.0 Core Intelligence Engine
LLM-first processing pipeline for semantic understanding
"""
import json
import asyncio
import os
from datetime import datetime, time
from typing import Optional, Dict, Any
import logging

from anthropic import AsyncAnthropic
import openai
from pydantic import ValidationError

from .models import TaskSignal, Task, ProcessedTask
from .database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """Core LLM-powered task processor with adaptive prompts"""

    def __init__(self, anthropic_key: str, openai_key: str = None):
        self.anthropic = AsyncAnthropic(api_key=anthropic_key)
        if openai_key:
            openai.api_key = openai_key
        self.db = DatabaseManager()

        # Prompt versioning
        self.current_prompts = {}
        self.performance_tracking = True

    async def process_signal_with_llm(self, signal: TaskSignal) -> Optional[ProcessedTask]:
        """
        Process a signal using LLM to extract actionable tasks
        Uses adaptive prompts that improve over time
        """
        start_time = datetime.now()

        # Get active prompt version or use default
        prompt = await self._get_active_prompt("task_processing")

        # Get user context
        work_email = os.environ.get('USER_WORK_EMAIL', 'mene@beltlineconsulting.co')
        home_email = os.environ.get('USER_HOME_EMAIL', '')
        user_emails = [work_email]
        if home_email:
            user_emails.append(home_email)

        # Format prompt with signal data
        formatted_prompt = prompt.format(
            source=signal.source,
            content=signal.raw_content,
            user_emails=', '.join(user_emails),
            current_time=datetime.now().strftime('%I:%M %p')
        )

        try:
            # Try Claude first
            response = await self._call_claude(formatted_prompt)
            if response:
                result = self._parse_llm_response(response)

                # Track performance
                if self.performance_tracking and result:
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000
                    await self._track_processing_performance(
                        signal, result, processing_time, "claude"
                    )

                return result

        except Exception as e:
            logger.warning(f"Claude API error: {e}")

            # Fallback to GPT-4 if Claude fails
            try:
                response = await self._call_gpt4(formatted_prompt)
                if response:
                    result = self._parse_llm_response(response)

                    # Track performance
                    if self.performance_tracking and result:
                        processing_time = (datetime.now() - start_time).total_seconds() * 1000
                        await self._track_processing_performance(
                            signal, result, processing_time, "gpt4"
                        )

                    return result
            except Exception as e:
                logger.error(f"Both LLM APIs failed: {e}")
                return None

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API"""
        response = await self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def _call_gpt4(self, prompt: str) -> str:
        """Call GPT-4 API as fallback"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=openai.api_key)
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content

    def _parse_llm_response(self, response: str) -> Optional[ProcessedTask]:
        """Parse LLM response into ProcessedTask"""
        try:
            # Clean response if needed
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)
            return ProcessedTask(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def _determine_energy_level(self, content: str = None) -> str:
        """Determine energy level based on time and content"""
        current_hour = datetime.now().hour

        # Content-based hints override time-based defaults
        if content:
            content_lower = content.lower()

            # High energy keywords
            high_energy_keywords = ['strategic', 'strategy', 'planning', 'design', 'create',
                                   'build', 'architect', 'analyze', 'research', 'proposal',
                                   'presentation', 'board', 'investor', 'vision']
            if any(keyword in content_lower for keyword in high_energy_keywords):
                return "high"

            # Medium energy keywords
            medium_energy_keywords = ['review', 'respond', 'meeting', 'email', 'call',
                                     'discuss', 'sync', 'check-in', 'follow up', 'feedback']
            if any(keyword in content_lower for keyword in medium_energy_keywords):
                return "medium"

            # Low energy keywords
            low_energy_keywords = ['read', 'organize', 'file', 'sort', 'clean', 'archive',
                                  'document', 'note', 'summary', 'list']
            if any(keyword in content_lower for keyword in low_energy_keywords):
                return "low"

        # Time-based defaults
        if 9 <= current_hour < 11:
            return "high"
        elif 14 <= current_hour < 16:
            return "medium"
        else:
            return "low"

    async def process_all_signals(self) -> Dict[str, int]:
        """Process all pending signals"""
        unprocessed = await self.db.get_unprocessed_signals()
        processed_count = 0
        task_count = 0

        for signal in unprocessed:
            result = await self.process_signal_with_llm(signal)

            if result and result.is_task:
                # Create task from processed signal
                task = Task(
                    signal_id=signal.id,
                    content=result.content,
                    next_action=result.next_action,
                    energy_level=result.energy_level or self._determine_energy_level(result.content),
                    time_estimate=result.time_estimate or 15,
                    context_required=result.context_required or ["computer"],
                    metadata={"confidence": result.confidence}
                )

                await self.db.create_task(task)
                task_count += 1

            # Mark signal as processed
            await self.db.mark_signal_processed(signal.id)
            processed_count += 1

        return {
            "processed": processed_count,
            "tasks_created": task_count
        }

    async def get_next_task(self) -> Optional[Task]:
        """
        Get the next task optimized for current energy level
        """
        current_energy = self._determine_energy_level()

        # Try to get task matching current energy
        task = await self.db.get_next_task_by_energy(current_energy)

        # Fallback to any task if no energy match
        if not task:
            task = await self.db.get_next_task()

        return task

    async def _get_active_prompt(self, prompt_type: str) -> str:
        """Get active prompt version or return default"""
        if prompt_type in self.current_prompts:
            return self.current_prompts[prompt_type]

        try:
            # Load from database
            result = await self.db.fetch_one("""
                SELECT prompt_content FROM prompt_versions
                WHERE prompt_type = $1 AND is_active = true
                ORDER BY activated_at DESC LIMIT 1
            """, prompt_type)

            if result:
                prompt = result["prompt_content"]
                self.current_prompts[prompt_type] = prompt
                return prompt
        except Exception as e:
            logger.warning(f"Failed to load prompt version: {e}")

        # Return default prompt
        return self._get_default_prompt(prompt_type)

    def _get_default_prompt(self, prompt_type: str) -> str:
        """Get default prompt for type"""
        if prompt_type == "task_processing":
            return """
You are an executive assistant AI designed as a cognitive prosthetic.

Analyze this signal from {source}: {content}

Context:
- User emails: {user_emails} (physician executive, CMO-level)
- High energy: 9-11am (strategy, analysis, creation)
- Medium energy: 2-4pm (email, reviews, meetings)
- Low energy: after 4pm (reading, organizing)
- ADHD-optimized: tasks must be 15-minute chunks maximum
- Current time: {current_time}

If this contains a commitment BY the user or request OF the user, return JSON:
{{
  "is_task": true,
  "content": "Human-readable task description",
  "next_action": "Single physical micro-step to begin (e.g., 'Open Gmail and type subject line')",
  "energy_level": "high|medium|low",
  "time_estimate": 15,
  "context_required": ["computer", "phone", "quiet"],
  "confidence": 0.0-1.0
}}

If no actionable task found, return: {{"is_task": false}}

Return ONLY valid JSON, no additional text.
"""
        return "Default prompt not found for type: " + prompt_type

    async def _track_processing_performance(self, signal: TaskSignal,
                                         result: ProcessedTask,
                                         processing_time_ms: float,
                                         provider: str):
        """Track processing performance for adaptive learning"""
        try:
            # Store performance metrics
            await self.db.execute("""
                INSERT INTO performance_metrics
                (metric_type, metric_value, measurement_time, context)
                VALUES ($1, $2, NOW(), $3)
            """,
            "processing_time_ms",
            processing_time_ms,
            json.dumps({
                "provider": provider,
                "signal_source": signal.source,
                "task_detected": result.is_task,
                "confidence": result.confidence
            })
            )

            # Update task with performance data if it becomes a task
            if result.is_task:
                current_prompt_version = await self._get_current_prompt_version("task_processing")
                # This will be used when the task is created
                result.metadata = result.metadata or {}
                result.metadata.update({
                    "prompt_version": current_prompt_version,
                    "processing_time_ms": processing_time_ms,
                    "llm_provider": provider
                })

        except Exception as e:
            logger.error(f"Failed to track processing performance: {e}")

    async def _get_current_prompt_version(self, prompt_type: str) -> str:
        """Get current active prompt version name"""
        try:
            result = await self.db.fetch_one("""
                SELECT version_name FROM prompt_versions
                WHERE prompt_type = $1 AND is_active = true
                ORDER BY activated_at DESC LIMIT 1
            """, prompt_type)

            return result["version_name"] if result else "default"
        except:
            return "default"

    async def reload_prompts(self):
        """Reload prompts from database (called when prompts are updated)"""
        self.current_prompts.clear()
        logger.info("Prompts reloaded from database")
