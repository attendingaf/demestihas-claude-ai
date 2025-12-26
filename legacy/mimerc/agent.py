"""
MiMerc Shared Grocery List Management Agent
LLM-POWERED VERSION: Using LangGraph for intelligent intent parsing
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="MiMerc Shared List API - LLM Powered", version="4.0.0")

# CRITICAL: Shared grocery list - all users access this same list
SHARED_GROCERY_LIST = {}  # thread_id -> list mapping

class ActionType(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"
    SHOW = "show"
    CLEAR = "clear"
    UNKNOWN = "unknown"

class GroceryItem(BaseModel):
    """Structured representation of a grocery item"""
    name: str = Field(description="The name of the item (can be multi-word like 'english muffins')")
    quantity: Optional[str] = Field(default=None, description="The quantity needed - None means no specific quantity mentioned")
    notes: Optional[str] = Field(default=None, description="Any special notes about the item")
    added_by: Optional[str] = Field(default=None, description="User initial who added this item")

class ParsedIntent(BaseModel):
    """Structured output from LLM intent parsing"""
    action: ActionType = Field(description="The type of action to perform")
    items: List[GroceryItem] = Field(default_factory=list, description="List of items involved in the action")
    confidence: float = Field(description="Confidence score of the parsing (0-1)")
    reasoning: str = Field(description="Brief explanation of the parsing decision")
    user_initial: Optional[str] = Field(default=None, description="User's initial for tracking")

class GroceryState(TypedDict):
    """State for LangGraph workflow"""
    message: str
    parsed_intent: Optional[ParsedIntent]
    validation_errors: List[str]
    corrections_made: List[str]
    final_actions: List[Dict[str, Any]]
    current_list: List[Dict[str, Any]]
    response: str
    iteration_count: int
    user_initial: Optional[str]
    user_name: Optional[str]

class LLMIntentParser:
    """
    LLM-based Intent Parser using LangGraph for intelligent conversation understanding
    """

    def __init__(self):
        # Initialize LLM with structured output
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create structured output parser
        self.structured_llm = self.llm.with_structured_output(ParsedIntent)

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

        self.system_prompt = """You are an expert grocery list intent parser. Your job is to understand what the user wants to do with their grocery list.

Key Instructions:
1. ALWAYS treat multi-word items as single entities (e.g., "english muffins" is ONE item, not two)
2. Identify the primary action: add, remove, update (change quantity), show (display list), or clear (empty list)
3. Extract all grocery items mentioned, preserving their full names
4. IMPORTANT: Only set quantity if explicitly mentioned (e.g., "2 gallons", "3 pounds"). If no quantity is specified, leave it as None/null
5. Handle complex requests that may have multiple items or actions

Common multi-word grocery items to recognize:
- english muffins, chocolate syrup, peanut butter, ice cream, sour cream, cream cheese
- hot dogs, ground beef, chicken breast, lunch meat
- chocolate milk, almond milk, soy milk, heavy cream, cottage cheese, greek yogurt
- cherry tomatoes, bell peppers, green beans
- olive oil, baking soda, baking powder, tomato sauce, barbecue sauce
- apple juice, orange juice, maple syrup

Examples:
- "add english muffins and chocolate syrup" → ADD action with 2 items: ["english muffins" (no quantity), "chocolate syrup" (no quantity)]
- "we need milk, 2 dozen eggs, and bread" → ADD action with 3 items: ["milk" (no quantity), "eggs" (quantity: "2 dozen"), "bread" (no quantity)]
- "add 3 gallons of milk" → ADD action with 1 item: ["milk" (quantity: "3 gallons")]
- "remove the peanut butter from the list" → REMOVE action with 1 item: ["peanut butter"]
- "change milk quantity to 2 gallons" → UPDATE action with item "milk" and quantity "2 gallons"
- "what's on the list?" → SHOW action with no items

