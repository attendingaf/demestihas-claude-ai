"""
MiMerc Grocery List Management Agent
Production version - API Server Only
"""

import os
import json
import time
from typing import List, Dict, TypedDict, Annotated, Any
from datetime import datetime
import asyncio
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langgraph_checkpoint_postgres import PostgresCheckpointer
from psycopg_pool import ConnectionPool

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the state for our agent
class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    grocery_list: Annotated[List[Dict[str, Any]], "The current grocery list"]
    next_action: Annotated[str, "The next action to take"]

# Define a simple tool for managing the grocery list
@tool
def add_items_to_list(items: List[str]) -> str:
    """Add items to the grocery list."""
    result = f"Added {len(items)} items to the grocery list: {', '.join(items)}"
    return result

@tool
def remove_items_from_list(items: List[str]) -> str:
    """Remove items from the grocery list."""
    result = f"Removed {len(items)} items from the grocery list: {', '.join(items)}"
    return result

@tool
def get_grocery_list() -> str:
    """Get the current grocery list."""
    return "Use the grocery_list from the state to show items."

# Node functions
def planner(state: GraphState) -> GraphState:
    """Plan the next action based on the user's request."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Get the last user message
    last_message = state["messages"][-1] if state["messages"] else None

    if not last_message:
        state["next_action"] = "respond"
        return state

    # Determine what action to take
    planning_prompt = f"""
    Based on the user's message: "{last_message.content}"
    Current grocery list: {state.get('grocery_list', [])}

    Determine the action:
    - If the user wants to add items, respond with: "add_items"
    - If the user wants to remove items, respond with: "remove_items"
    - If the user wants to see the list, respond with: "show_list"
    - For general conversation, respond with: "chat"

    Respond with only the action name.
    """

    response = llm.invoke([HumanMessage(content=planning_prompt)])
    action = response.content.strip().lower()

    # Validate and set the action
    valid_actions = ["add_items", "remove_items", "show_list", "chat"]
    if action in valid_actions:
        state["next_action"] = action
    else:
        state["next_action"] = "chat"

    return state

def list_manager(state: GraphState) -> GraphState:
    """Manage the grocery list based on the planned action."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    action = state.get("next_action", "chat")
    last_message = state["messages"][-1] if state["messages"] else None

    if not last_message:
        return state

    current_list = state.get("grocery_list", [])

    if action == "add_items":
        # Extract items to add from the user's message
        extract_prompt = f"""
        Extract the grocery items from this message: "{last_message.content}"
        Return as a JSON list of objects with 'item' and 'quantity' (if specified).
        Example: [{{"item": "milk", "quantity": "1 gallon"}}, {{"item": "eggs", "quantity": "1 dozen"}}]
        If no quantity specified, use "1" as default.
        """

        response = llm.invoke([HumanMessage(content=extract_prompt)])
        try:
            items_to_add = json.loads(response.content)
            current_list.extend(items_to_add)
            state["grocery_list"] = current_list
        except json.JSONDecodeError:
            # Fallback: try to extract items as simple strings
            items = [item.strip() for item in response.content.split(",")]
            for item in items:
                if item:
                    current_list.append({"item": item, "quantity": "1"})
            state["grocery_list"] = current_list

    elif action == "remove_items":
        # Extract items to remove
        extract_prompt = f"""
        Extract the grocery items to remove from this message: "{last_message.content}"
        Current list: {current_list}
        Return as a JSON list of item names to remove.
        Example: ["milk", "eggs"]
        """

        response = llm.invoke([HumanMessage(content=extract_prompt)])
        try:
            items_to_remove = json.loads(response.content)
            # Remove items from the list
            state["grocery_list"] = [
                item for item in current_list
                if item.get("item", "").lower() not in [i.lower() for i in items_to_remove]
            ]
        except json.JSONDecodeError:
            pass  # Keep the list unchanged if parsing fails

    elif action == "show_list":
        # The list is already in the state, no modification needed
        pass

    return state

