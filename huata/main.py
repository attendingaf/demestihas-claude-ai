#!/usr/bin/env python3
"""
Huata Calendar Agent - Main Entry Point
Natural language calendar management for Demestihas family
"""

import os
import sys
import asyncio
import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Import Huata components
from huata import HuataCalendarAgent
from calendar_intents import CalendarIntentClassifier
from calendar_tools import GoogleCalendarAPI
from calendar_prompts import CalendarPrompts

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Huata Calendar Agent",
    description="LLM-powered natural language calendar assistant",
    version="1.0.0"
)

# Configure CORS for family access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
huata_agent: Optional[HuataCalendarAgent] = None

@app.on_event("startup")
async def startup_event():
    """Initialize Huata agent on startup"""
    global huata_agent

    try:
        # Get configuration from environment
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize Huata
        huata_agent = HuataCalendarAgent(
            anthropic_api_key=anthropic_api_key,
            redis_host=redis_host,
            redis_port=redis_port
        )

        print(f"✅ Huata Calendar Agent initialized successfully")
        print(f"   Redis: {redis_host}:{redis_port}")
        print(f"   Model: Claude 3 Haiku")

    except Exception as e:
        print(f"❌ Failed to initialize Huata: {e}")
        sys.exit(1)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "agent": "Huata Calendar Agent",
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/calendar/query")
async def process_calendar_query(request: Request):
    """
    Process natural language calendar query

    Body:
    {
        "query": "Am I free Thursday afternoon?",
        "user": "mene",
        "timezone": "America/New_York"
    }
    """
    try:
        data = await request.json()

        # Extract parameters
        query = data.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Build user context
        user_context = {
            "user": data.get("user", "mene"),
            "timezone": data.get("timezone", "America/New_York"),
            "timestamp": datetime.now().isoformat()
        }

        # Process with Huata
        start_time = datetime.now()
        response = await huata_agent.process_query(query, user_context)
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "success": True,
            "query": query,
            "response": response,
            "user": user_context["user"],
            "response_time_ms": response_time_ms
        }

    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/schedule")
async def schedule_event(request: Request):
    """
    Schedule a new calendar event

    Body:
    {
        "title": "Team Meeting",
        "start_time": "2024-08-29T14:00:00",
        "end_time": "2024-08-29T15:00:00",
        "location": "Conference Room",
        "attendees": ["cindy@demestihas.com"],
        "user": "mene"
    }
    """
    try:
        data = await request.json()

        # Build user context
        user_context = {
            "user": data.get("user", "mene"),
            "timezone": data.get("timezone", "America/New_York")
        }

        # Create event parameters
        params = {
            "title": data.get("title", "New Event"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "location": data.get("location", ""),
            "description": data.get("description", ""),
            "attendees": data.get("attendees", [])
        }

        # Schedule via Huata
        result = await huata_agent.schedule_event(params, user_context)

        return result

    except Exception as e:
        print(f"Error scheduling event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/calendar/availability")
async def check_availability(
    user: str = "mene",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Check calendar availability for specified time range"""
    try:
        # Default to today if no time specified
        if not start_time:
            start_time = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        if not end_time:
            end_time = datetime.now().replace(hour=23, minute=59, second=59).isoformat()

        user_context = {
            "user": user,
            "timezone": "America/New_York"
        }

        params = {
            "time_range": {
                "start": start_time,
                "end": end_time
            }
        }

        result = await huata_agent.check_availability(params, user_context)

        return result

    except Exception as e:
        print(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/conflicts")
async def check_conflicts(request: Request):
    """
    Check for scheduling conflicts across calendars

    Body:
    {
        "calendars": ["mene", "cindy"],
        "start_time": "2024-08-29T14:00:00",
        "end_time": "2024-08-29T15:00:00"
    }
    """
    try:
        data = await request.json()

        params = {
            "calendars": data.get("calendars", ["mene"]),
            "time_range": {
                "start": data.get("start_time"),
                "end": data.get("end_time")
            }
        }

        user_context = {
            "user": "system",
            "timezone": "America/New_York"
        }

        result = await huata_agent.check_conflicts(params, user_context)

        return result

    except Exception as e:
        print(f"Error checking conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/calendar/events")
async def list_events(
    user: str = "mene",
    date: Optional[str] = None,
    limit: int = 10
):
    """List calendar events for specified date/user"""
    try:
        # Default to today if no date specified
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        # Parse date and create time range
        event_date = datetime.fromisoformat(date)
        start_time = event_date.replace(hour=0, minute=0, second=0).isoformat()
        end_time = event_date.replace(hour=23, minute=59, second=59).isoformat()

        user_context = {
            "user": user,
            "timezone": "America/New_York"
        }

        params = {
            "time_range": {
                "start": start_time,
                "end": end_time
            },
            "limit": limit
        }

        result = await huata_agent.list_events(params, user_context)

        return result

    except Exception as e:
        print(f"Error listing events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendar/block")
async def block_time(request: Request):
    """
    Block time for deep work or tasks

    Body:
    {
        "purpose": "Deep work on Consilium",
        "start_time": "2024-08-29T14:00:00",
        "end_time": "2024-08-29T16:00:00",
        "user": "mene"
    }
    """
    try:
        data = await request.json()

        user_context = {
            "user": data.get("user", "mene"),
            "timezone": data.get("timezone", "America/New_York")
        }

        params = {
            "purpose": data.get("purpose", "Blocked Time"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "description": data.get("description", "")
        }

        result = await huata_agent.block_time(params, user_context)

        return result

    except Exception as e:
        print(f"Error blocking time: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Run Huata Calendar Agent server"""
    port = int(os.getenv("HUATA_PORT", 8003))
    host = os.getenv("HUATA_HOST", "0.0.0.0")

    print(f"""
╔══════════════════════════════════════════╗
║     🗓️  Huata Calendar Agent 🗓️          ║
║                                          ║
║  Natural Language Calendar Intelligence  ║
║         Powered by Claude Haiku          ║
╚══════════════════════════════════════════╝

Starting server on {host}:{port}...
    """)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "development") == "development",
        log_level="info"
    )

if __name__ == "__main__":
    main()
