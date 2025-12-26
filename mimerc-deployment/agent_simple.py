"""
MiMerc Grocery List Management Agent
Simple API version without state persistence
"""

import os
import json
import logging
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
app = FastAPI(title="MiMerc API", version="1.0.0")

# In-memory storage for grocery lists (per thread_id)
grocery_lists = {}

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]

def process_message(message: str, current_list: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
    """Process user message and update grocery list."""
    message_lower = message.lower()

    # Determine action based on keywords
    if any(word in message_lower for word in ['add', 'put', 'need', 'buy']):
        # Extract items to add (simple parsing)
        items_text = message.replace(',', ' ').replace('and', ' ')
        words = items_text.split()

        # Skip common words
        skip_words = {'add', 'put', 'need', 'buy', 'to', 'the', 'list', 'my', 'grocery', 'please', 'i', 'want', 'some'}
        items = []

        for word in words:
            if word.lower() not in skip_words and len(word) > 2:
                # Check if it's a quantity
                if any(char.isdigit() for char in word):
                    continue
                items.append(word)

        if items:
            for item in items:
                current_list.append({"item": item, "quantity": "1"})
            response = f"I've added {len(items)} item(s) to your grocery list: {', '.join(items)}"
        else:
            response = "I couldn't identify specific items to add. Please tell me what items you'd like to add."

    elif any(word in message_lower for word in ['remove', 'delete', 'drop']):
        # Extract items to remove
        items_text = message.replace(',', ' ').replace('and', ' ')
        words = items_text.split()
        skip_words = {'remove', 'delete', 'drop', 'from', 'the', 'list', 'my', 'grocery', 'please'}

        items_to_remove = []
        for word in words:
            if word.lower() not in skip_words and len(word) > 2:
                items_to_remove.append(word.lower())

        if items_to_remove:
            original_count = len(current_list)
            current_list[:] = [item for item in current_list if item['item'].lower() not in items_to_remove]
            removed_count = original_count - len(current_list)
            response = f"I've removed {removed_count} item(s) from your list."
        else:
            response = "Please specify which items you'd like to remove."

    elif any(word in message_lower for word in ['show', 'what', 'list', 'display', 'see']):
        # Show the current list
        if current_list:
            list_display = "\n".join([
                f"- {item['item']} (Quantity: {item.get('quantity', '1')})"
                for item in current_list
            ])
            response = f"Here's your current grocery list:\n{list_display}"
        else:
            response = "Your grocery list is currently empty. Would you like to add some items?"

    elif any(word in message_lower for word in ['clear', 'empty', 'reset']):
        # Clear the list
        current_list.clear()
        response = "I've cleared your grocery list. It's now empty."

    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        response = "Hello! I'm MiMerc, your grocery list assistant. I can help you add, remove, or view items in your grocery list. What would you like to do?"

    else:
        # Default response
        response = "I can help you manage your grocery list. You can:\n- Add items (e.g., 'Add milk and eggs')\n- Remove items (e.g., 'Remove eggs')\n- View your list (e.g., 'Show my list')\n- Clear the list (e.g., 'Clear my list')\n\nWhat would you like to do?"

    return response, current_list

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests."""
    try:
        # Get or create list for this thread
        if request.thread_id not in grocery_lists:
            grocery_lists[request.thread_id] = []

        current_list = grocery_lists[request.thread_id]

        # Process the message
        response_text, updated_list = process_message(request.message, current_list)

        # Update stored list
        grocery_lists[request.thread_id] = updated_list

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
            grocery_list=updated_list
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MiMerc API", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
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

@app.get("/lists")
async def get_all_lists():
    """Get all active grocery lists (for debugging)."""
    return {
        "active_threads": list(grocery_lists.keys()),
        "total_threads": len(grocery_lists)
    }

# Main execution
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc Grocery List Management Agent v1.0 (Simple)")
    logger.info("=" * 60)
    logger.info("Starting API server...")

    # Run the FastAPI app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
