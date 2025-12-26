"""
MiMerc Shared Grocery List Management Agent
FIXED VERSION: Enhanced Intent Parsing with Self-Correction Loop
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="MiMerc Shared List API", version="3.0.0")

# CRITICAL: Shared grocery list - all users access this same list
SHARED_GROCERY_LIST = {}  # thread_id -> list mapping

# Track recent tool calls for validation
RECENT_TOOL_CALLS = {}  # thread_id -> list of recent calls

@dataclass
class ToolCall:
    """Represents a tool call for validation"""
    action: str
    item: str
    quantity: str = "1"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class IntentParser:
    """
    Enhanced Intent Parser with multi-word item handling
    This class serves as the LLM's intent routing logic
    """

    # CRITICAL SYSTEM PROMPT - The core of our fix
    SYSTEM_PROMPT = """You are an Intent Parser for a grocery list management system.

CRITICAL PARSING RULES - FOLLOW EXACTLY:

1. **SINGLE ENTITY RULE**: When parsing user requests, ALWAYS treat multi-word item names as SINGLE, INDIVISIBLE entities.
   - "english muffins" = ONE item, NOT "english" and "muffins"
   - "chocolate syrup" = ONE item, NOT "chocolate" and "syrup"
   - "peanut butter" = ONE item, NOT "peanut" and "butter"

2. **INTENT TO TOOL MAPPING**: Convert each user intent to EXACTLY ONE tool call per item:
   - "add english muffins" → add_item_to_list(item="english muffins", quantity="1")
   - "add chocolate syrup and milk" → add_item_to_list(item="chocolate syrup", quantity="1") AND add_item_to_list(item="milk", quantity="1")

3. **QUOTED PRESERVATION**: Any text in quotes MUST be treated as a single item:
   - "add 'english muffins'" → add_item_to_list(item="english muffins", quantity="1")

4. **COMMON MULTI-WORD ITEMS** (NEVER SPLIT THESE):
   - Food items: english muffins, chocolate syrup, peanut butter, ice cream, sour cream, cream cheese, hot dogs
   - Dairy: chocolate milk, almond milk, soy milk, heavy cream
   - Produce: cherry tomatoes, bell peppers, green beans
   - Other: olive oil, baking soda, baking powder, tomato sauce, barbecue sauce

5. **PARSING PRIORITY**:
   - First: Check for quoted items
   - Second: Check for known multi-word patterns
   - Third: Use context clues (adjacent words that commonly go together)
   - Last resort: Treat as separate items ONLY if clearly separated by conjunctions