def responder(state: GraphState) -> GraphState:
    """Generate a response to the user."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    action = state.get("next_action", "chat")
    last_message = state["messages"][-1] if state["messages"] else None
    current_list = state.get("grocery_list", [])

    # Generate appropriate response based on the action
    if action == "add_items":
        if current_list:
            response_text = f"I've added those items to your grocery list. Your list now has {len(current_list)} items."
        else:
            response_text = "I'll help you add items to your grocery list. Please tell me what you'd like to add."

    elif action == "remove_items":
        response_text = f"I've removed those items from your list. You now have {len(current_list)} items remaining."

    elif action == "show_list":
        if current_list:
            list_display = "\n".join([
                f"- {item['item']} (Quantity: {item.get('quantity', '1')})"
                for item in current_list
            ])
            response_text = f"Here's your current grocery list:\n{list_display}"
        else:
            response_text = "Your grocery list is currently empty. Would you like to add some items?"

    else:  # chat
        response_prompt = f"""
        Respond to the user's message: "{last_message.content if last_message else 'Hello'}"
        Be helpful and friendly. You are MiMerc, a grocery list management assistant.
        Current list size: {len(current_list)} items
        """
        response = llm.invoke([HumanMessage(content=response_prompt)])
        response_text = response.content

    # Add the response to messages
    state["messages"].append(AIMessage(content=response_text))

    return state

# Define the workflow
def build_graph():
    """Build the LangGraph workflow."""

    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("planner", planner)
    workflow.add_node("list_manager", list_manager)
    workflow.add_node("responder", responder)

    # Define the flow
    workflow.set_entry_point("planner")

    # Add edges
    workflow.add_edge("planner", "list_manager")
    workflow.add_edge("list_manager", "responder")
    workflow.add_edge("responder", END)

    # Initialize PostgreSQL checkpointer
    checkpointer, pool = initialize_checkpointer()

    # Compile the graph with memory
    app = workflow.compile(checkpointer=checkpointer)

    return app, pool

def initialize_checkpointer():
    """Initialize the PostgreSQL checkpointer for state persistence."""

    # Get connection info from environment
    conn_info = os.getenv("PG_CONNINFO")

    if not conn_info:
        # Build connection string from individual components
        pg_user = os.getenv("POSTGRES_USER", "mimerc")
        pg_password = os.getenv("POSTGRES_PASSWORD", "")
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "mimerc_db")

        conn_info = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    logger.info(f"Connecting to PostgreSQL...")

    # Create connection pool
    pool = ConnectionPool(
        conninfo=conn_info,
        max_size=20,
        min_size=5,
        timeout=30.0
    )

    # Create checkpointer
    checkpointer = PostgresCheckpointer(pool=pool)

    # Initialize the database tables
    with pool.connection() as conn:
        checkpointer.setup(conn)

    logger.info("PostgreSQL checkpointer initialized successfully")
    return checkpointer, pool

# FastAPI app
app_instance = FastAPI(title="MiMerc API", version="1.0.0")
graph_app = None
connection_pool = None

@app_instance.on_event("startup")
async def startup_event():
    """Initialize the graph on startup."""
    global graph_app, connection_pool
    logger.info("Starting MiMerc API server...")
    graph_app, connection_pool = build_graph()
    logger.info("MiMerc API server ready!")

@app_instance.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global connection_pool
    if connection_pool:
        connection_pool.close()
        logger.info("Database connection pool closed.")

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]

@app_instance.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests."""
    if not graph_app:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Configuration with thread ID for state persistence
        config = {"configurable": {"thread_id": request.thread_id}}

        # Create input state
        input_state = {
            "messages": [HumanMessage(content=request.message)],
            "grocery_list": [],
            "next_action": ""
        }

        # Run the agent
        response_content = ""
        final_list = []

        for chunk in graph_app.stream(input_state, config):
            for node_name, node_output in chunk.items():
                if node_name == "responder" and "messages" in node_output:
                    for msg in node_output["messages"]:
                        if isinstance(msg, AIMessage):
                            response_content = msg.content
                if "grocery_list" in node_output:
                    final_list = node_output["grocery_list"]

        return ChatResponse(
            response=response_content,
            thread_id=request.thread_id,
            grocery_list=final_list
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app_instance.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MiMerc API"}

@app_instance.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MiMerc Grocery List Management API",
        "version": "1.0.0",
        "endpoints": {
            "/chat": "POST - Send chat messages",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }

# Main execution
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc Grocery List Management Agent v1.0")
    logger.info("=" * 60)
    logger.info("Starting API server...")

    # Run the FastAPI app
    uvicorn.run(
        app_instance,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
