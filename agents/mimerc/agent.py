import os
import json
import signal
import sys
import time
from typing import TypedDict, Annotated, Literal, List, Dict, Any
from operator import add

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variables for graceful shutdown
pool = None
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested, pool
    print("\n\nShutdown signal received. Cleaning up...")
    shutdown_requested = True

    if pool:
        try:
            pool.close()
            print("Database connection pool closed successfully.")
        except Exception as e:
            print(f"Error closing pool: {e}")

    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# State Definition
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # Keep for conversational history
    grocery_list: Dict[str, float]  # FIX: Transactional dictionary (item: quantity)
    final_response: str  # NEW: Dedicated channel for final output
    tool_calls: list  # Track tool calls
    next_action: str

# Tool Schemas
class AddItemInput(BaseModel):
    """Schema for adding an item to the grocery list"""
    item: str = Field(description="The item to add to the grocery list")
    quantity: str = Field(default="1", description="The quantity of the item")

class RemoveItemInput(BaseModel):
    """Schema for removing an item from the grocery list"""
    item: str = Field(description="The item to remove from the grocery list")

class ViewListInput(BaseModel):
    """Schema for viewing the grocery list"""
    pass

# Tool Implementations
@tool("add_item_to_list", args_schema=AddItemInput)
def add_item_to_list(item: str, quantity: str = "1") -> str:
    """Add an item to the grocery list with optional quantity"""
    return json.dumps({
        "action": "add",
        "item": item,
        "quantity": quantity,
        "status": "success",
        "message": f"Added {quantity} {item} to the list"
    })

@tool("remove_item_from_list", args_schema=RemoveItemInput)
def remove_item_from_list(item: str) -> str:
    """Remove an item from the grocery list"""
    return json.dumps({
        "action": "remove",
        "item": item,
        "status": "success",
        "message": f"Removed {item} from the list"
    })

@tool("view_list", args_schema=ViewListInput)
def view_list() -> str:
    """View the current grocery list"""
    return json.dumps({
        "action": "view",
        "status": "success",
        "message": "Request to view list"
    })

# Initialize tools
tools = [add_item_to_list, remove_item_from_list, view_list]

# Initialize LLM with tools
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY")
).bind_tools(tools)

# Node Functions
def planner(state: AgentState) -> AgentState:
    """Plan the next action based on the conversation"""
    messages = state.get("messages", [])

    system_prompt = SystemMessage(content="""You are MiMerc, a helpful grocery list management assistant.
    You can help users:
    1. Add items to their grocery list
    2. Remove items from their list
    3. View their current list

    Always be helpful and conversational. When users ask about their list, use the appropriate tools.""")

    response = llm.invoke([system_prompt] + messages)

    # Check if there are tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        state["next_action"] = "execute_tools"
    else:
        state["next_action"] = "respond"

    return {"messages": [response], "next_action": state["next_action"]}

def tool_executor(state: AgentState) -> AgentState:
    """Execute the tools called by the planner"""
    messages = state.get("messages", [])
    last_message = messages[-1]

    # Get current grocery list (dictionary)
    current_list = state.get("grocery_list", {})

    tool_messages = []
    updated_list = current_list.copy()  # Start with current state

    if hasattr(last_message, 'tool_calls'):
        for tool_call in last_message.tool_calls:
            # Find the matching tool
            tool_fn = None
            for t in tools:
                if t.name == tool_call["name"]:
                    tool_fn = t
                    break

            if tool_fn:
                # Execute the tool
                result = tool_fn.invoke(tool_call["args"])
                result_data = json.loads(result)

                # Handle grocery list updates with dictionary operations
                if result_data["action"] == "add":
                    item = tool_call['args']['item']
                    quantity = float(tool_call['args'].get('quantity', '1'))
                    # Add or update quantity in dictionary
                    if item in updated_list:
                        updated_list[item] += quantity
                    else:
                        updated_list[item] = quantity

                elif result_data["action"] == "remove":
                    item = tool_call['args']['item']
                    # Remove from dictionary with case-insensitive matching
                    item_to_remove = None
                    for key in updated_list.keys():
                        if key.lower() == item.lower():
                            item_to_remove = key
                            break

                    if item_to_remove:
                        del updated_list[item_to_remove]
                        result_data["message"] = f"Removed {item_to_remove} from the list"
                    else:
                        result_data["message"] = f"{item} not found in the list"

                    # Update the tool message with actual removal status
                    result = json.dumps(result_data)

                elif result_data["action"] == "view":
                    # Include current list state in result
                    result_data["list"] = updated_list
                    result = json.dumps(result_data)

                # Create tool message
                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)

    # CRITICAL: Return the complete state update to trigger persistence
    # The grocery_list MUST be included in the return for checkpointer to save it
    return {
        "messages": tool_messages,
        "grocery_list": updated_list,  # Replace entire dict - triggers checkpoint save
        "next_action": "respond",
        "tool_calls": []  # Clear tool calls after execution
    }