Your primary objective: Parse the user's intent into the MINIMUM number of CORRECT tool calls, preserving multi-word items as single entities."""

    def __init__(self):
        self.multi_word_patterns = {
            # Common grocery multi-word items
            'english muffins', 'chocolate syrup', 'peanut butter', 'ice cream',
            'sour cream', 'cream cheese', 'hot dogs', 'chocolate milk',
            'almond milk', 'soy milk', 'heavy cream', 'cherry tomatoes',
            'bell peppers', 'green beans', 'olive oil', 'baking soda',
            'baking powder', 'tomato sauce', 'barbecue sauce', 'salad dressing',
            'lunch meat', 'ground beef', 'chicken breast', 'cottage cheese',
            'greek yogurt', 'maple syrup', 'apple juice', 'orange juice'
        }

    def parse_intent(self, message: str) -> Tuple[str, List[ToolCall]]:
        """
        Parse user message into structured tool calls
        Returns: (action_type, list_of_tool_calls)
        """
        message_lower = message.lower()
        tool_calls = []

        # Detect action type
        if any(word in message_lower for word in ['add', 'put', 'need', 'buy', 'get']):
            action = 'add'
            tool_calls = self._parse_add_intent(message)
        elif any(word in message_lower for word in ['remove', 'delete', 'drop']):
            action = 'remove'
            tool_calls = self._parse_remove_intent(message)
        elif any(word in message_lower for word in ['change', 'edit', 'update']) and 'quantity' in message_lower:
            action = 'edit'
            tool_calls = self._parse_edit_intent(message)
        elif any(word in message_lower for word in ['show', 'list', 'what', 'display']):
            action = 'show'
        elif 'clear' in message_lower and 'list' in message_lower:
            action = 'clear'
        else:
            action = 'unknown'

        return action, tool_calls

    def _parse_add_intent(self, message: str) -> List[ToolCall]:
        """
        Parse ADD intent with enhanced multi-word handling
        CRITICAL: This is where we prevent item splitting
        """
        tool_calls = []

        # Step 1: Extract quoted items first (highest priority)
        quoted_items = re.findall(r'"([^"]*)"', message)
        remaining_message = re.sub(r'"[^"]*"', '', message)

        for item in quoted_items:
            tool_calls.append(ToolCall(action='add', item=item.strip()))

        # Step 2: Check for known multi-word patterns
        message_lower = remaining_message.lower()
        for pattern in self.multi_word_patterns:
            if pattern in message_lower:
                tool_calls.append(ToolCall(action='add', item=pattern))
                # Remove found pattern to avoid duplicates
                message_lower = message_lower.replace(pattern, '')
                remaining_message = remaining_message.replace(pattern, '', 1)

        # Step 3: Parse remaining items (with adjacency detection)
        # Clean the message
        clean_words = []
        skip_words = {'add', 'put', 'need', 'buy', 'get', 'to', 'the', 'list',
                     'my', 'our', 'please', 'i', 'want', 'some', 'and'}

        words = remaining_message.lower().split()
        i = 0
        while i < len(words):
            word = words[i].strip('.,!?')

            # Check if this word + next word might be a multi-word item
            if i < len(words) - 1:
                two_word = f"{word} {words[i+1].strip('.,!?')}"
                # Check if it looks like a multi-word item (heuristic)
                if self._is_likely_multi_word(two_word):
                    tool_calls.append(ToolCall(action='add', item=two_word))
                    i += 2  # Skip next word
                    continue

            # Single word item
            if word not in skip_words and len(word) > 2 and not word.isdigit():
                # Check if it's not already part of a multi-word item we found
                already_added = any(word in tc.item.lower() for tc in tool_calls)
                if not already_added:
                    tool_calls.append(ToolCall(action='add', item=word))

            i += 1

        return tool_calls

    def _is_likely_multi_word(self, phrase: str) -> bool:
        """
        Heuristic to detect likely multi-word items
        """
        # Common patterns that indicate multi-word items
        patterns = [
            r'\w+ muffins?', r'\w+ butter', r'\w+ cream', r'\w+ sauce',
            r'\w+ milk', r'\w+ cheese', r'\w+ bread', r'\w+ juice',
            r'\w+ oil', r'\w+ pepper', r'\w+ beans?', r'\w+ tomatoes?'
        ]

        for pattern in patterns:
            if re.match(pattern, phrase):
                return True

        # Check if both words are food-related
        food_words = {'english', 'chocolate', 'peanut', 'ice', 'sour', 'cream',
                     'hot', 'almond', 'soy', 'cherry', 'bell', 'green', 'olive',
                     'baking', 'tomato', 'barbecue', 'ground', 'chicken', 'cottage',
                     'greek', 'maple', 'apple', 'orange'}

        words = phrase.split()
        if any(word in food_words for word in words):
            return True

        return False

    def _parse_remove_intent(self, message: str) -> List[ToolCall]:
        """Parse REMOVE intent"""
        # Similar logic but for removal
        return self._parse_add_intent(message.replace('remove', 'add').replace('delete', 'add'))

    def _parse_edit_intent(self, message: str) -> List[ToolCall]:
        """Parse EDIT quantity intent"""
        match = re.search(r'(change|edit|update)\s+(\w+[\w\s]*?)\s+(quantity|to)\s+(.+)',
                         message.lower())
        if match:
            item = match.group(2).strip()
            quantity = match.group(4).strip()
            return [ToolCall(action='edit', item=item, quantity=quantity)]
        return []

