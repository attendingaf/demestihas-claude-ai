"""
Huata Calendar Agent - FastAPI Application
Provides HTTP endpoints for calendar management and conflict detection
"""

import os
import sys
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import redis.asyncio as redis

# Import Huata components
from huata import HuataCalendarAgent
from conflict_detector import ConflictDetector, ConflictSeverity
from calendar_intents import CalendarIntentClassifier

# Try to import OAuth version first, fall back to service account if needed
try:
    from calendar_tools_oauth import GoogleCalendarOAuth
    print("✅ Using OAuth authentication for calendar access")
    USING_OAUTH = True
    calendar_api = GoogleCalendarOAuth()
except ImportError:
    print("⚠️  OAuth module not found, falling back to service account")
    from calendar_tools import GoogleCalendarAPI
    USING_OAUTH = False
    calendar_api = GoogleCalendarAPI(credentials_path='/app/credentials/huata-service-account.json')

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Huata Calendar Agent",
    description="LLM-powered natural language calendar assistant with conflict detection",
    version="2.0.0"
)

# Configure CORS for family access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
huata_agent: Optional[HuataCalendarAgent] = None
conflict_detector: Optional[ConflictDetector] = None
redis_client: Optional[redis.Redis] = None

@app.on_event("startup")
async def startup_event():
    """Initialize Huata agent and conflict detector on startup"""
    global huata_agent, conflict_detector, redis_client

    try:
        # Initialize Redis
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))

        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            await redis_client.ping()
            print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e} (caching disabled)")
            redis_client = None

        # Initialize Huata agent
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        huata_agent = HuataCalendarAgent(
            anthropic_api_key=anthropic_key,
            redis_host=redis_host,
            redis_port=redis_port
        )

        # Initialize conflict detector
        conflict_detector = ConflictDetector(redis_client=redis_client)

        print("✅ Huata Calendar Agent initialized successfully")

    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_status = "connected"
        if redis_client:
            try:
                await redis_client.ping()
            except:
                redis_status = "disconnected"
        else:
            redis_status = "not configured"

        # Check calendar API
        calendar_status = "ready" if calendar_api else "not initialized"

        return {
            "status": "healthy",
            "components": {
                "huata_agent": "ready" if huata_agent else "not initialized",
                "conflict_detector": "ready" if conflict_detector else "not initialized",
                "redis": redis_status,
                "calendar_api": calendar_status
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/query")
async def process_query(request: Request):
    """Process natural language calendar query"""
    try:
        data = await request.json()
        query = data.get("query")
        user_context = data.get("context", {})

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        if not huata_agent:
            raise HTTPException(status_code=503, detail="Huata agent not initialized")

        response = await huata_agent.process_query(query, user_context)

        return {
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conflicts")
async def detect_conflicts(
    days: int = Query(7, description="Number of days to check for conflicts"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
):
    """
    Detect calendar conflicts across all family calendars

    Args:
        days: Number of days ahead to check (default 7)
        start_date: Optional specific start date
        end_date: Optional specific end date

    Returns:
        Conflict analysis with severity levels and recommendations
    """
    try:
        if not conflict_detector:
            raise HTTPException(status_code=503, detail="Conflict detector not initialized")

        # Determine date range
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now()

        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = start + timedelta(days=days)

        # Fetch events from all calendars
        all_events = []
        calendar_ids = [
            "primary",  # Mene's work calendar
            "mene.personal@gmail.com",  # Mene's personal
            "cindy.work@hospital.org",  # Cindy's work
            "family@demestihas.com",  # Family calendar
            "persy.school@edu.org",  # Persy's school
            "appointments@demestihas.com"  # Shared appointments
        ]

        for calendar_id in calendar_ids:
            try:
                # Fetch events from calendar
                if USING_OAUTH:
                    events = await calendar_api.get_events_async(
                        calendar_id=calendar_id,
                        time_min=start.isoformat() + 'Z',
                        time_max=end.isoformat() + 'Z'
                    )
                else:
                    events = calendar_api.get_events(
                        calendar_id=calendar_id,
                        time_min=start.isoformat() + 'Z',
                        time_max=end.isoformat() + 'Z'
                    )

                # Add calendar_id to each event for tracking
                for event in events.get('items', []):
                    if 'start' in event and 'dateTime' in event['start']:
                        event['calendar_id'] = calendar_id
                        event['start'] = event['start']['dateTime']
                        event['end'] = event['end']['dateTime'] if 'end' in event else event['start']
                        all_events.append(event)

            except Exception as e:
                print(f"Error fetching calendar {calendar_id}: {e}")
                continue

        # Detect conflicts
        conflicts = await conflict_detector.detect_conflicts(
            events=all_events,
            start_date=start,
            end_date=end
        )

        return conflicts

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conflicts/check")
async def check_specific_conflict(request: Request):
    """
    Check for conflicts with a specific proposed event

    Request body:
        {
            "title": "Meeting with team",
            "start": "2025-09-21T14:00:00",
            "end": "2025-09-21T15:00:00",
            "calendar_id": "primary"
        }
    """
    try:
        if not conflict_detector:
            raise HTTPException(status_code=503, detail="Conflict detector not initialized")

        data = await request.json()
        proposed_event = {
            "id": "proposed",
            "summary": data.get("title", "Proposed Event"),
            "start": data["start"],
            "end": data["end"],
            "calendar_id": data.get("calendar_id", "primary")
        }

        # Get existing events in the same time period
        start = datetime.fromisoformat(proposed_event["start"])
        end = datetime.fromisoformat(proposed_event["end"])

        # Extend search window by 1 day each side for context
        search_start = start - timedelta(days=1)
        search_end = end + timedelta(days=1)

        # Fetch events from all calendars
        all_events = [proposed_event]  # Include proposed event
        calendar_ids = [
            "primary",
            "mene.personal@gmail.com",
            "cindy.work@hospital.org",
            "family@demestihas.com",
            "persy.school@edu.org",
            "appointments@demestihas.com"
        ]

        for calendar_id in calendar_ids:
            try:
                if USING_OAUTH:
                    events = await calendar_api.get_events_async(
                        calendar_id=calendar_id,
                        time_min=search_start.isoformat() + 'Z',
                        time_max=search_end.isoformat() + 'Z'
                    )
                else:
                    events = calendar_api.get_events(
                        calendar_id=calendar_id,
                        time_min=search_start.isoformat() + 'Z',
                        time_max=search_end.isoformat() + 'Z'
                    )

                for event in events.get('items', []):
                    if 'start' in event and 'dateTime' in event['start']:
                        event['calendar_id'] = calendar_id
                        event['start'] = event['start']['dateTime']
                        event['end'] = event['end']['dateTime'] if 'end' in event else event['start']
                        all_events.append(event)

            except Exception as e:
                print(f"Error fetching calendar {calendar_id}: {e}")
                continue

        # Detect conflicts
        conflicts = await conflict_detector.detect_conflicts(
            events=all_events,
            start_date=search_start,
            end_date=search_end
        )

        # Filter to only show conflicts involving the proposed event
        proposed_conflicts = [
            c for c in conflicts['conflicts']
            if any(e.get('id') == 'proposed' for e in c['events'])
        ]

        return {
            "proposed_event": proposed_event,
            "has_conflicts": len(proposed_conflicts) > 0,
            "conflicts": proposed_conflicts,
            "summary": {
                "total": len(proposed_conflicts),
                "critical": sum(1 for c in proposed_conflicts if c['severity'] == 'critical'),
                "high": sum(1 for c in proposed_conflicts if c['severity'] == 'high'),
                "medium": sum(1 for c in proposed_conflicts if c['severity'] == 'medium'),
                "low": sum(1 for c in proposed_conflicts if c['severity'] == 'low')
            }
        }

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conflicts/free-slots")
async def find_free_slots(
    duration_minutes: int = Query(60, description="Required duration in minutes"),
    days: int = Query(7, description="Number of days to search"),
    start_hour: int = Query(9, description="Start of working hours"),
    end_hour: int = Query(17, description="End of working hours")
):
    """
    Find available time slots without conflicts

    Args:
        duration_minutes: Required duration for the slot
        days: Number of days ahead to search
        start_hour: Start of working hours (0-23)
        end_hour: End of working hours (0-23)

    Returns:
        List of available time slots
    """
    try:
        if not conflict_detector:
            raise HTTPException(status_code=503, detail="Conflict detector not initialized")

        start = datetime.now()
        end = start + timedelta(days=days)

        # Fetch events from all calendars
        all_events = []
        calendar_ids = [
            "primary",
            "mene.personal@gmail.com",
            "cindy.work@hospital.org",
            "family@demestihas.com",
            "persy.school@edu.org",
            "appointments@demestihas.com"
        ]

        for calendar_id in calendar_ids:
            try:
                if USING_OAUTH:
                    events = await calendar_api.get_events_async(
                        calendar_id=calendar_id,
                        time_min=start.isoformat() + 'Z',
                        time_max=end.isoformat() + 'Z'
                    )
                else:
                    events = calendar_api.get_events(
                        calendar_id=calendar_id,
                        time_min=start.isoformat() + 'Z',
                        time_max=end.isoformat() + 'Z'
                    )

                for event in events.get('items', []):
                    if 'start' in event and 'dateTime' in event['start']:
                        event['calendar_id'] = calendar_id
                        event['start'] = event['start']['dateTime']
                        event['end'] = event['end']['dateTime'] if 'end' in event else event['start']
                        all_events.append(event)

            except Exception as e:
                print(f"Error fetching calendar {calendar_id}: {e}")
                continue

        # Find free slots
        free_slots = await conflict_detector.find_conflict_free_slots(
            events=all_events,
            duration_minutes=duration_minutes,
            start_date=start,
            end_date=end,
            working_hours=(start_hour, end_hour)
        )

        return {
            "search_parameters": {
                "duration_minutes": duration_minutes,
                "days": days,
                "working_hours": f"{start_hour:02d}:00 - {end_hour:02d}:00"
            },
            "available_slots": free_slots[:20],  # Limit to first 20 slots
            "total_slots_found": len(free_slots)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/calendars")
async def list_calendars():
    """List all configured calendars"""
    if not conflict_detector:
        raise HTTPException(status_code=503, detail="Conflict detector not initialized")

    return {
        "calendars": conflict_detector.calendars,
        "total": len(conflict_detector.calendars)
    }

if __name__ == "__main__":
    port = int(os.getenv("HUATA_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
