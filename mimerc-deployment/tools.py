"""
MiMerc Tools Module
Provides tool functions for grocery list management with proper state updates
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
def add_items_to_list(items: List[str], quantities: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Add items to the grocery list.

    IMPORTANT: When handling quoted items like "chocolate syrup",
    treat them as single items, not separate words.

    Args:
        items: List of item names to add
        quantities: Optional list of quantities corresponding to each item

    Returns:
        Dictionary with updated grocery list for state persistence
    """
    if quantities is None:
        quantities = ["1"] * len(items)

    # This will be populated by the tool executor
    result_items = []
    for i, item in enumerate(items):
        qty = quantities[i] if i < len(quantities) else "1"
        result_items.append({
            "item": item,
            "quantity": qty,
            "added_by": "system"  # Will be updated by agent
        })

    return {
        "action": "add",
        "items_processed": result_items,
        "message": f"Added {len(items)} item(s) to the grocery list"
    }

@tool
def remove_items_from_list(items: List[str]) -> Dict[str, Any]:
    """
    Remove items from the grocery list.

    Args:
        items: List of item names to remove

    Returns:
        Dictionary with action details for state update
    """
    return {
        "action": "remove",
        "items_to_remove": items,
        "message": f"Requested removal of {len(items)} item(s)"
    }

@tool
def edit_item_quantity(item: str, new_quantity: str) -> Dict[str, Any]:
    """
    Edit the quantity of a specific item in the grocery list.

    CRITICAL: This tool allows users to update quantities without removing/re-adding items.
    Essential for maintaining list integrity and proper state management.

    Args:
        item: The name of the item to update
        new_quantity: The new quantity value (e.g., "2 gallons", "500g", "3")

    Returns:
        Dictionary with update information for state persistence
    """
    return {
        "action": "edit_quantity",
        "item": item,
        "new_quantity": new_quantity,
        "message": f"Updated quantity of {item} to {new_quantity}"
    }

@tool
def get_grocery_list() -> Dict[str, Any]:
    """
    Get the current grocery list.

    Returns:
        Dictionary indicating list should be retrieved from state
    """
    return {
        "action": "get_list",
        "message": "Retrieving current grocery list from state"
    }

@tool
def clear_entire_list() -> Dict[str, Any]:
    """
    Clear the entire grocery list.
    WARNING: This affects all users sharing the list!

    Returns:
        Dictionary with clear action for state update
    """
    return {
        "action": "clear",
        "message": "Clearing entire grocery list (affects all users)"
    }

@tool
def search_item_in_list(search_term: str) -> Dict[str, Any]:
    """
    Search for items in the grocery list.

    Args:
        search_term: Term to search for in item names

    Returns:
        Dictionary with search parameters
    """
    return {
        "action": "search",
        "search_term": search_term,
        "message": f"Searching for items containing: {search_term}"
    }

def process_tool_result(tool_result: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process tool results and update the agent state accordingly.

    CRITICAL: This function ensures tool outputs properly update the grocery_list
    in AgentState, which is then persisted by PostgresSaver.

    Args:
        tool_result: The result from a tool execution
        current_state: The current agent state

    Returns:
        Updated state dictionary with modified grocery_list
    """
    action = tool_result.get("action")
    current_list = current_state.get("grocery_list", [])

    if action == "add":
        # Add new items to the list
        items_to_add = tool_result.get("items_processed", [])
        for item in items_to_add:
            # Check if item already exists
            existing = next((i for i in current_list if i["item"].lower() == item["item"].lower()), None)
            if existing:
                # Update quantity if item exists
                existing["quantity"] = f"{existing.get('quantity', '1')}, {item.get('quantity', '1')}"
            else:
                current_list.append(item)

        return {"grocery_list": current_list}

    elif action == "remove":
        # Remove items from the list
        items_to_remove = [item.lower() for item in tool_result.get("items_to_remove", [])]
        updated_list = [
            item for item in current_list
            if item["item"].lower() not in items_to_remove
        ]
        return {"grocery_list": updated_list}

    elif action == "edit_quantity":
        # Update quantity of specific item
        item_name = tool_result.get("item", "").lower()
        new_quantity = tool_result.get("new_quantity", "1")

        for item in current_list:
            if item["item"].lower() == item_name:
                item["quantity"] = new_quantity
                break
        else:
            # Item not found, add it with the specified quantity
            current_list.append({
                "item": tool_result.get("item"),
                "quantity": new_quantity
            })

        return {"grocery_list": current_list}

    elif action == "clear":
        # Clear the entire list
        return {"grocery_list": []}

    elif action == "search":
        # Search doesn't modify state, just returns filtered view
        search_term = tool_result.get("search_term", "").lower()
        filtered = [
            item for item in current_list
            if search_term in item["item"].lower()
        ]
        return {
            "search_results": filtered,
            "grocery_list": current_list  # Keep original list intact
        }

    # Default: return current state unchanged
    return {"grocery_list": current_list}
