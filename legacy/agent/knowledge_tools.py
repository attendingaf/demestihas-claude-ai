"""
Knowledge Retrieval Tools for General Agent

These LangChain tools wrap FalkorDB query functions to enable the general agent
to retrieve stored knowledge about users when explicitly asked.

This solves the critical bug where the general agent claimed it didn't know
anything about the user despite having persistent knowledge available.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR TOOL ARGUMENTS
# ============================================================================


class KnowledgeSearchInput(BaseModel):
    """Input schema for retrieving user knowledge from the knowledge graph."""

    user_id: str = Field(
        description="The unique identifier for the user whose knowledge to retrieve."
    )
    limit: int = Field(
        default=10,
        description="Maximum number of knowledge facts to retrieve (default: 10, max: 20)",
    )


class EntitySearchInput(BaseModel):
    """Input schema for searching entities by keyword."""

    keyword: str = Field(
        description="The search term or keyword to find related entities and concepts."
    )
    limit: int = Field(
        default=5, description="Maximum number of entities to return (default: 5)"
    )


# ============================================================================
# KNOWLEDGE RETRIEVAL TOOLS
# ============================================================================


async def get_user_knowledge_async(user_id: str, limit: int = 10) -> List[str]:
    """
    Async implementation: Retrieves structured knowledge triples about a user.

    This function queries FalkorDB for all knowledge facts stored about the user,
    formatted as human-readable statements.

    Args:
        user_id: User identifier
        limit: Maximum number of facts to retrieve

    Returns:
        List of human-readable knowledge statements
    """
    try:
        # Import here to avoid circular dependency
        from falkordb_manager import FalkorDBManager

        manager = FalkorDBManager()

        # Check connection
        if not manager.is_connected():
            await manager.connect()

        # Retrieve knowledge triples
        triples = await manager.get_user_knowledge_triples(
            user_id=user_id,
            limit=min(limit, 20),  # Cap at 20 for performance
        )

        if not triples:
            return ["No stored knowledge found for this user."]

        # Format triples as human-readable statements
        knowledge_statements = []
        for triple in triples:
            subject = triple.get("subject", "Unknown")
            predicate = triple.get("predicate", "RELATED_TO")
            obj = triple.get("object", "Unknown")
            confidence = triple.get("confidence", 0.0)

            # Format predicate as human-readable
            predicate_readable = predicate.replace("_", " ").lower()

            statement = (
                f"{subject} {predicate_readable} {obj} (confidence: {confidence:.2f})"
            )
            knowledge_statements.append(statement)

        logger.info(
            f"✅ Retrieved {len(knowledge_statements)} knowledge facts for user {user_id}"
        )
        return knowledge_statements

    except Exception as e:
        logger.error(f"Failed to retrieve user knowledge: {str(e)}")
        return [f"Error retrieving knowledge: {str(e)}"]


def get_user_knowledge(user_id: str, limit: int = 10) -> str:
    """
    Synchronous wrapper: Retrieves specific, structured facts about a user from FalkorDB.

    **USE THIS TOOL** when the user asks direct questions like:
    - "What do you know about me?"
    - "Tell me some facts about me"
    - "What information do you have stored?"

    This tool queries the persistent knowledge graph to retrieve stored facts,
    preferences, and relationships associated with the user.

    Args:
        user_id: The unique identifier for the user
        limit: Maximum number of facts to retrieve (default: 10)

    Returns:
        Formatted string containing user knowledge facts
    """
    try:
        # Check if there's a running event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in async context - cannot use asyncio.run()
            logger.debug(
                "get_user_knowledge called from async context - using thread pool workaround"
            )

            # As a workaround, run in a thread pool to avoid blocking
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(get_user_knowledge_async(user_id, limit))
                )
                knowledge_list = future.result(timeout=10)
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            knowledge_list = asyncio.run(get_user_knowledge_async(user_id, limit))

        if not knowledge_list or knowledge_list[0].startswith("No stored knowledge"):
            return "I don't have any stored knowledge about you yet. As we interact, I'll learn and remember important facts about your preferences and context."

        # Format as numbered list
        formatted_knowledge = (
            "Here's what I know about you from our previous interactions:\n\n"
        )
        for i, fact in enumerate(knowledge_list, 1):
            formatted_knowledge += f"{i}. {fact}\n"

        return formatted_knowledge.strip()

    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}")
        return f"I encountered an error while retrieving your information: {str(e)}"


async def search_entities_async(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Async implementation: Searches for entities matching a keyword.

    Args:
        keyword: Search term
        limit: Maximum entities to return

    Returns:
        List of entity dictionaries
    """
    try:
        from falkordb_manager import FalkorDBManager

        manager = FalkorDBManager()

        if not manager.is_connected():
            await manager.connect()

        entities = await manager.search_entities_by_keyword(
            keyword=keyword, limit=limit
        )

        return entities

    except Exception as e:
        logger.error(f"Failed to search entities: {str(e)}")
        return []


def search_knowledge_entities(keyword: str, limit: int = 5) -> str:
    """
    Searches the knowledge graph for entities and concepts matching a keyword.

    Use this tool when the user asks about specific topics, concepts, or entities
    that might be stored in the knowledge graph.

    Args:
        keyword: The search term or concept to look for
        limit: Maximum number of entities to return (default: 5)

    Returns:
        Formatted string with matching entities and their relationships
    """
    try:
        entities = asyncio.run(search_entities_async(keyword, limit))

        if not entities:
            return f"No entities found matching '{keyword}' in the knowledge graph."

        formatted_results = f"Found {len(entities)} entities matching '{keyword}':\n\n"
        for entity in entities:
            name = entity.get("name", "Unknown")
            entity_type = entity.get("type", "unknown")
            related_count = entity.get("related_count", 0)

            formatted_results += (
                f"- **{name}** (type: {entity_type}, {related_count} relationships)\n"
            )

        return formatted_results.strip()

    except Exception as e:
        logger.error(f"Entity search tool failed: {str(e)}")
        return f"Error searching entities: {str(e)}"


# ============================================================================
# TOOL DEFINITIONS FOR LANGCHAIN
# ============================================================================

# Define tools that can be bound to LLMs
GENERAL_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_knowledge",
            "description": (
                "Retrieves specific, structured facts and knowledge stored about the user "
                "from the persistent knowledge graph. Use this when the user asks what you "
                "know about them, or requests facts about themselves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The unique identifier for the user",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of facts to retrieve (default: 10, max: 20)",
                        "default": 10,
                    },
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_entities",
            "description": (
                "Searches the knowledge graph for entities and concepts matching a keyword. "
                "Use this when the user asks about specific topics that might be stored."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "The search term or concept to look for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entities to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["keyword"],
            },
        },
    },
]


# ============================================================================
# TOOL EXECUTION DISPATCHER
# ============================================================================


def execute_knowledge_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Executes a knowledge retrieval tool by name.

    This dispatcher is called by the general_agent_logic when the LLM
    requests to use a tool.

    Args:
        tool_name: Name of the tool to execute
        arguments: Dictionary of tool arguments

    Returns:
        Tool execution result as string
    """
    if tool_name == "get_user_knowledge":
        return get_user_knowledge(**arguments)
    elif tool_name == "search_knowledge_entities":
        return search_knowledge_entities(**arguments)
    else:
        return f"Unknown tool: {tool_name}"
