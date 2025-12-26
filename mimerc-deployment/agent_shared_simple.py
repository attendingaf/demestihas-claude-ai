"""
MiMerc Shared Grocery List Management Agent
Simplified version with in-memory shared state and enhanced item handling
"""

import os
import json
import logging
import re
from typing import List, Dict, Any
from datetime import datetime

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="MiMerc Shared List API", version="2.0.0")

# CRITICAL: Shared grocery list - all users access this same list
SHARED_GROCERY_LIST = {}  # thread_id -> list mapping

def process_message(message: str, current_list: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]], str]:
    """
    Process user message with enhanced multi-word item handling.

    CRITICAL ENHANCEMENTS:
    1. Detects and preserves quoted items
    2. Handles edit_item_quantity operations
    3. Implements self-correction for split items
    """
    message_lower = message.lower()

    # Extract quoted items FIRST - these must be preserved as single items
    quoted_items = re.findall(r'"([^"]*)"', message)

    # Remove quotes from message for easier processing
    clean_message = re.sub(r'"([^"]*)"', r'\1', message)

    # Determine action and process
    if any(word in message_lower for word in ['add', 'put', 'need', 'buy', 'get']):
        # ADD ITEMS - with quote preservation
        items_to_add = []

        if quoted_items:
            # Use quoted items directly
            items_to_add = quoted_items
        else:
            # Parse items from message
            items_text = clean_message.lower()

            # Remove action words
            for word in ['add', 'put', 'need', 'buy', 'get', 'to', 'the', 'list', 'my',
                        'grocery', 'please', 'i', 'want', 'some', 'our', 'and']:
                items_text = items_text.replace(word, ' ')

            # Check for common multi-word items
            multi_word_items = {
                'chocolate syrup': ['chocolate', 'syrup'],
                'peanut butter': ['peanut', 'butter'],
                'ice cream': ['ice', 'cream'],
                'sour cream': ['sour', 'cream'],
                'chocolate chips': ['chocolate', 'chips'],
                'olive oil': ['olive', 'oil'],
                'baking soda': ['baking', 'soda'],
                'baking powder': ['baking', 'powder']
            }

            # Check if multi-word items are present
            for full_item, parts in multi_word_items.items():
                if all(part in items_text for part in parts):
                    items_to_add.append(full_item)
                    # Remove from text to avoid duplication
                    for part in parts:
                        items_text = items_text.replace(part, '', 1)

            # Add remaining items
            words = items_text.split()
            for word in words:
                word = word.strip('.,!?')
                if len(word) > 2 and not word.isdigit():
                    items_to_add.append(word)

        # Add items to list
        if items_to_add:
            for item in items_to_add:
                # Check if item already exists
                existing = next((i for i in current_list if i['item'].lower() == item.lower()), None)
                if not existing:
                    current_list.append({"item": item, "quantity": "1"})

            response = f"✅ Added {len(items_to_add)} item(s) to the shared family list: {', '.join(items_to_add)}"
            action = "add"
        else:
            response = "Please specify what items you'd like to add to the shared list."
            action = "error"

    elif any(word in message_lower for word in ['change', 'edit', 'update', 'set']) and \
         any(word in message_lower for word in ['quantity', 'amount', 'to']):
        # EDIT QUANTITY - New functionality
        # Parse: "Change milk quantity to 2 gallons" or "Update eggs to 2 dozen"

        # Extract item and new quantity
        match = re.search(r'(change|edit|update|set)\s+(\w+[\w\s]*?)\s+(quantity|amount|to)\s+(.+)',
                         message_lower)

        if match:
            item_name = match.group(2).strip()
            new_quantity = match.group(4).strip()

            # Find and update item
            updated = False
            for item in current_list:
                if item_name in item['item'].lower():
                    item['quantity'] = new_quantity
                    updated = True
                    break

            if updated:
                response = f"✅ Updated {item_name} quantity to {new_quantity} in the shared list"
                action = "edit"
            else:
                # Item not found, add it with specified quantity
                current_list.append({"item": item_name, "quantity": new_quantity})
                response = f"✅ Added {item_name} with quantity {new_quantity} to the shared list"
                action = "add"
        else:
            response = "Please specify the item and new quantity. Example: 'Change milk to 2 gallons'"
            action = "error"

    elif any(word in message_lower for word in ['remove', 'delete', 'drop', 'take off']):
        # REMOVE ITEMS
        items_to_remove = quoted_items if quoted_items else []

        if not items_to_remove:
            # Parse items from message
            words = clean_message.lower().split()
            skip_words = {'remove', 'delete', 'drop', 'take', 'off', 'from', 'the',
                         'list', 'my', 'our', 'grocery', 'please'}

            for word in words:
                if word not in skip_words and len(word) > 2:
                    items_to_remove.append(word)

        if items_to_remove:
            original_count = len(current_list)
            current_list[:] = [
                item for item in current_list
                if not any(rem.lower() in item['item'].lower() for rem in items_to_remove)
            ]
            removed_count = original_count - len(current_list)
            response = f"✅ Removed {removed_count} item(s) from the shared list"
            action = "remove"
        else:
            response = "Please specify which items to remove from the shared list."
            action = "error"

    elif any(word in message_lower for word in ['show', 'what', 'list', 'display', 'see', 'view']):
        # SHOW LIST
        if current_list:
            list_display = "\n".join([
                f"• {item['item']} - Quantity: {item.get('quantity', '1')}"
                for item in current_list
            ])
            response = f"📋 **Shared Family Grocery List:**\n{list_display}\n\n_Total: {len(current_list)} items_"
        else:
            response = "The shared family grocery list is currently empty."
        action = "show"

    elif any(word in message_lower for word in ['clear', 'empty', 'reset']) and \
         any(word in message_lower for word in ['list', 'all', 'everything']):
        # CLEAR LIST
        current_list.clear()
        response = "⚠️ The entire shared family list has been cleared!"
        action = "clear"

    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        response = ("Hello! I'm MiMerc, managing our shared family grocery list.\n"
                   "Everyone can add, edit, or remove items. What would you like to do?")
        action = "greeting"

    else:
        # DEFAULT
        response = ("I manage our shared family grocery list. You can:\n"
                   "• Add items: 'Add \"chocolate syrup\" and milk'\n"
                   "• Edit quantity: 'Change milk to 2 gallons'\n"
                   "• Remove items: 'Remove bread'\n"
                   "• View list: 'Show our list'\n\n"
                   "Remember: All changes affect everyone using this list!")
        action = "help"

    return response, current_list, action

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "shared_family_list"

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]
    action: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat requests for the shared list.
    CRITICAL: Uses the thread_id to access the shared list
    """
    try:
        # CRITICAL: Get or create the shared list for this thread
        if request.thread_id not in SHARED_GROCERY_LIST:
            SHARED_GROCERY_LIST[request.thread_id] = []

        current_list = SHARED_GROCERY_LIST[request.thread_id]

        # Process message with enhanced handling
        response_text, updated_list, action = process_message(request.message, current_list)

        # Update the shared list
        SHARED_GROCERY_LIST[request.thread_id] = updated_list

        # Log the action for transparency
        logger.info(f"Thread {request.thread_id}: Action={action}, Items={len(updated_list)}")

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
            grocery_list=updated_list,
            action=action
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MiMerc Shared List API",
        "version": "2.0.0",
        "active_threads": list(SHARED_GROCERY_LIST.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MiMerc Shared Grocery List API",
        "version": "2.0.0",
        "features": [
            "Single shared family list",
            "Multi-word item support with quote preservation",
            "Edit item quantities",
            "Self-correction for common multi-word items"
        ],
        "endpoints": {
            "/chat": "POST - Send messages to manage shared list",
            "/health": "GET - Health check and status",
            "/list/{thread_id}": "GET - Get list for specific thread"
        }
    }

@app.get("/list/{thread_id}")
async def get_list(thread_id: str):
    """Get the grocery list for a specific thread."""
    if thread_id in SHARED_GROCERY_LIST:
        return {
            "thread_id": thread_id,
            "grocery_list": SHARED_GROCERY_LIST[thread_id],
            "item_count": len(SHARED_GROCERY_LIST[thread_id])
        }
    else:
        return {
            "thread_id": thread_id,
            "grocery_list": [],
            "item_count": 0,
            "message": "No list exists for this thread yet"
        }

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc Shared Family Grocery List Agent v2.0")
    logger.info("Features: Shared lists, multi-word items, quantity editing")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