Provide high confidence (0.9-1.0) when the intent is clear, lower confidence (0.5-0.8) when ambiguous."""

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for intent parsing"""

        workflow = StateGraph(GroceryState)

        # Add nodes
        workflow.add_node("parse_intent", self.parse_intent_node)
        workflow.add_node("validate_intent", self.validate_intent_node)
        workflow.add_node("correct_intent", self.correct_intent_node)
        workflow.add_node("execute_actions", self.execute_actions_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # Add edges
        workflow.add_edge("parse_intent", "validate_intent")

        # Conditional routing based on validation
        workflow.add_conditional_edges(
            "validate_intent",
            self.should_correct,
            {
                "correct": "correct_intent",
                "execute": "execute_actions"
            }
        )

        workflow.add_edge("correct_intent", "validate_intent")
        workflow.add_edge("execute_actions", "generate_response")
        workflow.add_edge("generate_response", END)

        # Set entry point
        workflow.set_entry_point("parse_intent")

        return workflow.compile()

    async def parse_intent_node(self, state: GroceryState) -> GroceryState:
        """Parse user intent using LLM"""
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Parse this grocery list request: {state['message']}")
            ]

            parsed_intent = self.structured_llm.invoke(messages)
            state["parsed_intent"] = parsed_intent
            state["iteration_count"] = state.get("iteration_count", 0) + 1

            logger.info(f"LLM parsed intent: action={parsed_intent.action}, items={len(parsed_intent.items)}, confidence={parsed_intent.confidence}")

        except Exception as e:
            logger.error(f"Error in LLM parsing: {e}")
            # Fallback to a simple intent
            state["parsed_intent"] = ParsedIntent(
                action=ActionType.UNKNOWN,
                items=[],
                confidence=0.0,
                reasoning=f"Error parsing: {str(e)}"
            )

        return state

    async def validate_intent_node(self, state: GroceryState) -> GroceryState:
        """Validate the parsed intent for common issues"""
        state["validation_errors"] = []

        if not state.get("parsed_intent"):
            state["validation_errors"].append("No intent parsed")
            return state

        intent = state["parsed_intent"]

        # Check for suspicious item splits (e.g., "english" and "muffins" as separate items)
        if intent.action in [ActionType.ADD, ActionType.REMOVE]:
            items_lower = [item.name.lower() for item in intent.items]

            # Known problematic splits
            problematic_pairs = [
                ("english", "muffins"), ("chocolate", "syrup"), ("peanut", "butter"),
                ("ice", "cream"), ("sour", "cream"), ("cream", "cheese"),
                ("hot", "dogs"), ("ground", "beef"), ("chicken", "breast")
            ]

            for word1, word2 in problematic_pairs:
                if word1 in items_lower and word2 in items_lower:
                    combined = f"{word1} {word2}"
                    if combined in state["message"].lower():
                        state["validation_errors"].append(
                            f"Incorrectly split '{combined}' into separate items"
                        )

        # Validate confidence threshold
        if intent.confidence < 0.5 and state.get("iteration_count", 0) < 3:
            state["validation_errors"].append("Low confidence parsing, needs correction")

        return state

    async def correct_intent_node(self, state: GroceryState) -> GroceryState:
        """Use LLM to correct parsing errors"""
        if state.get("iteration_count", 0) >= 3:
            logger.warning("Max correction iterations reached")
            return state

        correction_prompt = f"""The previous parsing had these issues: {', '.join(state['validation_errors'])}

Original message: {state['message']}
Previous parsing: {state['parsed_intent'].model_dump_json() if state.get('parsed_intent') else 'None'}

Please reparse the message, being especially careful to:
1. Keep multi-word items together (e.g., "english muffins" is ONE item)
2. Ensure the action type is correct
3. Extract all items mentioned in the original message

Provide a corrected parsing with higher confidence."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=correction_prompt)
        ]

        try:
            corrected_intent = self.structured_llm.invoke(messages)
            state["parsed_intent"] = corrected_intent
            state["corrections_made"] = state.get("corrections_made", [])
            state["corrections_made"].append(f"Reparsed with confidence {corrected_intent.confidence}")

        except Exception as e:
            logger.error(f"Error in correction: {e}")

        return state

    def should_correct(self, state: GroceryState) -> str:
        """Decide whether to correct or execute based on validation"""
        if state.get("validation_errors") and state.get("iteration_count", 0) < 3:
            return "correct"
        return "execute"

    async def execute_actions_node(self, state: GroceryState) -> GroceryState:
        """Execute the parsed actions on the grocery list"""
        state["final_actions"] = []

        if not state.get("parsed_intent"):
            return state

        intent = state["parsed_intent"]
        current_list = state.get("current_list", [])

        if intent.action == ActionType.ADD:
            for item in intent.items:
                # Check if item already exists
                existing = next(
                    (i for i in current_list if i['item'].lower() == item.name.lower()),
                    None
                )
                if not existing:
                    new_item = {
                        "item": item.name,
                        "added_by": state.get("user_initial", "?")
                    }
                    # Only add quantity if explicitly specified
                    if item.quantity:
                        new_item["quantity"] = item.quantity
                    if item.notes:
                        new_item["notes"] = item.notes

                    current_list.append(new_item)

                    # Format action message based on whether quantity was specified
                    if item.quantity:
                        state["final_actions"].append(f"Added '{item.name}' (qty: {item.quantity})")
                    else:
                        state["final_actions"].append(f"Added '{item.name}'")
                else:
                    state["final_actions"].append(f"'{item.name}' already in list")

        elif intent.action == ActionType.REMOVE:
            for item in intent.items:
                original_len = len(current_list)
                current_list[:] = [
                    i for i in current_list
                    if i['item'].lower() != item.name.lower()
                ]
                if len(current_list) < original_len:
                    state["final_actions"].append(f"Removed '{item.name}'")

        elif intent.action == ActionType.UPDATE:
            for item in intent.items:
                for list_item in current_list:
                    if item.name.lower() in list_item['item'].lower():
                        list_item['quantity'] = item.quantity
                        state["final_actions"].append(
                            f"Updated '{item.name}' quantity to {item.quantity}"
                        )
                        break

        elif intent.action == ActionType.CLEAR:
            current_list.clear()
            state["final_actions"].append("Cleared entire list")

        state["current_list"] = current_list
        return state

    async def generate_response_node(self, state: GroceryState) -> GroceryState:
        """Generate natural language response - ALWAYS show list after changes"""
        intent = state.get("parsed_intent")

        # Helper function to format the list
        def format_list(items):
            if not items:
                return "📭 <i>List is empty</i>"

            list_display = "\n".join([
                f"• {item['item']}"
                + (f" - {item['quantity']}" if item.get('quantity') else "")
                + (f" 📝 {item['notes']}" if item.get('notes') else "")
                + f" <i>[{item.get('added_by', '?')}]</i>"
                for item in items
            ])
            return list_display

        # Build response based on action
        if intent and intent.action == ActionType.SHOW:
            # Just show the list
            if state.get("current_list"):
                state["response"] = f"📋 <b>Current Grocery List</b> ({len(state['current_list'])} items):\n\n{format_list(state['current_list'])}"
            else:
                state["response"] = "📋 <b>Current Grocery List</b>:\n\n📭 <i>The list is empty. Add some items!</i>"

        elif state.get("final_actions"):
            # Show what changed + the updated list
            action_summary = "\n".join([f"✓ {action}" for action in state["final_actions"]])

            # Build response with action confirmation + current list
            response_parts = [
                "<b>✅ Changes Applied:</b>",
                action_summary,
                "",
                "<b>📋 Updated List</b> " + f"({len(state.get('current_list', []))} items):",
                format_list(state.get("current_list", []))
            ]

            # Add AI note if corrections were made
            if state.get("corrections_made"):
                response_parts.append("\n<i>🤖 AI auto-corrected multi-word items</i>")

            state["response"] = "\n".join(response_parts)

        elif intent and intent.action == ActionType.CLEAR:
            # Special case for clear action
            state["response"] = "🗑️ <b>List Cleared!</b>\n\n📋 <b>Current List</b>:\n📭 <i>The list is now empty</i>"

        elif intent and intent.action == ActionType.UNKNOWN:
            # Unknown request - still show current list for context
            current_list_text = format_list(state.get("current_list", []))
            state["response"] = (
                "❓ I couldn't understand that request.\n"
                "Try: 'Add milk and eggs' or 'Remove butter'\n\n"
                f"<b>📋 Current List</b> ({len(state.get('current_list', []))} items):\n{current_list_text}"
            )

        else:
            # No changes - show current list
            state["response"] = f"ℹ️ No changes made.\n\n<b>📋 Current List</b> ({len(state.get('current_list', []))} items):\n{format_list(state.get('current_list', []))}"

        return state

    async def process_message(self, message: str, current_list: List[Dict[str, Any]], user_initial: str = "?", user_name: str = "User") -> Tuple[str, List[Dict[str, Any]], str]:
        """Main entry point for processing messages"""

        # Initialize state
        initial_state: GroceryState = {
            "message": message,
            "parsed_intent": None,
            "validation_errors": [],
            "corrections_made": [],
            "final_actions": [],
            "current_list": current_list.copy(),
            "response": "",
            "iteration_count": 0,
            "user_initial": user_initial,
            "user_name": user_name
        }

        # Run the workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            action = final_state["parsed_intent"].action.value if final_state.get("parsed_intent") else "unknown"

            return (
                final_state["response"],
                final_state["current_list"],
                action
            )
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            return (
                "Sorry, I encountered an error processing your request.",
                current_list,
                "error"
            )

# Global parser instance
llm_parser = None

def get_llm_parser():
    """Get or create the LLM parser instance"""
    global llm_parser
    if llm_parser is None:
        llm_parser = LLMIntentParser()
    return llm_parser

# API Endpoints

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "shared_family_list"
    user_initial: str = "?"
    user_name: str = "User"

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]
    action: str
    llm_powered: bool = True

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat requests with LLM-powered intent parsing
    """
    try:
        # Get or create the shared list
        if request.thread_id not in SHARED_GROCERY_LIST:
            SHARED_GROCERY_LIST[request.thread_id] = []

        current_list = SHARED_GROCERY_LIST[request.thread_id]

        # Get parser instance
        parser = get_llm_parser()

        # Process with LLM
        response_text, updated_list, action = await parser.process_message(
            request.message, current_list, request.user_initial, request.user_name
        )

        # Update the shared list
        SHARED_GROCERY_LIST[request.thread_id] = updated_list

        logger.info(f"LLM Processed: action={action}, items={len(updated_list)}")

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
            grocery_list=updated_list,
            action=action,
            llm_powered=True
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MiMerc LLM-Powered API",
        "version": "4.0.0",
        "features": [
            "LLM-based intent parsing",
            "LangGraph workflow orchestration",
            "Structured output with Pydantic",
            "Self-correcting validation loop",
            "Natural language understanding"
        ],
        "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MiMerc Shared Grocery List API - LLM POWERED",
        "version": "4.0.0",
        "improvements": [
            "🧠 LLM-based natural language understanding",
            "🔄 LangGraph workflow for intelligent processing",
            "📊 Structured output with confidence scores",
            "🔧 Self-correcting validation loop",
            "🌍 Handles any language or phrasing",
            "💡 Zero-shot learning for new item types"
        ],
        "powered_by": "OpenAI GPT + LangGraph"
    }

@app.get("/debug/model-info")
async def get_model_info():
    """Debug endpoint to check LLM configuration"""
    return {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "langgraph_version": "0.2.0+",
        "parser_initialized": llm_parser is not None
    }

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc LLM-POWERED - Natural Language Understanding v4.0")
    logger.info(f"Using model: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    logger.info("Features: LangGraph, structured output, self-correction")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
