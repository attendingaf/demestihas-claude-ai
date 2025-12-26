"""
LangServe server for Lyco LangGraph.

Integrates LangGraph workflow with FastAPI and existing v2 endpoints.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from langserve import add_routes
from langchain_core.runnables import RunnableConfig
from typing import Dict, Any, Optional, List
import uvicorn
import os
import sys
from pathlib import Path
from datetime import datetime
import asyncio
import json

# Add v2 path to reuse existing endpoints
lyco_v2_path = Path(__file__).parent.parent / "lyco-v2"
if lyco_v2_path.exists():
    sys.path.insert(0, str(lyco_v2_path))
    # Import v2 components if available
    try:
        from server import (
            get_status, get_all_tasks, complete_task, skip_task,
            start_rounds, get_performance_stats, get_system_health,
            generate_weekly_insights
        )
        V2_AVAILABLE = True
    except ImportError:
        V2_AVAILABLE = False
else:
    V2_AVAILABLE = False

# Import our LangGraph workflow
from workflow.graph import app as lyco_workflow, get_graph_structure, validate_graph
from workflow.state import LycoGraphState

# Create FastAPI app
app = FastAPI(
    title="Lyco LangGraph",
    description="ADHD-optimized task management with visual workflow",
    version="2.0.0"
)

# Add LangServe routes for Studio integration
try:
    # Try with all parameters (older LangServe version)
    add_routes(
        app,
        lyco_workflow,
        path="/lyco",
        enabled_endpoints=["invoke", "batch", "stream", "stream_log"],
        enable_playground=True,
        enable_feedback_endpoint=True,
        enable_public_trace_link_endpoint=True,
        playground_type="default"
    )
except TypeError:
    # Fallback for newer LangServe version with fewer parameters
    add_routes(
        app,
        lyco_workflow,
        path="/lyco"
    )

# ===== ROOT ENDPOINT =====
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return HTMLResponse("""
    <html>
        <head>
            <title>Lyco LangGraph</title>
            <style>
                body { font-family: -apple-system, sans-serif; padding: 40px; background: #f5f5f5; }
                h1 { color: #333; }
                .endpoint { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; }
                code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
                a { color: #007AFF; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>🧠 Lyco LangGraph v2.0</h1>
            <p>ADHD-optimized task management with visual workflow</p>

            <h2>Key Endpoints:</h2>
            <div class="endpoint">
                <strong>LangGraph Playground:</strong> <a href="/lyco/playground">/lyco/playground</a>
            </div>
            <div class="endpoint">
                <strong>API Documentation:</strong> <a href="/docs">/docs</a>
            </div>
            <div class="endpoint">
                <strong>Graph Structure:</strong> <a href="/debug/graph">/debug/graph</a>
            </div>
            <div class="endpoint">
                <strong>Health Check:</strong> <a href="/health">/health</a>
            </div>

            <h2>Quick Start:</h2>
            <div class="endpoint">
                <code>curl -X POST http://localhost:8000/lyco/invoke -H "Content-Type: application/json" -d '{"input": {"raw_input": "Schedule meeting with team", "source": "terminal"}}'</code>
            </div>
        </body>
    </html>
    """)

# ===== TASK PROCESSING ENDPOINTS =====
@app.post("/api/task/process")
async def process_task(request: Dict[str, Any]):
    """Process a task through the LangGraph workflow"""
    try:
        # Prepare state for workflow
        state = LycoGraphState(
            raw_input=request.get("text", ""),
            source=request.get("source", "terminal"),
            user_id=request.get("user_id", "mene@beltlineconsulting.co"),
            timestamp=datetime.now().isoformat(),
            messages=[],
            skip_count=0,
            patterns_detected=[],
            skip_reasons=[],
            retry_count=0,
            processing_time_ms=0,
            cache_hit=False,
            confidence_score=0.0,
            notification_sent=False,
            calendar_blocked=False,
            notion_synced=False,
            redis_published=False,
            database_saved=False,
            should_retry=False,
            energy_mismatch=False,
            should_park=False,
            prompt_version=1
        )

        # Run through workflow
        config = RunnableConfig(configurable={"thread_id": "main"})
        result = await lyco_workflow.ainvoke(state, config)

        return JSONResponse(content={
            "success": True,
            "task_id": result.get("task_id"),
            "action": result.get("action"),
            "title": result.get("task_title"),
            "quadrant": result.get("quadrant"),
            "energy_level": result.get("energy_level"),
            "assigned_to": result.get("assigned_to")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== V2 COMPATIBILITY ENDPOINTS =====
if V2_AVAILABLE:
    # Mount existing v2 endpoints
    app.get("/api/status")(get_status)
    app.get("/api/tasks/all")(get_all_tasks)
    app.post("/api/tasks/{task_id}/complete")(complete_task)
    app.post("/api/tasks/{task_id}/skip")(skip_task)
    app.post("/api/rounds/start")(start_rounds)
    app.get("/api/performance")(get_performance_stats)
    app.get("/api/health")(get_system_health)
    app.post("/api/generate-insights")(generate_weekly_insights)
else:
    # Provide stub endpoints if v2 not available
    @app.get("/api/status")
    async def get_status():
        return {"status": "running", "version": "2.0.0", "v2_integration": False}

# ===== STUDIO DEBUGGING ENDPOINTS =====
@app.get("/debug/graph")
async def get_graph_visualization():
    """Return graph structure for visualization"""
    structure = get_graph_structure()
    validation = validate_graph()

    return {
        "structure": structure,
        "validation": validation,
        "stats": {
            "total_nodes": len(structure["nodes"]),
            "total_edges": len(structure["edges"])
        }
    }

@app.get("/debug/state/{execution_id}")
async def get_execution_state(execution_id: str):
    """Get current state of a running execution"""
    # This would connect to the checkpoint storage
    return {
        "execution_id": execution_id,
        "status": "running",
        "current_node": "parse_task",
        "message": "Feature requires checkpoint persistence setup"
    }

@app.get("/debug/nodes")
async def list_nodes():
    """List all available nodes in the workflow"""
    from workflow.nodes import __all__ as node_names
    return {"nodes": node_names}

# ===== WEBSOCKET FOR REAL-TIME UPDATES =====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time task updates"""
    await websocket.accept()
    try:
        while True:
            # Receive task from client
            data = await websocket.receive_json()

            # Process through workflow
            state = LycoGraphState(
                raw_input=data.get("text", ""),
                source="terminal",
                user_id=data.get("user_id", "mene@beltlineconsulting.co"),
                timestamp=datetime.now().isoformat(),
                messages=[],
                skip_count=0,
                patterns_detected=[],
                skip_reasons=[],
                retry_count=0,
                processing_time_ms=0,
                cache_hit=False,
                confidence_score=0.0,
                notification_sent=False,
                calendar_blocked=False,
                notion_synced=False,
                redis_published=False,
                database_saved=False,
                should_retry=False,
                energy_mismatch=False,
                should_park=False,
                prompt_version=1
            )

            # Stream updates as task progresses
            config = RunnableConfig(configurable={"thread_id": f"ws_{websocket.client}"})
            async for chunk in lyco_workflow.astream(state, config):
                await websocket.send_json({
                    "type": "update",
                    "data": chunk
                })

    except WebSocketDisconnect:
        pass

# ===== HEALTH AND MONITORING =====
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    graph_validation = validate_graph()

    # Check Redis connection
    redis_healthy = False
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        redis_healthy = True
    except:
        pass

    return {
        "status": "healthy" if graph_validation["valid"] else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "graph": graph_validation["valid"],
            "redis": redis_healthy,
            "v2_integration": V2_AVAILABLE
        }
    }

# ===== METRICS ENDPOINT =====
@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    metrics = []

    # Add basic metrics
    metrics.append("# HELP lyco_tasks_total Total number of tasks processed")
    metrics.append("# TYPE lyco_tasks_total counter")
    metrics.append("lyco_tasks_total 0")

    metrics.append("# HELP lyco_graph_nodes Total number of nodes in graph")
    metrics.append("# TYPE lyco_graph_nodes gauge")
    structure = get_graph_structure()
    metrics.append(f"lyco_graph_nodes {len(structure['nodes'])}")

    return "\n".join(metrics)

# ===== MAIN ENTRY POINT =====
if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Get server configuration
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8000))
    reload = os.getenv("DEBUG", "true").lower() == "true"

    print(f"""
    🚀 Lyco LangGraph Server Starting...

    📍 Server: http://{host}:{port}
    🎮 Playground: http://{host}:{port}/lyco/playground
    📚 API Docs: http://{host}:{port}/docs
    🔍 Graph Debug: http://{host}:{port}/debug/graph

    Press CTRL+C to stop
    """)

    # Run server
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