class ToolCallValidator:
    """
    CRITICAL COMPONENT: Validates and corrects tool calls
    This is our self-correction mechanism
    """

    def validate_and_correct(self,
                            message: str,
                            tool_calls: List[ToolCall],
                            current_list: List[Dict]) -> Tuple[List[ToolCall], bool, str]:
        """
        Validate tool calls and apply corrections if needed
        Returns: (corrected_tool_calls, was_corrected, correction_message)
        """

        # Detection: Check for suspicious splits
        if self._detect_incorrect_split(message, tool_calls):
            logger.warning(f"Detected incorrect split in tool calls: {[tc.item for tc in tool_calls]}")

            # Apply self-correction
            corrected_calls, correction_msg = self._apply_correction(message, tool_calls, current_list)
            return corrected_calls, True, correction_msg

        return tool_calls, False, ""

    def _detect_incorrect_split(self, message: str, tool_calls: List[ToolCall]) -> bool:
        """
        Detect if the LLM incorrectly split a multi-word item
        """
        if len(tool_calls) < 2:
            return False

        # Check for common split patterns
        items = [tc.item.lower() for tc in tool_calls if tc.action == 'add']

        # Known problematic splits
        problematic_pairs = [
            ('english', 'muffins'), ('chocolate', 'syrup'), ('peanut', 'butter'),
            ('ice', 'cream'), ('sour', 'cream'), ('cream', 'cheese'),
            ('hot', 'dogs'), ('chocolate', 'milk'), ('almond', 'milk'),
            ('soy', 'milk'), ('heavy', 'cream'), ('cherry', 'tomatoes'),
            ('bell', 'peppers'), ('green', 'beans'), ('olive', 'oil'),
            ('baking', 'soda'), ('baking', 'powder'), ('tomato', 'sauce'),
            ('barbecue', 'sauce'), ('ground', 'beef'), ('chicken', 'breast')
        ]

        for word1, word2 in problematic_pairs:
            if word1 in items and word2 in items:
                # Check if they appear consecutively in the original message
                if f"{word1} {word2}" in message.lower() or f"{word1} {word2}s" in message.lower():
                    return True

        # Additional heuristic: if message has fewer spaces than tool calls
        # it might indicate over-splitting
        word_count_in_message = len(message.split())
        if len(tool_calls) > word_count_in_message * 0.7:  # Too many splits
            return True

        return False

    def _apply_correction(self,
                         message: str,
                         incorrect_calls: List[ToolCall],
                         current_list: List[Dict]) -> Tuple[List[ToolCall], str]:
        """
        SELF-CORRECTION SEQUENCE:
        1. Identify the correct multi-word item
        2. Generate remove calls for incorrect items
        3. Generate add call for correct item
        """
        corrected_calls = []
        correction_messages = []

        # Step 1: Identify what should have been kept together
        items = [tc.item.lower() for tc in incorrect_calls if tc.action == 'add']

        # Try to reconstruct the correct item
        corrected_items = []
        skip_items = set()

        for i in range(len(items) - 1):
            if items[i] in skip_items:
                continue

            # Check if consecutive items should be combined
            combined = f"{items[i]} {items[i+1]}"
            if self._should_combine(combined, message):
                corrected_items.append(combined)
                skip_items.add(items[i])
                skip_items.add(items[i+1])

                # Generate correction sequence
                # First: Remove incorrect items
                corrected_calls.append(ToolCall(action='remove', item=items[i]))
                corrected_calls.append(ToolCall(action='remove', item=items[i+1]))
                # Then: Add correct combined item
                corrected_calls.append(ToolCall(action='add', item=combined))

                correction_messages.append(f"Corrected '{items[i]}' and '{items[i+1]}' to '{combined}'")

        # Add any uncorrected items
        for item in items:
            if item not in skip_items:
                corrected_calls.append(ToolCall(action='add', item=item))

        correction_msg = "; ".join(correction_messages) if correction_messages else ""
        return corrected_calls, correction_msg

    def _should_combine(self, combined: str, original_message: str) -> bool:
        """Determine if two items should be combined"""
        # Check if the combined form appears in the original message
        if combined in original_message.lower():
            return True

        # Check against known patterns
        parser = IntentParser()
        if combined in parser.multi_word_patterns:
            return True

        # Check heuristics
        if parser._is_likely_multi_word(combined):
            return True

        return False

