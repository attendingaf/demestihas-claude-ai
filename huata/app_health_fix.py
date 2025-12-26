#!/usr/bin/env python3
"""
Huata Calendar Agent - Simplified App with Working Health Endpoints
Ensures health checks work even if some components are missing
"""

import os
import sys
import asyncio
import json
import time
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Huata Calendar Agent",
    description="LLM-powered natural language calendar assistant with health monitoring",
    version="2.0.1"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Component status tracking
component_status = {
    "redis": "unknown",
    "huata_agent": "unknown",
    "calendar_api": "unknown",
    "conflict_detector": "unknown"
}

# Optional component instances
redis_client = None
huata_agent = None
calendar_api = None
conflict_detector = None

@app.on_event("startup")
async def startup_event():
    """Initialize components with graceful fallbacks"""
    global redis_client, huata_agent, calendar_api, conflict_detector, component_status

    print("🚀 Starting Huata Calendar Agent...")

    # Try to initialize Redis (optional)
    try:
        import redis.asyncio as redis
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))

        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        await redis_client.ping()
        component_status["redis"] = "connected"
        print(f"✅ Redis connected at {redis_host}:{redis_port}")
    except Exception as e:
        component_status["redis"] = f"disconnected: {str(e)[:50]}"
        print(f"⚠️  Redis unavailable: {e}")

    # Try to initialize Huata agent (optional)
    try:
        from huata import HuataCalendarAgent
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if anthropic_key:
            huata_agent = HuataCalendarAgent(
                anthropic_api_key=anthropic_key,
                redis_host=os.environ.get('REDIS_HOST', 'localhost'),
                redis_port=int(os.environ.get('REDIS_PORT', 6379))
            )
            component_status["huata_agent"] = "ready"
            print("✅ Huata agent initialized")
        else:
            component_status["huata_agent"] = "missing_api_key"
            print("⚠️  Huata agent: ANTHROPIC_API_KEY not set")
    except Exception as e:
        component_status["huata_agent"] = f"error: {str(e)[:50]}"
        print(f"⚠️  Huata agent initialization failed: {e}")

    # Try to initialize Calendar API (optional)
    try:
        # Try OAuth first
        try:
            from calendar_tools_oauth import GoogleCalendarOAuth
            calendar_api = GoogleCalendarOAuth()
            component_status["calendar_api"] = "oauth_ready"
            print("✅ Calendar API (OAuth) initialized")
        except:
            # Fall back to service account
            from calendar_tools import GoogleCalendarAPI
            creds_path = '/app/credentials/huata-service-account.json'
            if os.path.exists(creds_path):
                calendar_api = GoogleCalendarAPI(credentials_path=creds_path)
                component_status["calendar_api"] = "service_account_ready"
                print("✅ Calendar API (Service Account) initialized")
            else:
                component_status["calendar_api"] = "no_credentials"
                print("⚠️  Calendar API: No credentials available")
    except Exception as e:
        component_status["calendar_api"] = f"error: {str(e)[:50]}"
        print(f"⚠️  Calendar API initialization failed: {e}")

    # Try to initialize Conflict Detector (optional)
    try:
        from conflict_detector import ConflictDetector
        conflict_detector = ConflictDetector(redis_client=redis_client)
        component_status["conflict_detector"] = "ready"
        print("✅ Conflict detector initialized")
    except Exception as e:
        component_status["conflict_detector"] = f"error: {str(e)[:50]}"
        print(f"⚠️  Conflict detector initialization failed: {e}")

    print("🎯 Huata startup complete - Health endpoint available at /health")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            print("Redis connection closed")
        except:
            pass

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Huata Calendar Agent",
        "version": "2.0.1",
        "status": "running",
        "health_endpoint": "/health",
        "simple_health_endpoint": "/health/simple"
    }

@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint
    Returns component status even if some are missing
    """
    start_time = time.time()

    try:
        # Quick Redis ping if available
        if redis_client:
            try:
                await asyncio.wait_for(redis_client.ping(), timeout=0.5)
                component_status["redis"] = "connected"
            except asyncio.TimeoutError:
                component_status["redis"] = "timeout"
            except Exception as e:
                component_status["redis"] = f"error: {str(e)[:30]}"

        # Determine overall health
        critical_components = ["huata_agent", "calendar_api"]
        critical_ok = all(
            "ready" in component_status.get(comp, "unknown")
            for comp in critical_components
        )

        overall_status = "healthy" if critical_ok else "degraded"

        response_time_ms = int((time.time() - start_time) * 1000)

        return {
            "status": overall_status,
            "components": component_status,
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": response_time_ms,
            "version": "2.0.1"
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/health/simple")
async def simple_health():
    """
    Simple health endpoint for basic monitoring
    Always returns OK if the service is running
    """
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint
    Returns 200 only if critical components are ready
    """
    critical_ready = (
        "ready" in component_status.get("huata_agent", "unknown") and
        "ready" in component_status.get("calendar_api", "unknown")
    )

    if critical_ready:
        return {"status": "ready"}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "components": component_status}
        )

@app.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint
    Returns 200 if the service is alive (even if degraded)
    """
    return {"status": "alive"}

@app.post("/query")
async def process_query(request: Request):
    """Process natural language calendar query"""
    try:
        data = await request.json()
        query = data.get("query")

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        if not huata_agent:
            # Return graceful degradation message
            return {
                "query": query,
                "response": "Huata agent is currently unavailable. Please check the health endpoint for component status.",
                "status": "degraded",
                "timestamp": datetime.now().isoformat()
            }

        # Process query if agent available
        user_context = data.get("context", {})
        response = await huata_agent.process_query(query, user_context)

        return {
            "query": query,
            "response": response,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "query": query if 'query' in locals() else None,
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/status")
async def detailed_status():
    """
    Detailed status endpoint with component diagnostics
    """
    diagnostics = {
        "service": "Huata Calendar Agent",
        "version": "2.0.1",
        "environment": {
            "python_version": sys.version,
            "redis_host": os.environ.get('REDIS_HOST', 'not_set'),
            "redis_port": os.environ.get('REDIS_PORT', 'not_set'),
            "anthropic_key_set": bool(os.environ.get('ANTHROPIC_API_KEY')),
        },
        "components": component_status,
        "endpoints": {
            "health": "/health",
            "simple_health": "/health/simple",
            "readiness": "/health/ready",
            "liveness": "/health/live",
            "query": "/query",
            "status": "/status"
        },
        "timestamp": datetime.now().isoformat()
    }

    return diagnostics

if __name__ == "__main__":
    # Run with uvicorn
    port = int(os.environ.get("PORT", 8003))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"🚀 Starting Huata Calendar Agent on {host}:{port}")
    print(f"📊 Health check available at http://{host}:{port}/health")
    print(f"✅ Simple health check at http://{host}:{port}/health/simple")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