def responder(state: AgentState) -> AgentState:
    """Generate the final response to the user"""
    # Get current list state (transactional dictionary)
    current_list = state.get("grocery_list", {})

    # Find ONLY the most recent tool message (not all historical ones)
    last_tool_message = None
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, ToolMessage):
            last_tool_message = msg
            break

    # Generate the final response based on current state
    response_text = ""

    if last_tool_message:
        # Parse the last tool execution result
        try:
            result_data = json.loads(last_tool_message.content)
            action = result_data.get("action")

            if action == "view":
                # Format current list state
                if current_list:
                    items = [f"• {quantity} {item}" for item, quantity in current_list.items()]
                    response_text = f"Your current grocery list:\n" + "\n".join(items)
                else:
                    response_text = "Your grocery list is empty."

            elif action == "add":
                # Confirm addition
                response_text = result_data.get("message", "Item added to your list.")

            elif action == "remove":
                # Confirm removal
                response_text = result_data.get("message", "Item removed from your list.")

            else:
                response_text = result_data.get("message", "Request processed.")

        except json.JSONDecodeError:
            response_text = "I processed your request."
    else:
        # No tool was executed - pure conversational response
        response_text = "I'm MiMerc, your grocery list assistant. How can I help you?"

    # Return the final response in both channels for compatibility
    return {
        "messages": [AIMessage(content=response_text)],  # Keep for history
        "final_response": response_text,  # NEW: Clean output channel
        "next_action": "end"
    }

# Routing function
def route_next(state: AgentState) -> Literal["tool_executor", "responder", END]:
    """Route to the next node based on the planned action"""
    next_action = state.get("next_action", "end")

    if next_action == "execute_tools":
        return "tool_executor"
    elif next_action == "respond":
        return "responder"
    else:
        return END

# Persistence Initialization
def initialize_checkpointer():
    """Initialize PostgreSQL checkpointer with connection pool"""
    global pool

    pg_conninfo = os.environ.get("PG_CONNINFO")
    if not pg_conninfo:
        raise ValueError("PG_CONNINFO environment variable is not set")

    # Wait for database to be ready (with retry logic)
    max_retries = 10
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create connection pool
            pool = ConnectionPool(conninfo=pg_conninfo, min_size=2, max_size=10)

            # Test connection
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

            print("Successfully connected to PostgreSQL database.")
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"Failed to connect to database after {max_retries} attempts: {e}")
            print(f"Database connection attempt {retry_count}/{max_retries} failed. Retrying in 2 seconds...")
            time.sleep(2)

    # Create checkpointer using the connection pool
    # The PostgresSaver will handle table creation automatically
    checkpointer = PostgresSaver(
        pool,
        serde=JsonPlusSerializer()
    )

    return checkpointer, pool

# Graph Construction
def build_graph():
    """Build the LangGraph workflow"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("planner", planner)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("responder", responder)

    # Set entry point
    workflow.set_entry_point("planner")

    # Add edges
    workflow.add_conditional_edges(
        "planner",
        route_next
    )
    workflow.add_edge("tool_executor", "responder")
    workflow.add_edge("responder", END)

    # Initialize checkpointer
    checkpointer, pool = initialize_checkpointer()

    # Compile with checkpointer
    app = workflow.compile(checkpointer=checkpointer)

    return app, pool

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("MiMerc Grocery List Management Agent v1.0")
    print("=" * 60)
    print("Initializing system components...")

    try:
        # Build the graph
        app, connection_pool = build_graph()

        # Configuration with thread ID for state persistence
        config = {"configurable": {"thread_id": "user-123"}}

        print("\nMiMerc Agent is ready! Testing with sequential interactions...")
        print("-" * 50)

        # Test interactions
        test_messages = [
            "Hello! I need help managing my grocery list.",
            "Please add milk, eggs, and bread to my list.",
            "Add 2 pounds of chicken to the list.",
            "What's on my grocery list?",
            "Remove eggs from the list.",
            "Show me my updated list."
        ]

        for user_input in test_messages:
            print(f"\nUser: {user_input}")

            # Create input state
            input_state = {
                "messages": [HumanMessage(content=user_input)],
                "grocery_list": [],
                "next_action": ""
            }

            # Run the agent
            for chunk in app.stream(input_state, config):
                # Extract the final response
                for node_name, node_output in chunk.items():
                    if node_name == "responder" and "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, AIMessage):
                                print(f"MiMerc: {msg.content}")

            print("-" * 30)

        print("\n\nDemonstrating state persistence...")
        print("Creating a new session with the same thread_id...")
        print("-" * 50)

        # New interaction with same thread_id to demonstrate persistence
        new_input = {
            "messages": [HumanMessage(content="What items are on my list? (This should show the persisted state)")],
            "grocery_list": [],
            "next_action": ""
        }

        for chunk in app.stream(new_input, config):
            for node_name, node_output in chunk.items():
                if node_name == "responder" and "messages" in node_output:
                    for msg in node_output["messages"]:
                        if isinstance(msg, AIMessage):
                            print(f"MiMerc: {msg.content}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the pool gracefully
        if 'connection_pool' in locals():
            connection_pool.close()
            print("\nDatabase connection pool closed.")
        elif pool:
            pool.close()
            print("\nDatabase connection pool closed.")