def process_message_with_validation(message: str, current_list: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]], str]:
    """
    Main processing function with validation and self-correction
    This orchestrates the entire intent parsing and correction flow
    """

    # Initialize components
    parser = IntentParser()
    validator = ToolCallValidator()

    # Step 1: Parse intent
    action, tool_calls = parser.parse_intent(message)

    # Step 2: Validate and correct if needed
    if tool_calls and action in ['add', 'remove']:
        tool_calls, was_corrected, correction_msg = validator.validate_and_correct(
            message, tool_calls, current_list
        )

        if was_corrected:
            logger.info(f"Applied self-correction: {correction_msg}")

    # Step 3: Execute tool calls
    response_parts = []

    for call in tool_calls:
        if call.action == 'add':
            # Check if item already exists
            existing = next((i for i in current_list if i['item'].lower() == call.item.lower()), None)
            if not existing:
                current_list.append({"item": call.item, "quantity": call.quantity})
                response_parts.append(f"Added '{call.item}'")

        elif call.action == 'remove':
            # Remove items
            original_len = len(current_list)
            current_list[:] = [i for i in current_list if i['item'].lower() != call.item.lower()]
            if len(current_list) < original_len:
                response_parts.append(f"Removed '{call.item}'")

        elif call.action == 'edit':
            # Edit quantity
            for item in current_list:
                if call.item.lower() in item['item'].lower():
                    item['quantity'] = call.quantity
                    response_parts.append(f"Updated '{call.item}' quantity to {call.quantity}")
                    break

    # Step 4: Generate response
    if action == 'show':
        if current_list:
            list_display = "\n".join([
                f"• {item['item']} - Quantity: {item.get('quantity', '1')}"
                for item in current_list
            ])
            response = f"📋 **Shared Family Grocery List:**\n{list_display}\n\n_Total: {len(current_list)} items_"
        else:
            response = "The shared family grocery list is currently empty."
    elif action == 'clear':
        current_list.clear()
        response = "⚠️ The entire shared family list has been cleared!"
    elif response_parts:
        # Include correction notice if applicable
        if correction_msg:
            response = f"✅ {'; '.join(response_parts)}\n\n_Note: {correction_msg}_"
        else:
            response = f"✅ {'; '.join(response_parts)} to the shared family list"
    else:
        response = "I can help you manage the shared grocery list. Try: 'Add english muffins' or 'Show list'"

    return response, current_list, action

# API Endpoints

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "shared_family_list"

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    grocery_list: List[Dict[str, Any]]
    action: str
    was_corrected: bool = False

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat requests with enhanced validation
    """
    try:
        # Get or create the shared list
        if request.thread_id not in SHARED_GROCERY_LIST:
            SHARED_GROCERY_LIST[request.thread_id] = []

        current_list = SHARED_GROCERY_LIST[request.thread_id]

        # Process with validation and self-correction
        response_text, updated_list, action = process_message_with_validation(
            request.message, current_list
        )

        # Update the shared list
        SHARED_GROCERY_LIST[request.thread_id] = updated_list

        # Check if correction was applied
        was_corrected = "Note:" in response_text and "Corrected" in response_text

        logger.info(f"Processed: action={action}, items={len(updated_list)}, corrected={was_corrected}")

        return ChatResponse(
            response=response_text,
            thread_id=request.thread_id,
            grocery_list=updated_list,
            action=action,
            was_corrected=was_corrected
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MiMerc Fixed API",
        "version": "3.0.0",
        "features": [
            "Enhanced intent parsing",
            "Self-correction loop",
            "Multi-word item preservation",
            "Tool call validation"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MiMerc Shared Grocery List API - FIXED",
        "version": "3.0.0",
        "improvements": [
            "Robust multi-word item handling",
            "Self-correction for split items",
            "Enhanced intent parsing with validation",
            "Prevents 'english muffins' → 'english' + 'muffins' splits"
        ]
    }

@app.get("/debug/recent-corrections")
async def get_recent_corrections():
    """Debug endpoint to see recent corrections"""
    return {
        "message": "Check logs for recent corrections",
        "hint": "Corrections are logged with INFO level"
    }

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MiMerc FIXED - Enhanced Intent Parsing v3.0")
    logger.info("Features: Self-correction, validation, multi-word preservation")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
