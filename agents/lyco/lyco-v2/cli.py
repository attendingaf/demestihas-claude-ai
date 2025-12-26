#!/usr/bin/env python3
"""
Lyco 2.0 CLI - For testing the data pipeline
"""
import asyncio
import click
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

from src.database import DatabaseManager
from src.processor import IntelligenceEngine
from src.models import TaskSignal


@click.group()
def cli():
    """Lyco 2.0 Pipeline Testing"""
    pass


@cli.command()
@click.argument('text')
@click.option('--source', default='manual', help='Source of the signal')
def signal(text, source):
    """Create a test signal"""
    async def create():
        db = DatabaseManager()
        signal_id = await db.create_signal(source, text)
        click.echo(f"✓ Signal created: {signal_id}")

    asyncio.run(create())


@cli.command()
def process():
    """Process pending signals"""
    async def process_signals():
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if not anthropic_key:
            click.echo("Error: ANTHROPIC_API_KEY not set")
            return

        engine = IntelligenceEngine(anthropic_key, openai_key)
        results = await engine.process_all_signals()

        click.echo(f"✓ Processed {results['processed']} signals")
        click.echo(f"✓ Created {results['tasks_created']} tasks")

    asyncio.run(process_signals())


@cli.command()
@click.option('--energy', help='Filter by energy level')
def next(energy):
    """Get next task"""
    async def get_task():
        db = DatabaseManager()

        if energy:
            task = await db.get_next_task_by_energy(energy)
        else:
            task = await db.get_next_task()

        if task:
            click.echo(f"\n📋 TASK: {task.content}")
            click.echo(f"▶️  NEXT: {task.next_action}")
            click.echo(f"⚡ Energy: {task.energy_level} | ⏱️  {task.time_estimate} min")
            if task.context_required:
                click.echo(f"📍 Context: {', '.join(task.context_required)}")
        else:
            click.echo("✨ No tasks pending - you're all clear!")

    asyncio.run(get_task())


@cli.command()
@click.argument('task_id')
def complete(task_id):
    """Mark task as completed"""
    async def mark_complete():
        db = DatabaseManager()
        await db.complete_task(task_id)
        click.echo(f"✅ Task {task_id} completed!")

    asyncio.run(mark_complete())


@cli.command()
@click.argument('task_id')
@click.option('--reason', prompt='Why skip?', help='Reason for skipping')
def skip(task_id, reason):
    """Skip task with reason"""
    async def mark_skip():
        db = DatabaseManager()
        await db.skip_task(task_id, reason)
        click.echo(f"⏭️  Task {task_id} skipped: {reason}")

    asyncio.run(mark_skip())


@cli.command()
def status():
    """Show system status"""
    async def show_status():
        db = DatabaseManager()
        pending_count = await db.get_pending_tasks_count()

        click.echo("\n📊 Lyco 2.0 Status")
        click.echo(f"📋 Pending tasks: {pending_count}")

        # Get current energy level
        current_hour = datetime.now().hour
        if 9 <= current_hour < 11:
            energy = "high"
        elif 14 <= current_hour < 16:
            energy = "medium"
        else:
            energy = "low"

        click.echo(f"⚡ Current energy: {energy}")
        click.echo(f"🕐 Time: {datetime.now().strftime('%I:%M %p')}")

    asyncio.run(show_status())


@cli.command()
def test():
    """Run test signals through the pipeline"""
    test_signals = [
        "I'll send you the report by Friday",
        "Need to review the Q3 budget presentation",
        "Schedule meeting with Dr. Smith about patient outcomes",
        "Just checking in, how are things going?",
        "Remember to submit expense reports",
        "Can you help me understand the new policy?",
        "I'll follow up with the vendor tomorrow morning",
    ]

    async def run_tests():
        db = DatabaseManager()
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if not anthropic_key:
            click.echo("Error: ANTHROPIC_API_KEY not set")
            return

        engine = IntelligenceEngine(anthropic_key)

        click.echo("Running test signals...\n")

        for signal_text in test_signals:
            click.echo(f"📨 Signal: {signal_text}")

            # Create signal
            signal_id = await db.create_signal('test', signal_text)

            # Get the signal object
            signal = TaskSignal(
                id=signal_id,
                source='test',
                raw_content=signal_text
            )

            # Process it
            result = await engine.process_signal_with_llm(signal)

            if result and result.is_task:
                click.echo(f"  ✅ TASK: {result.content}")
                click.echo(f"  ▶️  ACTION: {result.next_action}")
            else:
                click.echo(f"  ❌ Not a task")

            click.echo()

    asyncio.run(run_tests())


if __name__ == '__main__':
    cli()
