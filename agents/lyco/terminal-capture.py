#!/usr/bin/env python3
"""
Terminal Brain Dump Capture for Lyco
Frictionless task capture through stream-of-consciousness input
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText
import websockets
from dotenv import load_dotenv

load_dotenv()

# Configuration
LYCO_API = os.getenv("LYCO_API_URL", "http://localhost:8000")
LYCO_WS = os.getenv("LYCO_WS_URL", "ws://localhost:8000/ws")
LOG_DIR = Path("/Users/menedemestihas/Projects/demestihas-ai/logs/brain-dumps")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Terminal styling
style = Style.from_dict({
    'prompt': '#00aa00 bold',
    'success': '#00ff00',
    'processing': '#ffff00',
    'error': '#ff0000',
    'info': '#0088ff'
})


class BrainDumpTerminal:
    """Terminal interface for capturing brain dump tasks"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
        self.context_buffer: List[str] = []
        self.transcript_file = None
        self.session_start = datetime.now()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def initialize(self):
        """Initialize HTTP and WebSocket connections"""
        self.session = aiohttp.ClientSession()
        await self._init_transcript()
        await self._connect_websocket()

    async def _init_transcript(self):
        """Initialize transcript file for this session"""
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.transcript_file = LOG_DIR / f"brain_dump_{timestamp}.md"

        with open(self.transcript_file, "w") as f:
            f.write(f"# Brain Dump Session - {self.session_start.isoformat()}\n\n")
            f.write(f"**Lyco API**: {LYCO_API}\n\n")
            f.write("---\n\n")

    async def _connect_websocket(self):
        """Establish WebSocket connection for real-time feedback"""
        try:
            # For now, we'll use HTTP polling since WS endpoint might not exist yet
            # This will be upgraded when Lyco supports WebSocket
            print(FormattedText([('class:info', '📡 Connecting to Lyco...')]))
            self.ws_connection = None  # Placeholder for future WS support
            return True
        except Exception as e:
            print(FormattedText([('class:error', f'⚠️  WebSocket unavailable, using HTTP mode')]))
            return False

    async def capture_task(self, input_text: str) -> Dict[str, Any]:
        """Send task to Lyco's capture endpoint"""
        try:
            # Build context from recent buffer
            context = "\n".join(self.context_buffer[-5:]) if self.context_buffer else ""

            payload = {
                "text": input_text,
                "context": context,
                "source": "terminal_brain_dump",
                "timestamp": datetime.now().isoformat()
            }

            async with self.session.post(
                f"{LYCO_API}/api/capture",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # Fallback: Try to create a basic task
                    async with self.session.post(
                        f"{LYCO_API}/api/tasks",
                        json={
                            "title": input_text,
                            "context": context,
                            "source": "terminal_brain_dump"
                        }
                    ) as fallback_response:
                        if fallback_response.status in [200, 201]:
                            return await fallback_response.json()
                        else:
                            return {
                                "error": f"API returned {response.status}",
                                "text": input_text
                            }

        except aiohttp.ClientError as e:
            return {"error": f"Connection failed: {str(e)}", "text": input_text}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "text": input_text}

    def log_to_transcript(self, input_text: str, response: Dict[str, Any]):
        """Log interaction to transcript file"""
        with open(self.transcript_file, "a") as f:
            f.write(f"**[{datetime.now().strftime('%H:%M:%S')}]** {input_text}\n")

            if "error" in response:
                f.write(f"  ❌ Error: {response['error']}\n")
            elif "task" in response:
                task = response["task"]
                f.write(f"  ✅ Captured: {task.get('title', 'Untitled')}\n")
                if task.get('energy_level'):
                    f.write(f"     Energy: {task['energy_level']}\n")
                if task.get('estimated_duration'):
                    f.write(f"     Duration: {task['estimated_duration']} min\n")
            f.write("\n")

    async def handle_command(self, command: str) -> bool:
        """Handle special commands"""
        if command == "/review":
            print(FormattedText([('class:info', f'🌐 Opening review dashboard: {LYCO_API}/review')]))
            os.system(f"open {LYCO_API}/review")
            return True

        elif command == "/clear":
            self.context_buffer.clear()
            print(FormattedText([('class:success', '🧹 Context cleared')]))
            return True

        elif command == "/status":
            try:
                async with self.session.get(f"{LYCO_API}/api/status") as response:
                    if response.status == 200:
                        status = await response.json()
                        print(FormattedText([
                            ('class:info', f"📊 Status:\n"),
                            ('class:info', f"   Pending tasks: {status.get('pending_count', 0)}\n"),
                            ('class:info', f"   Energy level: {status.get('current_energy', 'unknown')}\n"),
                            ('class:info', f"   System health: {status.get('system_health', 'unknown')}")
                        ]))
            except Exception as e:
                print(FormattedText([('class:error', f'❌ Could not fetch status: {e}')]))
            return True

        elif command == "/help":
            print(FormattedText([
                ('class:info', "📚 Commands:\n"),
                ('class:info', "   /review - Open review dashboard\n"),
                ('class:info', "   /clear - Clear context buffer\n"),
                ('class:info', "   /status - Show system status\n"),
                ('class:info', "   /exit - Exit terminal\n"),
                ('class:info', "   /help - Show this help")
            ]))
            return True

        elif command == "/exit":
            return False

        return True

    async def run(self):
        """Main terminal loop"""
        print(FormattedText([
            ('class:success', "🧠 Lyco Brain Dump Terminal\n"),
            ('class:info', f"Connected to: {LYCO_API}\n"),
            ('class:info', f"Transcript: {self.transcript_file}\n"),
            ('class:info', "Type /help for commands, /exit to quit\n"),
            ('class:info', "─" * 50)
        ]))

        history = FileHistory(str(LOG_DIR / ".terminal_history"))

        while True:
            try:
                # Get input with history and auto-suggestions
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: prompt(
                        FormattedText([('class:prompt', '💭 ')]),
                        history=history,
                        auto_suggest=AutoSuggestFromHistory(),
                        style=style
                    )
                )

                # Skip empty lines
                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if not await self.handle_command(user_input.strip()):
                        break
                    continue

                # Show processing indicator
                print(FormattedText([('class:processing', '⏳ Processing...')]), end='\r')

                # Capture the task
                response = await self.capture_task(user_input)

                # Clear processing indicator and show result
                print(" " * 20, end='\r')  # Clear line

                if "error" in response:
                    print(FormattedText([('class:error', f"❌ {response['error']}")]))
                else:
                    task = response.get("task", {})
                    title = task.get("title", user_input[:50])
                    print(FormattedText([
                        ('class:success', f"✅ Captured: {title}")
                    ]))

                    # Show additional details if available
                    if task.get("energy_level"):
                        print(FormattedText([
                            ('class:info', f"   ⚡ Energy: {task['energy_level']}")
                        ]))
                    if task.get("estimated_duration"):
                        print(FormattedText([
                            ('class:info', f"   ⏱️  Duration: {task['estimated_duration']} min")
                        ]))

                # Update context buffer
                self.context_buffer.append(user_input)
                if len(self.context_buffer) > 10:
                    self.context_buffer.pop(0)

                # Log to transcript
                self.log_to_transcript(user_input, response)

            except KeyboardInterrupt:
                print(FormattedText([('class:info', '\n👋 Goodbye!')]))
                break
            except EOFError:
                break
            except Exception as e:
                print(FormattedText([('class:error', f"❌ Error: {e}")]))

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.ws_connection:
            await self.ws_connection.close()

        # Final transcript summary
        if self.transcript_file:
            with open(self.transcript_file, "a") as f:
                f.write("\n---\n\n")
                f.write(f"**Session ended**: {datetime.now().isoformat()}\n")
                f.write(f"**Duration**: {datetime.now() - self.session_start}\n")
                f.write(f"**Tasks captured**: {len(self.context_buffer)}\n")

        print(FormattedText([
            ('class:info', f"\n📝 Transcript saved: {self.transcript_file}")
        ]))


async def main():
    """Main entry point"""
    terminal = BrainDumpTerminal()

    try:
        await terminal.initialize()
        await terminal.run()
    finally:
        await terminal.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
