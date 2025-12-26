"""
MiMerc Grocery List Management Agent
SHARED LIST VERSION with Enhanced Item Handling and Tool Execution
"""

import os
import json
import logging
from typing import List, Dict, Any, TypedDict, Annotated
from datetime import datetime

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph_checkpoint_postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# Import our tools module
from tools import (
    add_items_to_list,
    remove_items_from_list,
    edit_item_quantity,
    get_grocery_list,
    clear_entire_list,
    search_item_in_list,
    process_tool_result
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the state for our agent
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    grocery_list: Annotated[List[Dict[str, Any]], "The current shared grocery list"]
    next_action: Annotated[str, "The next action to take"]
    tool_calls: Annotated[List[Dict], "Recent tool calls for tracking"]
    needs_correction: Annotated[bool, "Flag for self-correction needed"]

# FastAPI app
app = FastAPI(title="MiMerc Shared List API", version="2.0.0")

# Global variables for LangGraph app and connection pool
graph_app = None
connection_pool = None

def create_system_prompt():
    """
    Create enhanced system prompt with explicit multi-word item handling.
    CRITICAL: This prompt ensures proper handling of quoted items and self-correction.
    """
    return SystemMessage(content="""You are MiMerc, a shared family grocery list assistant.

CRITICAL RULES FOR ITEM HANDLING:
1. **QUOTED ITEMS**: When a user's request contains a quoted item name like "chocolate syrup",
   you MUST treat the ENTIRE phrase as a SINGLE, INDIVISIBLE item.
   DO NOT split "chocolate syrup" into "chocolate" and "syrup".

2. **MULTI-WORD ITEMS**: Common multi-word items should be recognized as single items:
   - "peanut butter" (NOT "peanut" and "butter")
   - "ice cream" (NOT "ice" and "cream")
   - "sour cream" (NOT "sour" and "cream")
   - "chocolate chips" (NOT "chocolate" and "chips")

3. **TOOL USAGE PRIORITY**: Always use the appropriate tool:
   - add_items_to_list: For adding new items (respect quotes!)
   - edit_item_quantity: For changing quantities of existing items
   - remove_items_from_list: For removing items

4. **SELF-CORRECTION**: If you accidentally split an item incorrectly:
   - First, use remove_items_from_list to remove the incorrect split items
   - Then, use add_items_to_list with the correct full item name

5. **SHARED LIST**: Remember this is a SHARED family list. All changes affect all users.

When processing requests:
- Parse carefully for quoted strings
- Maintain item integrity for multi-word items
- Use edit_item_quantity when users want to change amounts
- Always confirm what was added/changed/removed""")

def enhanced_planner(state: AgentState) -> AgentState:
    """
    Enhanced planner that properly identifies multi-word items.
    MODIFIED: Includes logic to detect quoted items and prevent splitting.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    messages = state.get("messages", [])
    if not messages:
        state["next_action"] = "respond"
        return state

    last_message = messages[-1]

    # Check if we need correction from previous action
    if state.get("needs_correction", False):
        state["next_action"] = "correct_items"
        return state

    # Enhanced parsing for quoted items
    message_content = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # Detect quoted items in the message
    import re
    quoted_items = re.findall(r'"([^"]*)"', message_content)

    # Create planning context with quote awareness
    planning_prompt = f"""
    User message: "{message_content}"
    Current list has {len(state.get('grocery_list', []))} items.

    IMPORTANT: Found quoted items: {quoted_items if quoted_items else 'None'}
    These must be treated as single items!

    Determine the action:
    - If adding items (especially quoted ones): "add_items"
    - If changing quantity: "edit_quantity"
    - If removing items: "remove_items"
    - If viewing list: "show_list"
    - If clearing list: "clear_list"
    - For general chat: "chat"

    Respond with only the action name."""

    response = llm.invoke([create_system_prompt(), HumanMessage(content=planning_prompt)])
    action = response.content.strip().lower()

    valid_actions = ["add_items", "edit_quantity", "remove_items", "show_list", "clear_list", "chat"]
    state["next_action"] = action if action in valid_actions else "chat"

    return state

def tool_executor(state: AgentState) -> AgentState:
    """
    Execute tools and properly update state.
    CRITICAL: Ensures tool results update grocery_list for PostgresSaver persistence.
    """
    action = state.get("next_action", "chat")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        return state

    message_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Create tool-specific prompts with quote preservation
    tools = [add_items_to_list, remove_items_from_list, edit_item_quantity,
             get_grocery_list, clear_entire_list, search_item_in_list]

    if action == "add_items":
        # Extract items with special handling for quotes
        import re
        quoted_items = re.findall(r'"([^"]*)"', message_content)

        extract_prompt = f"""
        Extract grocery items from: "{message_content}"

        CRITICAL RULES:
        1. Quoted items found: {quoted_items}
        2. Each quoted item must be kept as ONE item
        3. Do NOT split "chocolate syrup" into separate items

        Return a JSON object:
        {{"items": ["item1", "item2"], "quantities": ["qty1", "qty2"]}}

        Keep multi-word items together!"""

        response = llm.invoke([HumanMessage(content=extract_prompt)])

        try:
            data = json.loads(response.content)
            items = data.get("items", [])
            quantities = data.get("quantities", [])

            # Execute tool
            tool_result = add_items_to_list.invoke({"items": items, "quantities": quantities})

            # Update state with tool result
            updated_state = process_tool_result(tool_result, state)
            state["grocery_list"] = updated_state.get("grocery_list", state.get("grocery_list", []))

            # Track tool call for potential correction
            state["tool_calls"] = state.get("tool_calls", []) + [{"tool": "add_items", "items": items}]

        except Exception as e:
            logger.error(f"Error processing add items: {e}")

    elif action == "edit_quantity":
        # Extract item and new quantity
        extract_prompt = f"""
        Extract item and new quantity from: "{message_content}"
        Return JSON: {{"item": "item_name", "quantity": "new_quantity"}}"""

        response = llm.invoke([HumanMessage(content=extract_prompt)])

        try:
            data = json.loads(response.content)
            item = data.get("item", "")
            quantity = data.get("quantity", "1")

            # Execute tool - CRITICAL: edit_item_quantity ensures proper state update
            tool_result = edit_item_quantity.invoke({"item": item, "new_quantity": quantity})

            # Update state with tool result
            updated_state = process_tool_result(tool_result, state)
            state["grocery_list"] = updated_state.get("grocery_list", state.get("grocery_list", []))

        except Exception as e:
            logger.error(f"Error processing quantity edit: {e}")

    elif action == "remove_items":
        # Extract items to remove
        extract_prompt = f"""
        Extract items to remove from: "{message_content}"
        Return JSON: {{"items": ["item1", "item2"]}}"""

        response = llm.invoke([HumanMessage(content=extract_prompt)])

        try:
            data = json.loads(response.content)
            items = data.get("items", [])

            # Execute tool
            tool_result = remove_items_from_list.invoke({"items": items})

            # Update state
            updated_state = process_tool_result(tool_result, state)
            state["grocery_list"] = updated_state.get("grocery_list", state.get("grocery_list", []))

        except Exception as e:
            logger.error(f"Error processing remove items: {e}")

    elif action == "clear_list":
        # Clear entire list
        tool_result = clear_entire_list.invoke({})
        updated_state = process_tool_result(tool_result, state)
        state["grocery_list"] = updated_state.get("grocery_list", [])

    # Check if correction needed (e.g., if "chocolate" and "syrup" were added separately)
    if action == "add_items" and state.get("tool_calls"):
        last_call = state["tool_calls"][-1]
        items_added = last_call.get("items", [])

        # Simple heuristic: check for suspicious splits
        if ("chocolate" in items_added and "syrup" in items_added) or \
           ("peanut" in items_added and "butter" in items_added):
            state["needs_correction"] = True

    return state

def self_corrector(state: AgentState) -> AgentState:
    """
    Self-correction node to fix incorrectly split items.
    NEW: Implements two-step correction process.
    """
    if not state.get("needs_correction", False):
        return state

    # Analyze last tool call for correction
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        state["needs_correction"] = False
        return state

    last_call = tool_calls[-1]
    items = last_call.get("items", [])

    # Detect common mis-splits
    corrections = []
    if "chocolate" in items and "syrup" in items:
        corrections.append(("chocolate syrup", ["chocolate", "syrup"]))
    if "peanut" in items and "butter" in items:
        corrections.append(("peanut butter", ["peanut", "butter"]))
    if "ice" in items and "cream" in items:
        corrections.append(("ice cream", ["ice", "cream"]))

    # Apply corrections
    for correct_item, wrong_items in corrections:
        # Step 1: Remove incorrect items
        remove_result = remove_items_from_list.invoke({"items": wrong_items})
        updated_state = process_tool_result(remove_result, state)
        state["grocery_list"] = updated_state.get("grocery_list", [])

        # Step 2: Add correct item
        add_result = add_items_to_list.invoke({"items": [correct_item], "quantities": ["1"]})
        updated_state = process_tool_result(add_result, state)
        state["grocery_list"] = updated_state.get("grocery_list", [])

        # Log correction
        logger.info(f"Self-corrected: {wrong_items} -> {correct_item}")

    state["needs_correction"] = False
    return state

def responder(state: AgentState) -> AgentState:
    """Generate a response to the user."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    action = state.get("next_action", "chat")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    current_list = state.get("grocery_list", [])

    # Generate appropriate response
    if action == "add_items":
        response_text = f"✅ Items added to the shared family list. Total items: {len(current_list)}"

    elif action == "edit_quantity":
        response_text = "✅ Item quantity updated in the shared list."

    elif action == "remove_items":
        response_text = f"✅ Items removed. Remaining items: {len(current_list)}"

    elif action in ["show_list", "get_list"]:
        if current_list:
            list_display = "\n".join([
                f"• {item['item']} - Quantity: {item.get('quantity', '1')}"
                for item in current_list
            ])
            response_text = f"📋 **Shared Family Grocery List:**\n{list_display}\n\n_Total: {len(current_list)} items_"
        else:
            response_text = "The shared grocery list is currently empty."

    elif action == "clear_list":
        response_text = "⚠️ Entire shared list has been cleared!"

    else:
        # General response
        response_prompt = f"""
        Respond as MiMerc, the shared family grocery list assistant.
        User said: "{last_message.content if last_message else 'Hello'}"
        List has {len(current_list)} items.
        Remind them this is a SHARED list."""

        response = llm.invoke([create_system_prompt(), HumanMessage(content=response_prompt)])
        response_text = response.content

    # Add response to messages
    state["messages"].append(AIMessage(content=response_text))

    return state

def build_graph():
    """Build the enhanced LangGraph workflow."""

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("planner", enhanced_planner)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("self_corrector", self_corrector)
    workflow.add_node("responder", responder)

    # Define the flow with correction path
    workflow.set_entry_point("planner")

    # Add edges
    workflow.add_edge("planner", "tool_executor")

    # Conditional edge for self-correction
    def check_correction(state):
        return "self_corrector" if state.get("needs_correction", False) else "responder"

    workflow.add_conditional_edges(
        "tool_executor",
        check_correction,
        {
            "self_corrector": "self_corrector",
            "responder": "responder"
        }
    )

    workflow.add_edge("self_corrector", "responder")
    workflow.add_edge("responder", END)

    # Initialize PostgreSQL checkpointer for persistence
    checkpointer, pool = initialize_checkpointer()

    # Compile with checkpointer for state persistence
    app = workflow.compile(checkpointer=checkpointer)

    return app, pool

def initialize_checkpointer():
    """Initialize PostgreSQL checkpointer for shared state persistence."""

    # Get connection info
    conn_info = os.getenv("PG_CONNINFO")

    if not conn_info:
        pg_user = os.getenv("POSTGRES_USER", "mimerc")
        pg_password = os.getenv("POSTGRES_PASSWORD", "")
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "mimerc_db")

        conn_info = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    logger.info("Connecting to PostgreSQL for shared state...")

    # Create connection pool
    pool = ConnectionPool(
        conninfo=conn_info,
        max_size=20,
        min_size=5,
        timeout=30.0
    )

    # Create checkpointer - CRITICAL for shared state persistence
    checkpointer = PostgresSaver(pool=pool)

    # Setup database tables
    checkpointer.setup()

    logger.info("PostgreSQL checkpointer ready for shared list persistence")
    return checkpointer, pool

# FastAPI endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize the graph on startup."""
    global graph_app, connection_pool
    logger.info("Starting MiMerc Shared List API...")
    graph_app, connection_pool = build_graph()
    logger.info("API ready with shared list support!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global connection_pool
    if connection_pool:
        connection_pool.close()
        logger.info("Database connection pool closed.")

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "shared_family_list"  # Default to shared thread

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests for the shared list."""
    if not graph_app:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # CRITICAL: Use the provided thread_id (should be "shared_family_list")
        config = {"configurable": {"thread_id": request.thread_id}}

        # Create input state
        input_state = {
            "messages": [HumanMessage(content=request.message)],
            "grocery_list": [],  # Will be loaded from checkpoint
            "next_action": "",
            "tool_calls": [],
            "needs_correction": False
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
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MiMerc Shared List API", "version": "2.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MiMerc Shared Grocery List API",
        "version": "2.0.0",
        "features": [
            "Shared family list",
            "Multi-word item support",
            "Quantity editing",
            "Self-correction for split items"
        ]
    }

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc Shared Grocery List Agent v2.0")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
