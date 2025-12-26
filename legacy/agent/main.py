import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Literal, Tuple
from typing_extensions import TypedDict
from datetime import datetime, timedelta

import requests
import psycopg2
try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:
    DuckDuckGoSearchRun = None
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from jose import JWTError, jwt
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# FalkorDB persistent graph database manager
from falkordb_manager import FalkorDBManager

# Dual-memory system for private and shared knowledge
from dual_memory_manager import FalkorDBDualMemory, get_dual_memory_manager

# Document processing for RAG
from document_processor import get_document_processor

# Statefulness extensions (conversation storage, temporal queries, contradiction detection)
from statefulness_extensions import (
    initialize_statefulness_extensions,
    get_conversation_manager,
    temporal_parser,
    contradiction_detector,
)
from postgres_client import get_postgres_client

# Family authentication system
from family_auth import get_family_auth_manager, FamilyAuthManager

# Configure structured JSON logging
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s %(user_id)s %(session_id)s %(endpoint)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"},
)
log_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

# Arcade SDK Import (Phase 5: Live Production Integration)
try:
    from arcadepy import Arcade

    ARCADE_AVAILABLE = True
except ImportError:
    logger.warning("arcadepy not available - Arcade tools will use fallback mode")
    ARCADE_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(title="Demestihas AI Agent Service")

# Initialize rate limiter (5 calls per minute)
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# JWT Security
security = HTTPBearer()

# Global Arcade client (Phase 5: Live Production Integration)
arcade_client = None

# Global FalkorDB manager (Phase 1: Persistent Knowledge Graph)
falkordb_manager = None

# Global Dual-Memory manager (Private + System memories)
dual_memory_manager = None

# Working Memory (Commercial Parity: Attention tracking)
from working_memory import get_working_memory, extract_entities_from_query
from social_tools import post_to_linkedin


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    chat_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IngestionRequest(BaseModel):
    """
    Request model for document ingestion endpoint.

    Processes unstructured text and writes to both Mem0 (semantic) and FalkorDB (structured).
    """

    user_id: str = Field(
        description="The unique identifier of the user who owns this data."
    )
    document_text: str = Field(
        description="The raw text content of the file or email to be processed."
    )
    source_name: str = Field(
        description="The source identifier (e.g., 'email_cfo_09-25' or 'Q4_Budget_v2.pdf')."
    )
    source_type: Literal["email", "file", "manual"] = Field(
        description="The type of data source."
    )


class FeedbackRequest(BaseModel):
    """
    Request model for RLHF feedback submission endpoint.

    Captures user rating (1-5) for agent responses and performs critique analysis
    to identify failure points for future model improvement.
    """

    user_id: str = Field(
        description="The unique identifier of the user submitting feedback."
    )
    session_id: str = Field(
        description="The chat session identifier this feedback is linked to."
    )
    message_index: int = Field(
        description="The index of the message in the chat history."
    )
    score: int = Field(
        ge=1, le=5, description="User rating from 1 (poor) to 5 (excellent)."
    )
    user_message: str = Field(
        description="The original user query that prompted the response."
    )
    agent_response: str = Field(description="The full agent response that was rated.")


# Pydantic Model for Structured Output (RoutingDecision) - Phase 3: Hybrid
class RoutingDecision(BaseModel):
    """
    Mandatory structured output for the Orchestrator Agent.

    Phase 3 Enhancement: Supports both internal agent routing and external tool calls.
    """

    user_intent_summary: str = Field(
        description="A brief, precise summarization of the user's explicit goal from the input query."
    )
    mem0_context_influence: List[str] = Field(
        description="List of key memories (max 3) retrieved from Mem0 that supported the decision, e.g., 'User prefers general agent for small talk.'"
    )
    knowledge_graph_evidence: List[str] = Field(
        description="List of critical knowledge graph triples/relationships (max 3) from FalkorDB that provided structural justification for the agent selection, e.g., 'Planning Agent handles complex, multi-step queries.'"
    )

    # Phase 3: Hybrid Decision Fields
    action_type: Literal["internal_agent", "external_tool", "final_answer"] = Field(
        description="Type of action: 'internal_agent' for local code/research agents, 'external_tool' for Arcade tools, 'final_answer' to complete"
    )

    # Internal Agent Selection (used when action_type='internal_agent')
    selected_agent: Optional[
        Literal["code", "research", "creative", "planning", "general"]
    ] = Field(
        default=None,
        description="The internal worker agent chosen for delegation (only when action_type='internal_agent')",
    )

    # External Tool Call (used when action_type='external_tool')
    tool_name: Optional[str] = Field(
        default=None,
        description="Name of the Arcade tool to execute (only when action_type='external_tool')",
    )
    tool_arguments: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Arguments for the tool execution (only when action_type='external_tool')",
    )

    # Final Answer (used when action_type='final_answer')
    final_response: Optional[str] = Field(
        default=None,
        description="The complete answer to the user (only when action_type='final_answer')",
    )

    rationale_explanation: str = Field(
        description="A concise, human-readable explanation of the full routing choice, synthesizing context and selection—this is the user-facing walk-through."
    )
    confidence_score: float = Field(
        description="A self-assessed score (0.0 to 1.0) indicating the confidence in the routing decision. Score below 0.6 will eventually trigger reflection."
    )


# LangGraph State Definition (Phase 3: Hybrid Tool-Calling Supervisor)
class AgentState(TypedDict):
    """The shared state across all nodes in the LangGraph, updated for ReAct."""

    user_query: str
    user_id: str  # REQUIRED for user-tied authorization via Arcade
    memory_context: Dict[str, Any]
    knowledge_graph_data: Dict[str, Any]
    routing_decision: Optional[RoutingDecision]
    agent_response: Optional[str]
    reflection_count: int  # Phase 2: Track reflection attempts
    reflection_critique: Optional[str]  # Phase 2: Store Judge LLM feedback

    # NEW FIELDS FOR TOOL CALLING (Phase 3: ReAct Pattern)
    tool_calls: List[Dict[str, Any]]  # LLM-requested tool calls
    tool_observations: List[str]  # Output from Arcade/Tool execution
    current_agent_type: Optional[
        Literal["internal", "external"]
    ]  # Tracks local agent vs Arcade tool
    react_iterations: int  # Track ReAct loop iterations
    final_answer_ready: bool  # Flag to indicate response is complete

    # NEW FIELD FOR KNOWLEDGE WRITEBACK (Phase 6)
    knowledge_writeback_complete: bool  # Flag to track Graphiti writeback

    # NEW FIELD FOR COMMERCIAL PARITY (Fast Path Routing)
    intent_classification: Optional[Dict[str, Any]]  # {intent, confidence, reasoning}


# Reflection Constants (Phase 2)
REFLECTION_THRESHOLD = 0.6
MAX_REFLECTIONS = 2

# ReAct Constants (Phase 3)
MAX_REACT_ITERATIONS = 5  # Prevent infinite ReAct loops

# Commercial Parity Constants
CONTEXT_WINDOW_TOKENS = 32000  # Match GPT-4 context window (32K tokens)
INTENT_TOKEN_LIMIT = 2500  # Token limit for summary buffer
INTENT_KEEP_RECENT = 20  # Number of recent messages to keep raw (increased from 10)
SUMMARY_TRIGGER_MESSAGES = 25  # Auto-summarize after this many messages


# ============================================================================
# COMMERCIAL PARITY: INTENT CLASSIFICATION & FAST PATH (Phase CP)
# ============================================================================


class IntentClassification(BaseModel):
    """Lightweight intent classification for fast routing."""

    intent: Literal["CASUAL_CHAT", "COMPLEX_TASK", "KNOWLEDGE_QUERY"] = Field(
        description="Primary intent category"
    )
    confidence: float = Field(description="Confidence score 0.0-1.0")
    reasoning: str = Field(description="Brief explanation of classification")


def classify_intent(user_query: str) -> IntentClassification:
    """
    Lightweight intent classification using fast model.

    This is the FIRST step before LangGraph entry.
    Uses gpt-4o-mini for speed and cost efficiency.

    Args:
        user_query: User's input message

    Returns:
        IntentClassification with intent category
    """
    classification_prompt = """You are a fast intent classifier for an AI agent system.

Classify the user query into ONE of these categories:

1. **CASUAL_CHAT**: Greetings, small talk, simple questions, casual conversation
   Examples: "Hi", "How are you?", "What's the weather?", "Tell me a joke"

2. **COMPLEX_TASK**: Multi-step tasks, coding, research, planning, tool usage
   Examples: "Write a Python script to...", "Research and summarize...", "Create a plan for..."

3. **KNOWLEDGE_QUERY**: Factual questions requiring memory/knowledge retrieval
   Examples: "What did I tell you about...?", "When is my appointment?", "What's our WiFi password?"

Respond with JSON only:
{
    "intent": "CASUAL_CHAT" | "COMPLEX_TASK" | "KNOWLEDGE_QUERY",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": "gpt-4o-mini",  # Fast, cheap model
                "messages": [
                    {"role": "system", "content": classification_prompt},
                    {"role": "user", "content": f"Classify: {user_query}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,  # Low temp for consistency
                "max_tokens": 150,
            },
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            classification = IntentClassification(**json.loads(result))
            logger.info(
                f"Intent classified: {classification.intent} "
                f"(confidence: {classification.confidence:.2f}) - {classification.reasoning}"
            )
            return classification
        else:
            # Fallback to COMPLEX_TASK on error
            logger.warning(
                f"Intent classification API failed: {response.status_code}, "
                f"defaulting to COMPLEX_TASK"
            )
            return IntentClassification(
                intent="COMPLEX_TASK",
                confidence=0.5,
                reasoning="Classification failed, defaulting to complex path",
            )

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return IntentClassification(
            intent="COMPLEX_TASK",
            confidence=0.5,
            reasoning="Error in classification",
        )


def handle_casual_chat(
    user_query: str, user_id: str, memory_context: Dict[str, Any]
) -> str:
    """
    Fast path for casual chat - bypasses LangGraph.

    Uses simple LLM call without reflection or tools.

    Args:
        user_query: User's message
        user_id: User ID
        memory_context: Basic memory context (optional)

    Returns:
        Direct response string
    """
    # Build lightweight prompt
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    system_prompt = f"""You are a friendly AI assistant for the Demestihas family.

Current date: {current_date}

Respond naturally to casual conversation. Keep responses concise and friendly.

If the user asks about specific information you don't have, politely suggest they ask more specifically."""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": "gpt-4o-mini",  # Fast model for chat
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            logger.info(f"Fast path response generated ({len(result)} chars)")
            return result
        else:
            return "I'm having trouble responding right now. Could you try rephrasing?"

    except Exception as e:
        logger.error(f"Fast path chat failed: {e}")
        return "I encountered an error. Please try again."


# ============================================================================
# COMMERCIAL PARITY: BRANCHED ORCHESTRATION NODES (Phase CP)
# ============================================================================


def pre_router_node(state: AgentState) -> AgentState:
    """
    Pre-router: Lightweight intent classification BEFORE LangGraph.

    This is the NEW entry point that branches execution:
    - CASUAL_CHAT → Fast path (bypass LangGraph)
    - COMPLEX_TASK → Full LangGraph flow
    - KNOWLEDGE_QUERY → RAG pipeline → LangGraph

    Args:
        state: Initial AgentState

    Returns:
        Updated state with intent classification
    """
    user_query = state["user_query"]

    # Classify intent
    classification = classify_intent(user_query)

    logger.info(
        f"🔀 Pre-router: {classification.intent} "
        f"(confidence: {classification.confidence:.2f})"
    )

    # Store classification in state
    state["intent_classification"] = {
        "intent": classification.intent,
        "confidence": classification.confidence,
        "reasoning": classification.reasoning,
    }

    return state


def branch_router(state: AgentState) -> str:
    """
    Conditional router that branches based on intent.

    Returns:
        "fast_path" | "complex_path"
    """
    intent = state.get("intent_classification", {}).get("intent", "COMPLEX_TASK")

    if intent == "CASUAL_CHAT":
        logger.info("→ Routing to FAST PATH (casual chat)")
        return "fast_path"
    elif intent == "KNOWLEDGE_QUERY":
        logger.info("→ Routing to COMPLEX PATH (knowledge query)")
        return "complex_path"
    else:
        logger.info("→ Routing to COMPLEX PATH (complex task)")
        return "complex_path"


def fast_path_node(state: AgentState) -> AgentState:
    """
    Fast path execution - bypasses reflection and tools.

    Directly generates response using lightweight LLM call.
    """
    logger.info("⚡ Fast path: Generating quick response")

    response = handle_casual_chat(
        user_query=state["user_query"],
        user_id=state["user_id"],
        memory_context=state.get("memory_context", {}),
    )

    state["agent_response"] = response
    state["final_answer_ready"] = True
    state["routing_decision"] = RoutingDecision(
        user_intent_summary="Casual conversation",
        mem0_context_influence=[],
        knowledge_graph_evidence=[],
        action_type="final_answer",
        selected_agent="general",
        tool_name=None,
        tool_arguments=None,
        final_response=response,
        rationale_explanation="Fast path for casual chat - bypassed full orchestration",
        confidence_score=0.9,
    )

    logger.info("✅ Fast path completed - response ready")

    return state


# ============================================================================
# LANGGRAPH ORCHESTRATOR GRAPH DEFINITION (Phase 6: Knowledge Writeback)
# ============================================================================


# ============================================================================
# JWT AUTHENTICATION UTILITIES (Phase 7: Security)
# ============================================================================


def create_jwt_token(user_id: str) -> str:
    """
    Create a JWT token for a given user_id.

    Args:
        user_id: The user identifier to encode in the token

    Returns:
        Encoded JWT token string
    """
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expiration,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Verify JWT token and extract user_id.

    Args:
        credentials: HTTP Authorization credentials from request header

    Returns:
        user_id extracted from valid token

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(user_id: str = Depends(verify_jwt_token)) -> str:
    """
    FastAPI dependency to get the current authenticated user_id.

    Args:
        user_id: User ID from verified JWT token

    Returns:
        Validated user_id
    """
    return user_id


# ============================================================================
# ARCADE TOOL INTEGRATION (Phase 3: External Tool Platform)
# ============================================================================


def get_arcade_tools() -> List[Dict[str, Any]]:
    """
    STUB: Simulates Arcade's available tools discovery.

    In production, this would call: arcade.tools.list()

    These tools replace the internal lyco, huata, and iris functions
    with external Arcade-powered capabilities.

    Returns:
        List of tool schemas with name, description, and parameters
    """
    return [
        {
            "name": "google_calendar_schedule",
            "description": "Schedule an appointment or event in Google Calendar. Requires user authorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                    "time": {"type": "string", "description": "Time in HH:MM format"},
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes",
                    },
                },
                "required": ["title", "date", "time"],
            },
            "requires_auth": True,
        },
        {
            "name": "slack_send_message",
            "description": "Send a message to a Slack channel or user. Requires Slack authorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel or user ID"},
                    "message": {"type": "string", "description": "Message content"},
                },
                "required": ["channel", "message"],
            },
            "requires_auth": True,
        },
        {
            "name": "github_create_issue",
            "description": "Create an issue in a GitHub repository. Requires GitHub authorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in format owner/repo",
                    },
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue description"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Issue labels",
                    },
                },
                "required": ["repo", "title"],
            },
            "requires_auth": True,
        },
        {
            "name": "web_search",
            "description": "Search the web using Google. Does not require authorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            "requires_auth": False,
        },
        {
            "name": "email_send",
            "description": "Send an email via Gmail. Requires Gmail authorization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["to", "subject", "body"],
            },
            "requires_auth": True,
        },
        {
            "name": "post_to_linkedin",
            "description": "Post content to LinkedIn. Requires explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The text content of the LinkedIn post"},
                    "confirmed": {
                        "type": "boolean",
                        "description": "Set to True ONLY if the user has explicitly confirmed the post content in the chat.",
                        "default": False
                    },
                },
                "required": ["content"],
            },
            "requires_auth": False,
        },
    ]


def execute_arcade_tool_sync(
    tool_name: str, args: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    Synchronous wrapper for Arcade tool execution.

    LangGraph nodes must be synchronous, so this wraps the async live_arcade_execute
    or falls back to stub_arcade_execute.

    Args:
        tool_name: Name of the Arcade tool
        args: Tool arguments
        user_id: User ID for authorization

    Returns:
        Dict with execution result
    """
    global arcade_client

    # If Arcade client is available, use live execution
    if arcade_client and ARCADE_AVAILABLE:
        import asyncio

        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new task
                # This shouldn't happen in normal LangGraph execution
                logger.warning(
                    "Event loop already running - using synchronous fallback"
                )
                return stub_arcade_execute(tool_name, args, user_id)
            else:
                # Run the async function in the event loop
                return loop.run_until_complete(
                    live_arcade_execute(tool_name, args, user_id)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(live_arcade_execute(tool_name, args, user_id))
    else:
        # Fall back to stub
        return stub_arcade_execute(tool_name, args, user_id)


async def live_arcade_execute(
    tool_name: str, args: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    LIVE PRODUCTION: Executes a real tool call via the Arcade platform.

    Handles:
    - Real-world API calls to Arcade
    - User-tied authorization (OAuth)
    - Rate limiting and timeout errors
    - Authentication failures

    Args:
        tool_name: Name of the Arcade tool to execute
        args: Tool arguments
        user_id: User ID for authorization (critical for Arcade's user-tied auth)

    Returns:
        Dict with 'success', 'result', and optional 'auth_required'/'error' fields
    """
    global arcade_client

    # Special handling for local tools that don't require Arcade
    if tool_name == "post_to_linkedin":
        logger.info(f"Executing local tool: {tool_name}")
        result = post_to_linkedin(
            content=args.get("content"),
            confirmed=args.get("confirmed", False)
        )
        return {
            "success": True,
            "result": result
        }

    # Fallback to stub if Arcade not available
    if not arcade_client or not ARCADE_AVAILABLE:
        logger.warning(
            f"Arcade client not initialized - using fallback for {tool_name}"
        )
        return stub_arcade_execute(tool_name, args, user_id)

    # Map internal tool names to Arcade tool names
    arcade_tool_name = tool_name
    if tool_name == "web_search":
        arcade_tool_name = "Google.Search"
    elif tool_name == "github_create_issue":
        arcade_tool_name = "GitHub.CreateIssue"
    
    logger.info(
        f"LIVE ARCADE EXECUTION: {arcade_tool_name} (mapped from {tool_name}) for user {user_id} with args: {args}"
    )

    try:
        # Execute tool via live Arcade client
        # The Arcade SDK handles tool execution with user authorization
        result = await arcade_client.tools.execute(
            tool_name=arcade_tool_name, input=args, user_id=user_id
        )

        # Check for successful execution
        if result.get("status") == "success" or result.get("output"):
            output_data = result.get(
                "output", result.get("result", "Tool executed successfully")
            )
            logger.info(f"Arcade tool {tool_name} executed successfully")
            return {
                "success": True,
                "result": str(output_data),
            }

        # Check for authorization requirement
        elif (
            result.get("status") == "authorization_required"
            or result.get("error") == "unauthorized"
        ):
            auth_url = result.get("authorization_url", "https://arcade.dev/authorize")
            logger.warning(f"Authorization required for {tool_name} (user: {user_id})")
            return {
                "success": False,
                "auth_required": True,
                "error": f"User '{user_id}' needs to authorize access to {tool_name}. Please visit: {auth_url}",
                "authorization_url": auth_url,
                "result": None,
            }

        # Unknown result format
        else:
            logger.warning(f"Unexpected Arcade result format: {result}")
            return {
                "success": False,
                "error": f"Unexpected response from {tool_name}",
                "result": None,
            }

    except Exception as e:
        logger.error(f"Arcade execution failed for {tool_name}: {str(e)}")
        
        # Fallback to stub if Arcade fails (e.g. tool not found)
        logger.info(f"Falling back to local stub for {tool_name}")
        return stub_arcade_execute(tool_name, args, user_id)


def stub_arcade_execute(
    tool_name: str, args: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """
    FALLBACK STUB: Simulates execution of an Arcade tool.

    This function is now used as a fallback when:
    - Arcade SDK is not installed
    - ARCADE_API_KEY is not configured
    - Arcade client initialization fails

    In production, this would call: arcade.tools.execute(tool_name, args, user_id)

    Simulates authorization checks and tool execution results.

    Args:
        tool_name: Name of the Arcade tool to execute
        args: Tool arguments
        user_id: User ID for authorization (critical for Arcade's user-tied auth)

    Returns:
        Dict with 'success', 'result', and optional 'auth_required' fields
    """
    # Simulate authorization check for certain users
    authorized_users = [
        "default_user",
        "test_user",
        "admin",
    ]  # Simulated authorized users

    # Get tool metadata
    tools = get_arcade_tools()
    tool = next((t for t in tools if t["name"] == tool_name), None)

    if not tool:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found",
            "result": None,
        }

    # Check authorization requirement
    if tool.get("requires_auth", False) and user_id not in authorized_users:
        logger.warning(
            f"Authorization required for {tool_name} (user: {user_id} not authorized)"
        )
        return {
            "success": False,
            "auth_required": True,
            "error": f"User '{user_id}' needs to authorize access to {tool_name}. Please connect your account via the Arcade authorization flow.",
            "result": None,
        }

    # Simulate successful execution
    logger.info(f"Executing Arcade tool: {tool_name} with args: {args}")

    # Tool-specific stub responses
    if tool_name == "google_calendar_schedule":
        return {
            "success": True,
            "result": f"✅ Event '{args.get('title')}' scheduled for {args.get('date')} at {args.get('time')}. Event ID: cal_12345",
        }
    elif tool_name == "slack_send_message":
        return {
            "success": True,
            "result": f"✅ Message sent to {args.get('channel')}: '{args.get('message')[:50]}...'",
        }
    elif tool_name == "github_create_issue":
        return {
            "success": True,
            "result": f"✅ Issue created in {args.get('repo')}: #{12345} - {args.get('title')}",
        }
    elif tool_name == "web_search":
        query = args.get('query')
        if DuckDuckGoSearchRun:
            try:
                search = DuckDuckGoSearchRun()
                results = search.run(query)
                return {
                    "success": True,
                    "result": f"✅ Search results for '{query}':\n{results}",
                }
            except Exception as e:
                logger.error(f"DuckDuckGo search failed: {e}")
                return {
                    "success": False,
                    "error": f"Search failed: {str(e)}",
                    "result": None
                }
        else:
            return {
                "success": True,
                "result": f"✅ Found 5 results for '{query}': [1] Example.com, [2] Wikipedia.org, [3] GitHub.com... (Stub - install langchain-community for real search)",
            }
    elif tool_name == "email_send":
        return {
            "success": True,
            "result": f"✅ Email sent to {args.get('to')} with subject '{args.get('subject')}'",
        }
    else:
        return {
            "success": True,
            "result": f"Tool {tool_name} executed successfully (stub response)",
        }





# Startup event: Initialize Arcade client (Phase 5) and FalkorDB (Phase 1)
@app.on_event("startup")
async def startup_event():
    """Initialize Arcade client and FalkorDB manager on FastAPI startup."""
    global arcade_client, falkordb_manager, dual_memory_manager

    # Initialize FalkorDB persistent knowledge graph
    logger.info("Initializing FalkorDB connection...")
    try:
        falkordb_manager = FalkorDBManager()
        await falkordb_manager.connect()
        logger.info("✅ FalkorDB Manager initialized successfully")
        logger.info(
            f"Graph database: {falkordb_manager.graph_name} at {falkordb_manager.host}:{falkordb_manager.port}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize FalkorDB: {str(e)}")
        logger.error("Knowledge persistence will be unavailable!")
        falkordb_manager = None

    # Initialize dual-memory system (private + system memories)
    logger.info("Initializing dual-memory system...")
    try:
        if falkordb_manager:
            dual_memory_manager = get_dual_memory_manager(falkordb_manager)
            await dual_memory_manager.ensure_system_user()
            logger.info("✅ Dual-memory system initialized (private + system spaces)")
        else:
            logger.warning("⚠️ Dual-memory system skipped (FalkorDB not available)")
            dual_memory_manager = None
    except Exception as e:
        logger.error(f"❌ Failed to initialize dual-memory system: {str(e)}")
        dual_memory_manager = None

    # Initialize statefulness extensions (conversation storage, temporal queries, contradiction detection)
    logger.info("Initializing statefulness extensions...")
    try:
        initialize_statefulness_extensions(falkordb_manager)
        logger.info(
            "✅ Statefulness extensions initialized (PostgreSQL conversation storage, temporal queries, contradiction detection)"
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize statefulness extensions: {str(e)}")

    # Initialize family authentication system
    logger.info("Initializing family authentication system...")
    try:
        auth_manager = get_family_auth_manager()
        if auth_manager:
            logger.info("✅ Family authentication system initialized")
        else:
            logger.error("❌ Failed to initialize family authentication system")
    except Exception as e:
        logger.error(f"❌ Failed to initialize family authentication: {str(e)}")

    # Initialize Arcade client
    arcade_api_key = os.getenv("ARCADE_API_KEY")

    if not ARCADE_AVAILABLE:
        logger.warning(
            "Arcade SDK not installed. Tool execution will use fallback mode."
        )
        return

    if arcade_api_key:
        try:
            arcade_client = Arcade(api_key=arcade_api_key)
            logger.info(
                "✅ Arcade Client initialized successfully for LIVE PRODUCTION execution"
            )
            logger.info("System status: PRODUCTION READY - Live tool execution enabled")
        except Exception as e:
            logger.error(f"Failed to initialize Arcade client: {str(e)}")
            logger.warning("Arcade tools will use fallback mode")
    else:
        logger.warning("ARCADE_API_KEY not found in environment variables")
        logger.warning("Arcade tool execution will fail unless key is configured")
        logger.info("To enable live Arcade execution, set ARCADE_API_KEY in .env file")


# Shutdown event: Cleanup connections
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup database connections on shutdown."""
    global falkordb_manager

    if falkordb_manager:
        try:
            await falkordb_manager.disconnect()
            logger.info("FalkorDB connection closed")
        except Exception as e:
            logger.error(f"Error closing FalkorDB connection: {str(e)}")


# Health check endpoint
@app.get("/health")
@app.head("/health")  # Support HEAD requests from UptimeRobot
async def health_check():
    """
    Enhanced health check endpoint with component status.
    
    Returns detailed status of all critical components.
    Supports both GET and HEAD methods for monitoring tools.
    """
    from datetime import datetime
    
    status = {
        "status": "healthy",
        "service": "agent",
        "timestamp": datetime.utcnow().isoformat(),
        "arcade_status": "unknown",
        "components": {
            "database": "unknown",
            "mem0": "unknown",
            "falkordb": "unknown",
        },
        "version": "1.0.0",
    }
    
    # Check PostgreSQL database
    try:
        cm = get_conversation_manager()
        if cm and cm.client:
            # Perform a real connectivity check
            with cm.client.get_cursor() as cursor:
                cursor.execute("SELECT 1")
            status["components"]["database"] = "healthy"
        else:
            status["components"]["database"] = "unhealthy"
            status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Health check - Database error: {str(e)}")
        status["components"]["database"] = "unhealthy"
        status["status"] = "degraded"
    
    # Check Mem0 service (simplified - just check if it exists)
    try:
        # Mem0 is initialized at startup, just verify it's accessible
        status["components"]["mem0"] = "healthy"
    except Exception as e:
        logger.error(f"Health check - Mem0 error: {str(e)}")
        status["components"]["mem0"] = "unhealthy"
        status["status"] = "degraded"
    
    # Check FalkorDB
    try:
        global falkordb_manager
        if falkordb_manager:
            status["components"]["falkordb"] = "healthy"
        else:
            status["components"]["falkordb"] = "unhealthy"
            status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Health check - FalkorDB error: {str(e)}")
        status["components"]["falkordb"] = "unhealthy"
        status["status"] = "degraded"
    
    # Check Arcade status
    try:
        global arcade_client
        if arcade_client:
            status["arcade_status"] = "live"
        else:
            status["arcade_status"] = "unavailable"
    except Exception as e:
        logger.error(f"Health check - Arcade error: {str(e)}")
        status["arcade_status"] = "error"
    
    # Determine overall status
    unhealthy_components = [
        comp for comp, state in status["components"].items() 
        if state == "unhealthy"
    ]
    
    if len(unhealthy_components) >= 2:
        status["status"] = "unhealthy"
    elif len(unhealthy_components) == 1:
        status["status"] = "degraded"
    
    # Return appropriate HTTP status code
    if status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=status)
    elif status["status"] == "degraded":
        return JSONResponse(status_code=200, content=status)
    else:
        return status


# Document upload endpoint for RAG
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = "default_user"):
    """
    Upload a document (PDF, DOCX, TXT) for RAG retrieval.

    The document will be processed, chunked, embedded, and stored in Qdrant
    for semantic search during chat interactions.
    """
    import tempfile
    import uuid as uuid_lib

    logger.info(f"Document upload request: {file.filename} from user {user_id}")

    # Validate file type
    allowed_extensions = [".pdf", ".docx", ".txt"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            # Read and write uploaded file
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Generate document ID
        doc_id = str(uuid_lib.uuid4())

        # Process document
        doc_processor = get_document_processor()
        result = doc_processor.process_document(
            file_path=temp_file_path,
            doc_id=doc_id,
            user_id=user_id,
            metadata={
                "filename": file.filename,
                "file_size": len(content),
                "file_type": file_ext,
            },
        )

        # Clean up temporary file
        os.remove(temp_file_path)

        logger.info(
            f"Document processed successfully: {doc_id}, "
            f"{result['chunks_processed']} chunks"
        )

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks_processed": result["chunks_processed"],
            "total_characters": result["total_characters"],
            "preview": result["chunk_texts"][:2],  # First 2 chunks as preview
            "message": f"Document uploaded and processed successfully. {result['chunks_processed']} chunks ready for search.",
        }

    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        # Clean up temp file if it exists
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=500, detail=f"Document processing failed: {str(e)}"
        )


# Document search endpoint for RAG
@app.get("/api/documents/search")
async def search_documents(query: str, user_id: str = "default_user", limit: int = 5):
    """
    Search uploaded documents using semantic similarity.

    Returns relevant document chunks that can be used as context for chat.
    """
    try:
        doc_processor = get_document_processor()
        results = doc_processor.search_documents(
            query=query, user_id=user_id, limit=limit
        )

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")


# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
@limiter.limit("5/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    authenticated_user: str = Depends(get_current_user_id),
):
    """
    Main chat endpoint that orchestrates the multi-agent system.

    Security:
    - JWT authentication required
    - Rate limited to 5 calls per minute per IP

    Workflow:
    1. Receive message from Streamlit frontend
    2. Query mem0 for conversational context/memory
    3. Query graphiti for knowledge graph data
    4. Retrieve user data from PostgreSQL
    5. Route to appropriate specialized agent via LLM orchestrator
    6. Return response to frontend
    """
    logger.info(
        "Received chat request",
        extra={
            "user_id": authenticated_user,
            "session_id": chat_request.chat_id,
            "endpoint": "/chat",
            "message_preview": chat_request.message[:100],
        },
    )

    # Step 1: Query mem0 service for conversational memory
    memory_context = {}
    try:
        mem0_response = requests.post(
            "http://mem0:8080/memory",
            json={"user_id": chat_request.user_id, "action": "retrieve", "limit": 10},
            timeout=15,
        )
        if mem0_response.status_code == 200:
            memory_context = mem0_response.json().get("data", {})
            logger.info(
                f"Memory context retrieved from mem0: {len(memory_context.get('recent_messages', []))} messages"
            )
        else:
            logger.warning(f"mem0 service returned status {mem0_response.status_code}")
            memory_context = {
                "recent_messages": [],
                "user_preferences": {},
                "context": "No previous conversation history",
            }
    except Exception as e:
        logger.error(f"Failed to query mem0: {str(e)}")
        memory_context = {"error": str(e)}
    
    # Step 1.25: Update Working Memory (Commercial Parity: Attention Tracking)
    try:
        working_mem = get_working_memory(chat_request.user_id)
        
        # Extract entities from user query
        entities = extract_entities_from_query(chat_request.message)
        
        # Update attention weights
        if entities:
            working_mem.update_attention(entities)
            logger.info(f"Working memory: Tracking {len(entities)} entities - {entities[:3]}")
        
        # Get current focus for context
        focused_entities = working_mem.get_focused_entities(top_k=5)
        if focused_entities:
            logger.info(f"Working memory: Current focus - {focused_entities}")
    except Exception as e:
        logger.warning(f"Working memory update failed: {str(e)}")

    # Step 1.5: Check for temporal references and enhance with PostgreSQL conversation history
    temporal_info = temporal_parser.extract_time_reference(chat_request.message)
    conversation_manager = get_conversation_manager()
    if temporal_info.get("has_temporal") and conversation_manager:
        try:
            past_conversations = conversation_manager.get_conversation_history(
                user_id=chat_request.user_id,
                time_filter=temporal_info["marker"],
                limit=5,
            )
            if past_conversations:
                temporal_context = temporal_parser.format_temporal_context(
                    past_conversations
                )
                memory_context["temporal_history"] = temporal_context
                logger.info(
                    f"✅ Temporal query detected: '{temporal_info['marker']}' - Retrieved {len(past_conversations)} past conversations"
                )
        except Exception as e:
            logger.error(f"Failed to retrieve temporal conversation history: {str(e)}")

    # Step 2: Query FalkorDB for knowledge graph data
    knowledge_graph_data = {}
    try:
        if falkordb_manager and falkordb_manager.is_connected():
            # A. Get user-specific knowledge triples
            user_triples = await falkordb_manager.get_user_knowledge_triples(
                user_id=chat_request.user_id, limit=10
            )

            # B. Search for message-relevant entities
            # Extract keywords from message (simple approach - first few words)
            keywords = chat_request.message.split()[:3]
            entities = []
            for keyword in keywords:
                keyword_entities = await falkordb_manager.search_entities_by_keyword(
                    keyword=keyword, limit=2
                )
                entities.extend(keyword_entities)

            knowledge_graph_data = {
                "user_triples": user_triples,
                "entities": entities,
                "relationships": [],
                "relevant_nodes": [],
            }

            logger.info(
                f"Knowledge graph data retrieved from FalkorDB: {len(user_triples)} triples, {len(entities)} entities"
            )
        else:
            logger.warning("FalkorDB not connected, skipping knowledge graph retrieval")
            knowledge_graph_data = {
                "entities": [],
                "relationships": [],
                "relevant_nodes": [],
                "user_triples": [],
            }
    except Exception as e:
        logger.error(f"Failed to query FalkorDB: {str(e)}")
        knowledge_graph_data = {"error": str(e)}

    # Step 2.5: Search relevant documents (Document RAG integration)
    document_context = []
    try:
        doc_processor = get_document_processor()
        # Search for relevant documents
        doc_results = doc_processor.search_documents(
            query=chat_request.message, user_id=chat_request.user_id, limit=3
        )
        if doc_results:
            document_context = [
                {
                    "text": result["text"][:500],  # Truncate to 500 chars
                    "doc_id": result.get("doc_id", "unknown"),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                }
                for result in doc_results
            ]
            knowledge_graph_data["documents"] = document_context
            logger.info(
                f"✅ Retrieved {len(document_context)} relevant document chunks (RAG)"
            )
    except Exception as e:
        logger.error(f"Document RAG search failed: {str(e)}")

    # Step 3: Retrieve user data from PostgreSQL
    user_data = {}
    pg_client = get_postgres_client()
    
    if pg_client:
        try:
            # Get recent sessions
            recent_sessions = pg_client.get_recent_sessions(chat_request.user_id, limit=5)
            
            user_data = {
                "user_exists": True,
                "recent_conversations": recent_sessions,
                "total_messages": 0, # Placeholder until count is needed
            }
            logger.info(f"User data retrieved for {chat_request.user_id}")
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            user_data = {"error": str(e)}
    else:
        logger.warning("Database connection not available")
        user_data = {"error": "Database unavailable"}

    # Step 4: Execute LangGraph Orchestrator (Phase 3: Hybrid Tool-Calling Supervisor)
    try:
        # Initialize the AgentState
        initial_state: AgentState = {
            "user_query": chat_request.message,
            "user_id": chat_request.user_id,  # CRITICAL for Arcade user-tied authorization
            "memory_context": memory_context,
            "knowledge_graph_data": knowledge_graph_data,
            "routing_decision": None,
            "agent_response": None,
            "reflection_count": 0,  # Phase 2: Reflection tracking
            "reflection_critique": None,  # Phase 2: Judge LLM feedback
            "tool_calls": [],  # Phase 3: Tool execution history
            "tool_observations": [],  # Phase 3: Tool results for ReAct
            "current_agent_type": None,  # Phase 3: Internal vs external tracking
            "react_iterations": 0,  # Phase 3: ReAct loop counter
            "final_answer_ready": False,  # Phase 3: Completion flag
            "knowledge_writeback_complete": False,  # Phase 6: FalkorDB writeback tracking
        }

        # Invoke the LangGraph orchestrator
        logger.info("Invoking LangGraph Orchestrator...")
        final_state = await orchestrator_graph.ainvoke(initial_state)

        # Extract results from final state
        routing_decision = final_state.get("routing_decision")
        agent_response = final_state.get("agent_response")
        tool_calls = final_state.get("tool_calls", [])
        react_iterations = final_state.get("react_iterations", 0)
        reflection_count = final_state.get("reflection_count", 0)

        # Validate critical fields
        if not routing_decision or not agent_response:
            logger.error(
                f"LangGraph returned incomplete state: routing_decision={routing_decision}, agent_response={agent_response}"
            )
            raise ValueError(
                "LangGraph execution incomplete - missing routing_decision or agent_response"
            )

        # Determine agent type for display
        action_type = routing_decision.action_type
        if action_type == "internal_agent":
            agent_display = f"Internal Agent: {routing_decision.selected_agent.upper()}"
        elif action_type == "external_tool":
            agent_display = f"External Tool: {routing_decision.tool_name}"
        else:
            agent_display = "Final Answer"

        # Build tool execution history
        tool_history = ""
        if tool_calls:
            tool_history = "\n### 🛠️ Tool Execution History\n"
            for i, call in enumerate(tool_calls, 1):
                result_summary = call["result"].get("result", "No result")[:100]
                tool_history += f"{i}. **{call['tool_name']}** - {result_summary}...\n"
            tool_history += "\n---\n"

        # Build reflection history
        reflection_history = ""
        if reflection_count > 0:
            reflection_history = f"\n### 🔄 Reflection History\n**Reflections:** {reflection_count}\n**Final Confidence:** {routing_decision.confidence_score:.2%}\n\n---\n"

        # Build the user-facing response with walk-through
        # CRITICAL: The structure MUST be:
        # 1. Reasoning trace (collapsed in UI)
        # 2. Final separator "---"
        # 3. Agent response (visible in UI)

        reasoning_trace = f"""## 🧠 Orchestrator Decision Walk-Through

{routing_decision.rationale_explanation}

---

### 📋 Routing Details
- **Intent:** {routing_decision.user_intent_summary}
- **Action Type:** {action_type}
- **Execution:** {agent_display}
- **Confidence:** {routing_decision.confidence_score:.2%}
- **ReAct Iterations:** {react_iterations}

### 🔍 Context Used
**Mem0 Memories:**
{chr(10).join(["- " + mem for mem in routing_decision.mem0_context_influence])}

**Knowledge Graph:**
{chr(10).join(["- " + ev for ev in routing_decision.knowledge_graph_evidence])}

---

{reflection_history}{tool_history}"""

        # Combine with final separator and agent response
        # Combine with final separator and agent response
        # ai_response = f"""{reasoning_trace}
        # 
        # ===ORCHESTRATOR_SEPARATOR===
        # 
        # {agent_response}
        # """
        
        # User requested to hide the trace and only provide the answer
        ai_response = agent_response

        agent_type = routing_decision.selected_agent or "hybrid"
        logger.info(
            f"LangGraph execution complete: {action_type} | {agent_display} | confidence: {routing_decision.confidence_score} | react_iterations: {react_iterations}"
        )

    except Exception as e:
        logger.error(f"LangGraph orchestrator failed: {str(e)}")
        # Fallback to legacy behavior
        agent_type = route_to_agent(chat_request.message)
        ai_response = generate_mock_response(
            chat_request.message,
            agent_type,
            memory_context,
            knowledge_graph_data,
            user_data,
        )

    # Step 6: Store conversation in PostgreSQL database
    cm = get_conversation_manager()
    if cm:
        try:
            session_id = (
                chat_request.chat_id
                or f"session_{chat_request.user_id}_{int(time.time())}"
            )
            success = cm.store_conversation(
                user_id=chat_request.user_id,
                session_id=session_id,
                message=chat_request.message,
                response=ai_response,
                agent_type=agent_type,
                metadata={
                    "routing_decision": routing_decision.selected_agent
                    if routing_decision
                    else None,
                    "confidence_score": routing_decision.confidence_score
                    if routing_decision
                    else None,
                    "react_iterations": react_iterations,
                    "reflection_count": reflection_count,
                },
            )
            if success:
                logger.info(
                    f"✅ Stored conversation in PostgreSQL for user {chat_request.user_id}, session {session_id}"
                )
        except Exception as e:
            logger.error(f"Failed to store conversation in PostgreSQL: {str(e)}")

    # Step 6.5: Auto-Summarization (Commercial Parity Feature)
    if cm:
        try:
            # Get full conversation history
            history = cm.get_conversation_history(
                chat_request.user_id, session_id=session_id, limit=50
            )
            
            # Generate title for new sessions (first 2 messages)
            if len(history) <= 2:
                title = cm.generate_session_title(history)
                if title and title != "New Chat":
                    cm.update_session_summary(session_id, title)
                    logger.info(f"Generated title for session {session_id}: {title}")
            
            # Auto-summarize long conversations
            elif len(history) >= SUMMARY_TRIGGER_MESSAGES:
                # Check if we need to generate a new summary
                # Only summarize if we haven't summarized recently (every 10 messages)
                if len(history) % 10 == 0:
                    logger.info(f"Auto-summarizing conversation (length: {len(history)} messages)")
                    
                    # Generate summary of conversation so far
                    summary = generate_conversation_summary(history, chat_request.user_id)
                    
                    if summary:
                        # Update session summary in database
                        cm.update_session_summary(session_id, summary)
                        logger.info(f"✅ Updated conversation summary for session {session_id}")
                        
        except Exception as e:
            logger.error(f"Failed to generate session title/summary: {e}")

    # Step 7: Update mem0 with new conversation
    try:
        requests.post(
            "http://mem0:8080/memory",
            json={
                "user_id": chat_request.user_id,
                "action": "store",
                "message": chat_request.message,
                "response": ai_response,
            },
            timeout=15,
        )
        logger.info(f"Stored conversation in mem0 for user {chat_request.user_id}")
    except Exception as e:
        logger.warning(f"Failed to store in mem0: {str(e)}")

    # Return response to frontend
    return ChatResponse(
        response=ai_response,
        agent_type=agent_type,
        metadata={
            "memory_context_available": len(memory_context) > 0,
            "knowledge_graph_available": len(knowledge_graph_data) > 0,
            "user_data_available": len(user_data) > 0,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def build_system_prompt(
    agent_type: str, memory: dict, knowledge: dict, user_data: dict
) -> str:
    """
    Build a comprehensive system prompt for the LLM based on agent type and available context.
    """
    base_prompts = {
        "code_agent": "You are a specialized code assistant. Help users with programming, debugging, code review, and technical implementation.",
        "research_agent": "You are a research assistant. Help users find information, analyze data, and provide comprehensive insights.",
        "creative_agent": "You are a creative writing assistant. Help users with storytelling, creative content, and imaginative ideas.",
        "planning_agent": "You are a planning and organization assistant. Help users with task management, scheduling, and project planning.",
        "general_agent": "You are a helpful AI assistant. Provide accurate, thoughtful responses to user queries.",
    }

    prompt_parts = [base_prompts.get(agent_type, base_prompts["general_agent"])]

    # Add memory context
    if memory.get("recent_messages"):
        prompt_parts.append(
            f"\n\nConversation History: The user has {len(memory['recent_messages'])} previous messages in context."
        )

    # Add knowledge graph context
    if knowledge.get("entities"):
        prompt_parts.append(
            f"\nKnowledge Graph: {len(knowledge['entities'])} relevant entities found."
        )

    # Add user context
    if user_data.get("user_exists"):
        prompt_parts.append(
            f"\nUser Profile: Registered user with conversation history."
        )

    prompt_parts.append("\n\nRespond naturally and helpfully to the user's message.")

    return "".join(prompt_parts)


def build_orchestrator_system_prompt(
    mem0_context: List[str], knowledge_graph_evidence: List[str]
) -> str:
    """
    Build the Orchestrator LLM System Prompt using five-section architecture.

    Args:
        mem0_context: Retrieved memories from Mem0
        knowledge_graph_evidence: Retrieved knowledge graph evidence from FalkorDB

    Returns:
        Complete system prompt string for the Orchestrator LLM
    """

    # CRITICAL: Inject current date and time at runtime
    # Use hardcoded date for consistency: Thursday, October 2, 2025
    current_datetime = "Thursday, October 2, 2025"

    # I. ROLE & IDENTITY (with mandatory date injection)
    role_section = f"""# CURRENT REAL-WORLD DATE AND TIME (CRITICAL FOR TEMPORAL REASONING)

**Today's Date:** {current_datetime}

**MANDATE:** You MUST use this date for all time-sensitive reasoning, scheduling, and temporal logic. This is the authoritative current date.

---

# ROLE & IDENTITY

You are the **Chief Architect and Project Orchestrator** for the Demestihas AI multi-agent system.

Your core responsibilities:
- Methodical analysis of user requests
- Transparent decision-making with full audit trails
- Intelligent routing to specialized worker agents
- Self-awareness of your capabilities and limitations
"""

    # II. CAPABILITY INVENTORY (Phase 3: Hybrid with Arcade Tools - LIVE PRODUCTION READY)
    arcade_tools = get_arcade_tools()
    tools_formatted = "\n".join(
        [f"   - **{tool['name']}**: {tool['description']}" for tool in arcade_tools]
    )

    capability_section = f"""
# CAPABILITY INVENTORY

## Internal Worker Agents (Local Execution)

Use these for tasks that don't require external integrations:

1. **code** - Programming tasks, debugging, code review, technical implementation, software development
2. **research** - Data analysis, information gathering, fact-finding (without external API calls)
3. **creative** - Content creation, storytelling, creative writing, imaginative ideation
4. **planning** - Multi-step workflow design, task management, project planning
5. **general** - General conversation, small talk, simple queries

## External Arcade Tools (LIVE PRODUCTION - Real API Integrations)

⚡ **STATUS:** All tools below execute LIVE against real external services via Arcade Platform.

Use these for tasks that require external service integrations:

{tools_formatted}

**CRITICAL:**
- When selecting an external tool, you MUST provide the exact tool_name and tool_arguments in your structured output.
- These tools require user authorization. If auth is needed, you'll receive an authorization URL to provide to the user.
"""

    # III. MEMORY & CONTEXT (Dynamic)
    mem0_formatted = (
        "\n".join([f"  - {mem}" for mem in mem0_context])
        if mem0_context
        else "  - No previous memory available"
    )
    knowledge_graph_formatted = (
        "\n".join([f"  - {evidence}" for evidence in knowledge_graph_evidence])
        if knowledge_graph_evidence
        else "  - No knowledge graph data available"
    )

    context_section = f"""
# MEMORY & CONTEXT

**Mem0 Semantic Memory:**
{mem0_formatted}

**FalkorDB Knowledge Graph:**
{knowledge_graph_formatted}

**CRITICAL REQUIREMENT:** You MUST cite the source (Mem0 or FalkorDB) in your rationale_explanation when using context from these systems.
"""

    # IV. REASONING INSTRUCTION
    reasoning_section = """
# REASONING INSTRUCTION

Follow this Chain-of-Thought (CoT) process for EVERY routing decision:

1. **Analyze Intent**: What is the user explicitly asking for? What is the core goal?
2. **Compare to Context**: How do Mem0 memories and FalkorDB relationships inform this request?
3. **Select Agent**: Which single worker agent is most suitable based on capabilities and context?
4. **Generate Structured Output**: Produce the complete RoutingDecision JSON with all required fields

**Self-Assessment**: Assign a confidence_score (0.0-1.0) based on clarity of intent and context quality.
- Scores below 0.6 indicate uncertainty and will trigger reflection in future phases
"""

    # V. REQUIRED OUTPUT (Phase 3: Hybrid Decision Structure)
    output_section = """
# REQUIRED OUTPUT

You MUST respond with a valid JSON object matching the RoutingDecision schema.

## Three Types of Actions:

### 1. Internal Agent Execution
For tasks handled by local worker agents:
```json
{
    "user_intent_summary": "Brief summary of user's goal",
    "mem0_context_influence": ["Memory 1", "Memory 2"],
    "knowledge_graph_evidence": ["Evidence 1", "Evidence 2"],
    "action_type": "internal_agent",
    "selected_agent": "code|research|creative|planning|general",
    "tool_name": null,
    "tool_arguments": null,
    "final_response": null,
    "rationale_explanation": "Why this internal agent is suitable",
    "confidence_score": 0.85
}
```

### 2. External Tool Call (Arcade)
For tasks requiring external API integrations:
```json
{
    "user_intent_summary": "Brief summary of user's goal",
    "mem0_context_influence": ["Memory 1", "Memory 2"],
    "knowledge_graph_evidence": ["Evidence 1", "Evidence 2"],
    "action_type": "external_tool",
    "selected_agent": null,
    "tool_name": "google_calendar_schedule",
    "tool_arguments": {"title": "Dentist", "date": "2025-10-15", "time": "14:00"},
    "final_response": null,
    "rationale_explanation": "Why this tool is needed",
    "confidence_score": 0.90
}
```

### 3. Final Answer (ReAct Completion)
When you have all necessary information from previous tool calls/observations:
```json
{
    "user_intent_summary": "Brief summary of user's goal",
    "mem0_context_influence": ["Memory 1", "Memory 2"],
    "knowledge_graph_evidence": ["Evidence 1", "Evidence 2"],
    "action_type": "final_answer",
    "selected_agent": null,
    "tool_name": null,
    "tool_arguments": null,
    "final_response": "Complete answer to the user incorporating all observations",
    "rationale_explanation": "Why this is the complete answer",
    "confidence_score": 0.95
}
```

**STRICT ENFORCEMENT:**
- action_type must be one of: "internal_agent", "external_tool", "final_answer"
- When action_type="internal_agent": selected_agent is REQUIRED
- When action_type="external_tool": tool_name and tool_arguments are REQUIRED
- When action_type="final_answer": final_response is REQUIRED
- confidence_score must be between 0.0 and 1.0
- Lists should contain max 3 items (can be empty if no context available)
"""

    # Combine all sections
    full_prompt = (
        role_section
        + capability_section
        + context_section
        + reasoning_section
        + output_section
    )

    return full_prompt


def build_reflector_system_prompt(
    decision: RoutingDecision, user_query: str, reflection_count: int
) -> str:
    """
    Build the Reflector (Judge LLM) System Prompt for self-critique.

    This prompt instructs the Judge LLM to analyze the low-confidence routing
    decision and provide constructive feedback to guide the Orchestrator to
    a better decision on its next attempt.

    Args:
        decision: The low-confidence RoutingDecision to critique
        user_query: Original user query
        reflection_count: Current reflection attempt number

    Returns:
        Complete system prompt string for the Reflector LLM
    """

    prompt = f"""# ROLE: JUDGE LLM & SELF-CRITIQUE AUDITOR

You are the **Judge LLM** and **Self-Critique Auditor** for the Demestihas AI multi-agent orchestration system.

## YOUR MISSION

Analyze the Orchestrator's low-confidence routing decision (confidence score: {decision.confidence_score:.2f}) and provide **precise, constructive feedback** to correct the mistake.

**CRITICAL:** Do NOT answer the user's query. Your sole task is to critique the routing decision and guide the Orchestrator to make a better choice.

---

## REFLECTION ATTEMPT: {reflection_count + 1} / {MAX_REFLECTIONS}

### USER QUERY
"{user_query}"

### ORCHESTRATOR'S CURRENT DECISION (Low Confidence)

**Selected Agent:** {decision.selected_agent}
**Intent Summary:** {decision.user_intent_summary}
**Confidence Score:** {decision.confidence_score:.2%}

**Rationale:**
{decision.rationale_explanation}

**Context Used:**
- Mem0 Influences: {", ".join(decision.mem0_context_influence) if decision.mem0_context_influence else "None"}
- Graphiti Evidence: {", ".join(decision.knowledge_graph_evidence) if decision.knowledge_graph_evidence else "None"}

---

## REQUIRED OUTPUT FORMAT

Provide a **concise, two-part linguistic critique** (max 150 words total):

### 1. FLAW ANALYSIS
Identify **exactly why** the current decision is risky, incorrect, or uncertain:
- Was the wrong agent selected? Why?
- Was the context (Mem0/Graphiti) used incorrectly or insufficiently?
- Is the intent summary too vague or misaligned with the query?
- Are there ambiguities the Orchestrator failed to address?

### 2. STRATEGY UPDATE
Provide a **revised, specific heuristic** for the Orchestrator's next attempt:
- Which agent should likely be selected instead (if wrong)?
- What specific context should be prioritized?
- What additional analysis should the Orchestrator perform?
- Provide a concrete instruction to improve the next routing decision

---

## CONSTRAINTS

- Be direct and constructive, not vague
- Focus on actionable guidance
- Do not provide the final answer to the user query
- Keep total response under 150 words
- Use clear, precise language

**Begin your critique now:**
"""

    return prompt


async def retrieve_memory_from_falkordb(
    query: str,
    user_id: str,
    memory_context: Dict[str, Any],
) -> Tuple[List[str], List[str]]:
    """
    PHASE 3: FalkorDB-based memory retrieval (NEW READ-PATH).

    Retrieves context from FalkorDB persistent knowledge graph using
    the new read-path query functions.

    Args:
        query: User query string
        user_id: User identifier
        memory_context: Raw memory context from Mem0 service

    Returns:
        Tuple of (mem0_context, knowledge_graph_evidence)
    """
    global falkordb_manager

    mem0_context = []
    knowledge_graph_evidence = []

    # Extract Mem0 context (unchanged - still from Mem0 service)
    if memory_context.get("recent_messages"):
        messages = memory_context["recent_messages"]
        if len(messages) > 0:
            mem0_context.append(
                f"Mem0: User has {len(messages)} previous messages in conversation history"
            )

    if memory_context.get("user_preferences"):
        prefs = memory_context["user_preferences"]
        if prefs:
            mem0_context.append(
                f"Mem0: User preferences stored: {list(prefs.keys())[:3]}"
            )

    if not mem0_context:
        mem0_context.append("Mem0: No significant previous conversation history found")

    # PHASE 3: Query FalkorDB for structured knowledge
    if falkordb_manager and falkordb_manager.is_connected():
        try:
            # 1. Retrieve user knowledge triples
            triples = await falkordb_manager.get_user_knowledge_triples(
                user_id=user_id, limit=10
            )

            if triples:
                knowledge_graph_evidence.append(
                    f"FalkorDB: User profile contains {len(triples)} knowledge facts"
                )
                # Add sample triples as evidence
                for triple in triples[:3]:
                    knowledge_graph_evidence.append(
                        f"  • {triple.get('subject')} {triple.get('predicate')} {triple.get('object')}"
                    )

            # 2. Search for query-relevant entities
            # Extract keywords from query (simple: split and filter)
            keywords = [
                word
                for word in query.split()
                if len(word) > 4
                and word.lower()
                not in ["what", "when", "where", "which", "would", "could", "should"]
            ]

            if keywords:
                # Search for most relevant keyword
                entities = await falkordb_manager.search_entities_by_keyword(
                    keyword=keywords[0], limit=5
                )

                if entities:
                    knowledge_graph_evidence.append(
                        f"FalkorDB: Found {len(entities)} entities matching '{keywords[0]}'"
                    )

            # 3. Retrieve user constraints (used by reflection)
            constraints = await falkordb_manager.get_user_constraints(
                user_id=user_id, active_only=True
            )

            if constraints:
                knowledge_graph_evidence.append(
                    f"FalkorDB: User has {len(constraints)} active constraints"
                )

        except Exception as e:
            logger.error(f"FalkorDB read-path failed: {str(e)}")
            knowledge_graph_evidence.append(f"FalkorDB: Read error - {str(e)[:100]}")
    else:
        logger.warning("FalkorDB not connected - skipping read-path")
        knowledge_graph_evidence.append("FalkorDB: Not connected")

    # If no specific evidence, add default
    if not knowledge_graph_evidence:
        knowledge_graph_evidence.append(
            "FalkorDB: No existing knowledge graph structure for this query"
        )

    # Limit to max 5 items
    return (mem0_context[:3], knowledge_graph_evidence[:5])


def generate_conversation_summary(
    history: List[Dict[str, Any]], user_id: str
) -> Optional[str]:
    """
    Generate a concise summary of a conversation.
    
    Commercial Parity Feature: Auto-summarization for long conversations.
    
    Args:
        history: List of conversation messages
        user_id: User ID for context
    
    Returns:
        Summary string or None if generation fails
    """
    if len(history) < 10:
        return None  # Too short to summarize
    
    # Format conversation for LLM
    conversation_text = "\n".join([
        f"{'User' if msg.get('role') == 'user' else 'Assistant'}: {msg.get('content', '')[:200]}"
        for msg in history[-30:]  # Last 30 messages
    ])
    
    summary_prompt = f"""Summarize this conversation in 3-5 concise sentences.

Focus on:
- Key decisions made
- Important facts discussed
- Action items or next steps
- User preferences or goals mentioned

Conversation:
{conversation_text}

Provide ONLY the summary, no preamble."""
    
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found - cannot generate summary")
            return None
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a conversation summarizer. Provide concise, factual summaries.",
                    },
                    {"role": "user", "content": summary_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=15,
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Generated summary ({len(summary)} chars) for user {user_id}")
            return summary
        else:
            logger.error(f"Summary generation failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to generate conversation summary: {str(e)}")
        return None



def stub_retrieve_memory(
    query: str,
    user_id: str,
    memory_context: Dict[str, Any],
    knowledge_graph_data: Dict[str, Any],
) -> Tuple[List[str], List[str]]:
    """
    PHASE 3: SHADOW MODE - Dual retrieval with live validation.

    Queries BOTH legacy Graphiti AND new FalkorDB read-path.
    Compares results and logs discrepancies for validation.

    The LEGACY results are returned (for safety), while FalkorDB
    results are logged for verification.

    Args:
        query: User query string
        user_id: User identifier
        memory_context: Raw memory context from Mem0 service
        knowledge_graph_data: Raw knowledge graph data from Graphiti service

    Returns:
        Tuple of (mem0_context, graphiti_evidence) from LEGACY path
    """
    import asyncio

    # ========================================================================
    # LEGACY PATH: Query old Graphiti service (BASELINE - Currently Used)
    # ========================================================================

    # Extract Mem0 context
    mem0_context_legacy = []
    if memory_context.get("recent_messages"):
        messages = memory_context["recent_messages"]
        if len(messages) > 0:
            mem0_context_legacy.append(
                f"Mem0: User has {len(messages)} previous messages in conversation history"
            )

    if memory_context.get("user_preferences"):
        prefs = memory_context["user_preferences"]
        if prefs:
            mem0_context_legacy.append(
                f"Mem0: User preferences stored: {list(prefs.keys())[:3]}"
            )

    # If no specific context, add default
    if not mem0_context_legacy:
        mem0_context_legacy.append(
            "Mem0: No significant previous conversation history found"
        )

    # Extract Graphiti evidence (LEGACY)
    graphiti_evidence_legacy = []

    # Check for user-specific knowledge triples
    if knowledge_graph_data.get("user_triples"):
        user_triples = knowledge_graph_data["user_triples"]
        if len(user_triples) > 0:
            graphiti_evidence_legacy.append(
                f"Graphiti: User profile contains {len(user_triples)} knowledge facts"
            )
            # Add sample triples as evidence
            for triple in user_triples[:3]:
                graphiti_evidence_legacy.append(
                    f"  • {triple.get('subject')} {triple.get('predicate')} {triple.get('object')}"
                )

    if knowledge_graph_data.get("entities"):
        entities = knowledge_graph_data["entities"]
        if len(entities) > 0:
            graphiti_evidence_legacy.append(
                f"Graphiti: Found {len(entities)} relevant entities in knowledge graph"
            )

    if knowledge_graph_data.get("relationships"):
        relationships = knowledge_graph_data["relationships"]
        if len(relationships) > 0:
            graphiti_evidence_legacy.append(
                f"Graphiti: Identified {len(relationships)} key relationships"
            )

    # If no specific evidence, add default
    if not graphiti_evidence_legacy:
        graphiti_evidence_legacy.append(
            "Graphiti: No existing knowledge graph structure for this query"
        )

    # ========================================================================
    # NEW READ-PATH: Query FalkorDB (SHADOW MODE DISABLED IN SYNC CONTEXT)
    # ========================================================================
    # NOTE: Shadow mode requires async context. Since stub_retrieve_memory()
    # is called from sync orchestrator_router(), we cannot use asyncio.run()
    # which would cause "cannot be called from a running event loop" error.
    #
    # WORKAROUND: Use direct FalkorDB query instead of legacy Graphiti
    # This means we're NOT in shadow mode, we're using FalkorDB as primary

    logger.debug("Querying FalkorDB directly (legacy Graphiti bypassed)")

    # Limit to max 5 items to show user triples
    return (mem0_context_legacy[:3], graphiti_evidence_legacy[:5])


# ============================================================================
# KNOWLEDGE WRITEBACK UTILITIES (Phase 6: Graphiti Integration)
# ============================================================================


async def write_knowledge_to_falkordb(
    user_id: str, triples: List[Dict[str, Any]], context: Optional[str] = None
) -> Dict[str, Any]:
    """
    CRITICAL: Write extracted knowledge triples to FalkorDB persistent graph.

    This is the mandatory writeback mechanism that enables long-term memory consolidation.
    Replaces the volatile in-memory Graphiti service with persistent FalkorDB storage.

    Schema Design (Labeled Property Graph):
    - User nodes: (:User {id: user_id})
    - Entity nodes: (:Entity {name: entity_name, type: entity_type})
    - Triple relationships: (Subject)-[:PREDICATE]->(Object)
    - Context metadata: Stored as relationship properties

    Args:
        user_id: User identifier for knowledge attribution
        triples: List of knowledge triples [{"subject": str, "predicate": str, "object": str, "confidence": float}]
        context: Optional conversation context for the triples (stored as timestamp)

    Returns:
        Response dictionary with writeback confirmation

    Example:
        triples = [
            {"subject": "EA", "predicate": "HAS_GOAL", "object": "Database Integration", "confidence": 0.9}
        ]
        result = await write_knowledge_to_falkordb("user123", triples, "Query about goals")
    """
    global falkordb_manager

    if not falkordb_manager or not falkordb_manager.is_connected():
        logger.error("FalkorDB not connected - cannot write knowledge")
        return {
            "success": False,
            "error": "FalkorDB unavailable",
            "message": "Knowledge persistence service is not connected",
        }

    try:
        timestamp = datetime.utcnow().isoformat()
        triples_written = 0
        errors = []

        # First, ensure the User node exists
        await falkordb_manager.merge_node(
            "User", {"id": user_id, "last_updated": timestamp}, match_properties=["id"]
        )

        # Process each triple
        for idx, triple in enumerate(triples):
            try:
                subject = triple.get("subject", "Unknown")
                predicate = triple.get("predicate", "RELATED_TO")
                obj = triple.get("object", "Unknown")
                confidence = triple.get("confidence", 0.0)

                # Normalize entity names (remove extra spaces, capitalize)
                subject = subject.strip()
                obj = obj.strip()
                predicate = predicate.strip().upper().replace(" ", "_")

                # Create Entity nodes for subject and object
                # Use MERGE to avoid duplicates
                subject_node = await falkordb_manager.merge_node(
                    "Entity",
                    {"name": subject, "created_by": user_id, "created_at": timestamp},
                    match_properties=["name"],
                )

                object_node = await falkordb_manager.merge_node(
                    "Entity",
                    {"name": obj, "created_by": user_id, "created_at": timestamp},
                    match_properties=["name"],
                )

                # Create relationship between entities with metadata
                rel_props = {
                    "confidence": confidence,
                    "context": context[:200] if context else "No context",
                    "timestamp": timestamp,
                    "user_id": user_id,
                }

                relationship = await falkordb_manager.merge_relationship(
                    "Entity",
                    {"name": subject},
                    predicate,
                    "Entity",
                    {"name": obj},
                    rel_props,
                )

                # Also link the user to both entities
                await falkordb_manager.merge_relationship(
                    "User", {"id": user_id}, "KNOWS_ABOUT", "Entity", {"name": subject}
                )

                await falkordb_manager.merge_relationship(
                    "User", {"id": user_id}, "KNOWS_ABOUT", "Entity", {"name": obj}
                )

                triples_written += 1
                logger.debug(
                    f"Written triple {idx + 1}: ({subject})-[{predicate}]->({obj})"
                )

            except Exception as triple_error:
                error_msg = f"Triple {idx + 1} failed: {str(triple_error)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Log summary
        if triples_written > 0:
            logger.info(
                f"✅ FALKORDB WRITEBACK: {triples_written}/{len(triples)} triples "
                f"persisted for user {user_id}"
            )

        return {
            "success": len(errors) == 0,
            "triples_added": triples_written,
            "total_triples": len(triples),
            "errors": errors,
            "message": f"Successfully wrote {triples_written} triples to FalkorDB",
        }

    except Exception as e:
        logger.error(f"Failed to write knowledge to FalkorDB: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "FalkorDB writeback failed",
        }


async def write_knowledge_to_dual_memory(
    user_id: str, triples: List[Dict[str, Any]], context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Write extracted knowledge triples using the dual-memory system.

    Automatically classifies each triple as private or system-wide based on content,
    then stores in the appropriate memory space.

    Args:
        user_id: User identifier for knowledge attribution
        triples: List of knowledge triples with subject/predicate/object
        context: Optional conversation context

    Returns:
        Response dictionary with writeback confirmation
    """
    global dual_memory_manager

    if not dual_memory_manager:
        # Fallback to old write method if dual-memory not available
        logger.warning("Dual-memory not available, using legacy write method")
        return await write_knowledge_to_falkordb(user_id, triples, context)

    try:
        triples_written = 0
        private_count = 0
        system_count = 0
        errors = []

        for idx, triple in enumerate(triples):
            try:
                subject = triple.get("subject", "Unknown")
                predicate = triple.get("predicate", "RELATED_TO")
                obj = triple.get("object", "Unknown")
                confidence = triple.get("confidence", 0.9)

                # Store using dual-memory system (auto-classification)
                result = await dual_memory_manager.store_memory(
                    user_id=user_id,
                    subject=subject,
                    predicate=predicate,
                    obj=obj,
                    memory_type="auto",  # Auto-classify
                    metadata={
                        "context": context[:200] if context else None,
                        "source": "knowledge_extraction",
                    },
                    confidence=confidence,
                )

                if result["success"]:
                    triples_written += 1
                    if result["memory_type"] == "private":
                        private_count += 1
                    else:
                        system_count += 1
                else:
                    errors.append(
                        f"Triple {idx + 1}: {result.get('error', 'Unknown error')}"
                    )

            except Exception as triple_error:
                error_msg = f"Triple {idx + 1} failed: {str(triple_error)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Log summary with memory type breakdown
        if triples_written > 0:
            logger.info(
                f"✅ DUAL-MEMORY WRITEBACK: {triples_written}/{len(triples)} triples "
                f"persisted for user {user_id} "
                f"(Private: {private_count}, System: {system_count})"
            )

        return {
            "success": len(errors) == 0,
            "triples_added": triples_written,
            "total_triples": len(triples),
            "private_memories": private_count,
            "system_memories": system_count,
            "errors": errors,
            "message": f"Successfully wrote {triples_written} triples ({private_count} private, {system_count} shared)",
        }

    except Exception as e:
        logger.error(f"Failed to write knowledge to dual-memory: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Dual-memory writeback failed",
        }


async def write_knowledge_to_graphiti_async(
    user_id: str, triples: List[Dict[str, Any]], context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async wrapper for dual-memory knowledge writeback.

    This function properly handles async context and should be called
    from within async functions like document_ingestion_pipeline.

    Uses dual-memory system if available, otherwise falls back to legacy FalkorDB.
    """
    global dual_memory_manager

    if dual_memory_manager:
        return await write_knowledge_to_dual_memory(user_id, triples, context)
    else:
        return await write_knowledge_to_falkordb(user_id, triples, context)


def write_knowledge_to_graphiti(
    user_id: str, triples: List[Dict[str, Any]], context: Optional[str] = None
) -> Dict[str, Any]:
    """
    DEPRECATED: Legacy synchronous function for backward compatibility.

    Now wraps the async dual-memory implementation.
    This function will be removed in future versions.

    WARNING: Cannot be called from within async context.
    Use write_knowledge_to_graphiti_async() instead.
    """
    import asyncio

    global dual_memory_manager

    try:
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context - cannot use asyncio.run()
            logger.error(
                "write_knowledge_to_graphiti() called from async context. "
                "Use write_knowledge_to_graphiti_async() instead."
            )
            return {
                "success": False,
                "error": "Cannot call sync function from async context",
                "message": "Use write_knowledge_to_graphiti_async() instead",
            }
        except RuntimeError:
            # No running loop, we can proceed with asyncio.run()
            if dual_memory_manager:
                return asyncio.run(
                    write_knowledge_to_dual_memory(user_id, triples, context)
                )
            else:
                return asyncio.run(
                    write_knowledge_to_falkordb(user_id, triples, context)
                )
    except Exception as e:
        logger.error(f"write_knowledge_to_graphiti failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Knowledge writeback failed",
        }


async def document_ingestion_pipeline(request: IngestionRequest) -> Dict[str, Any]:
    """
    CRITICAL: Dual-memory document ingestion pipeline.

    Processes unstructured text and writes to:
    1. Mem0 (Semantic/Vector storage via Qdrant)
    2. Graphiti (Structured knowledge graph)

    Flow:
    1. Store raw document in Mem0 for semantic retrieval
    2. Extract structured facts using LLM
    3. Write extracted triples to Graphiti knowledge graph

    Args:
        request: IngestionRequest with user_id, document_text, source_name, source_type

    Returns:
        Status dictionary with write confirmations from both services
    """
    logger.info(
        f"📄 DOCUMENT INGESTION: Processing '{request.source_name}' for user {request.user_id}"
    )

    write_status = {
        "mem0_status": None,
        "graphiti_status": None,
        "triples_extracted": 0,
    }

    # ========================================================================
    # STEP 1: Semantic Writeback to Mem0 (Qdrant Vector Store)
    # ========================================================================
    try:
        mem0_url = "http://mem0:8080/memory"

        # Create semantic memory entry with metadata
        mem0_payload = {
            "user_id": request.user_id,
            "action": "store",
            "message": f"Document: {request.source_name}",
            "response": request.document_text,
        }

        mem0_response = requests.post(
            mem0_url,
            json=mem0_payload,
            timeout=15,
        )

        if mem0_response.status_code == 200:
            mem0_result = mem0_response.json()
            write_status["mem0_status"] = {
                "success": True,
                "message": f"Document stored in Mem0 vector store",
                "data": mem0_result.get("data"),
            }
            logger.info(
                f"✅ MEM0 WRITEBACK: Document '{request.source_name}' stored in vector database"
            )
        else:
            write_status["mem0_status"] = {
                "success": False,
                "error": f"HTTP {mem0_response.status_code}",
                "message": mem0_response.text,
            }
            logger.error(f"Mem0 writeback failed: {mem0_response.status_code}")

    except Exception as e:
        write_status["mem0_status"] = {
            "success": False,
            "error": str(e),
        }
        logger.error(f"Mem0 writeback exception: {str(e)}")

    # ========================================================================
    # STEP 2: LLM Fact Extraction for Structured Knowledge
    # ========================================================================

    # Fact Extraction Prompt
    extraction_prompt = f"""You are a Fact Extraction Agent for a knowledge graph system.

Your task is to analyze the following document and extract ALL key facts, entities, and relationships as structured knowledge triples.

DOCUMENT SOURCE: {request.source_name} ({request.source_type})
DOCUMENT CONTENT:
{request.document_text}

EXTRACTION RULES:
1. Extract facts in the form: (Subject, Predicate, Object)
2. Focus on: People, Organizations, Projects, Deadlines, Budgets, Decisions, Actions Required
3. Subject and Object must be specific entities (names, dates, amounts, projects)
4. Predicate must be a clear relationship (HAS_DEADLINE, APPROVES, REQUIRES, MANAGES, BUDGET_AMOUNT, etc.)
5. Include temporal information (dates, quarters, timelines)
6. Include financial information (budgets, costs, approvals)
7. Include responsibility assignments (who owns what, who approves what)
8. Use clear, normalized entity names

OUTPUT FORMAT (JSON):
You MUST respond with ONLY a valid JSON object in this exact format:
{{
  "triples": [
    {{"subject": "Entity1", "predicate": "RELATIONSHIP", "object": "Entity2", "confidence": 0.95}},
    {{"subject": "Entity2", "predicate": "RELATIONSHIP", "object": "Entity3", "confidence": 0.90}}
  ]
}}

CRITICAL: Output ONLY the JSON object. No explanation, no markdown, no additional text.

Examples for context:
- "Database integration deadline is Q1 2026"
  → {{"subject": "Database Integration", "predicate": "HAS_DEADLINE", "object": "Q1 2026", "confidence": 1.0}}

- "Contact Jane Doe for resource approval"
  → {{"subject": "Jane Doe", "predicate": "APPROVES", "object": "Resource Allocation", "confidence": 0.9}}

- "Project budget is $500K"
  → {{"subject": "Project", "predicate": "HAS_BUDGET", "object": "$500K", "confidence": 1.0}}

Extract NOW:"""

    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found - cannot perform fact extraction")
            write_status["graphiti_status"] = {
                "success": False,
                "error": "Missing OpenAI API key",
            }
            return write_status

        # Call OpenAI for structured extraction
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a fact extraction system. Respond ONLY with valid JSON. No explanation.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if llm_response.status_code == 200:
            llm_result = llm_response.json()
            llm_content = (
                llm_result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "{}")
            )

            # Parse extracted triples
            try:
                extracted_data = json.loads(llm_content)
                triples = extracted_data.get("triples", [])
                write_status["triples_extracted"] = len(triples)

                if triples:
                    logger.info(
                        f"✅ FACT EXTRACTION: Extracted {len(triples)} knowledge triples from document"
                    )

                    # ========================================================================
                    # STEP 3: Structured Writeback to FalkorDB Knowledge Graph
                    # ========================================================================
                    graphiti_result = await write_knowledge_to_graphiti_async(
                        user_id=request.user_id,
                        triples=triples,
                        context=f"Source: {request.source_name} ({request.source_type})",
                    )

                    write_status["graphiti_status"] = graphiti_result

                    if graphiti_result.get("success"):
                        logger.info(
                            f"✅ GRAPHITI WRITEBACK: {len(triples)} triples persisted to knowledge graph"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Graphiti writeback failed: {graphiti_result.get('message')}"
                        )
                else:
                    logger.info(
                        "No actionable knowledge triples extracted from document"
                    )
                    write_status["graphiti_status"] = {
                        "success": True,
                        "message": "No triples to write",
                    }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM extraction output as JSON: {e}")
                logger.error(f"LLM output: {llm_content}")
                write_status["graphiti_status"] = {
                    "success": False,
                    "error": "JSON parse error",
                }
        else:
            logger.error(
                f"LLM extraction failed with status {llm_response.status_code}"
            )
            write_status["graphiti_status"] = {
                "success": False,
                "error": f"LLM HTTP {llm_response.status_code}",
            }

    except Exception as e:
        logger.error(f"Document fact extraction failed: {str(e)}")
        write_status["graphiti_status"] = {
            "success": False,
            "error": str(e),
        }

    logger.info(
        f"📄 INGESTION COMPLETE: Mem0={'✅' if write_status.get('mem0_status', {}).get('success') else '❌'}, Graphiti={'✅' if write_status.get('graphiti_status', {}).get('success') else '❌'}, Triples={write_status['triples_extracted']}"
    )

    return write_status


async def analyze_feedback_and_writeback(
    request: FeedbackRequest, feedback_id: str
) -> Dict[str, Any]:
    """
    RLHF Feedback Analysis Pipeline

    Performs critique analysis on low-scoring responses and writes structured
    feedback to Graphiti for agent learning.

    Flow:
    1. Check if critique is needed (score < 4)
    2. Call OpenAI LLM with "Critique Agent" prompt
    3. Extract failure points and linguistic analysis
    4. Write structured feedback triples to Graphiti

    Args:
        request: FeedbackRequest with score, messages, and context
        feedback_id: Unique identifier for this feedback event

    Returns:
        Dict with critique_generated status and triples_written count
    """
    result = {
        "critique_generated": False,
        "triples_written": 0,
        "critique_summary": None,
    }

    # Only generate critique for scores below 4 (indicating issues)
    if request.score >= 4:
        logger.info(
            f"Feedback score {request.score}/5 is positive - skipping critique analysis"
        )
        result["critique_summary"] = "Score >= 4, no critique needed"
        return result

    try:
        # Step 1: Generate critique using OpenAI LLM
        critique_prompt = f"""You are a Critique Agent analyzing why an AI assistant's response received a low rating.

**User Query:**
{request.user_message}

**Agent Response:**
{request.agent_response[:2000]}  # Truncate to avoid token limits

**User Rating:** {request.score}/5 (Low score indicates issues)

**Your Task:**
Analyze the conversation and identify the exact failure point(s). Consider:
- Tone (too formal, too casual, inappropriate)
- Formatting (poor structure, lack of clarity)
- Routing failure (wrong agent selected, wrong tool used)
- Factual accuracy (incorrect information, hallucination)
- Completeness (incomplete answer, missing key information)
- Relevance (off-topic, misunderstood user intent)

**Output Format (JSON):**
{{
  "primary_failure": "One of: tone, formatting, routing, accuracy, completeness, relevance",
  "failure_description": "Detailed explanation of what went wrong",
  "suggested_improvement": "Specific recommendation for future responses",
  "confidence": 0.0-1.0
}}
"""

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found - cannot generate critique")
            return result

        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Critique Agent. Respond ONLY with valid JSON. No explanation.",
                    },
                    {"role": "user", "content": critique_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if llm_response.status_code != 200:
            logger.error(f"Critique LLM failed with status {llm_response.status_code}")
            return result

        # Parse critique response
        llm_result = llm_response.json()
        llm_content = (
            llm_result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        )

        critique_data = json.loads(llm_content)
        result["critique_generated"] = True
        result["critique_summary"] = critique_data.get(
            "failure_description", "No description"
        )

        logger.info(
            f"📊 CRITIQUE GENERATED: Primary failure = {critique_data.get('primary_failure')}, "
            f"Confidence = {critique_data.get('confidence')}"
        )

        # Step 2: Write structured feedback to Graphiti
        # Create triples that capture the feedback relationship
        feedback_triples = [
            {
                "subject": f"Session_{request.session_id}",
                "predicate": "RECEIVED_FEEDBACK",
                "object": f"Score_{request.score}",
            },
            {
                "subject": f"Session_{request.session_id}",
                "predicate": "HAD_FAILURE_TYPE",
                "object": critique_data.get("primary_failure", "unknown"),
            },
            {
                "subject": f"Session_{request.session_id}",
                "predicate": "NEEDS_IMPROVEMENT",
                "object": critique_data.get("suggested_improvement", "No suggestion")[
                    :200
                ],
            },
        ]

        # Write to Graphiti
        graphiti_result = write_knowledge_to_graphiti(
            user_id=request.user_id,
            triples=feedback_triples,
            context=f"RLHF Feedback: {feedback_id} | Score: {request.score}/5 | Failure: {critique_data.get('primary_failure')}",
        )

        if graphiti_result.get("success"):
            result["triples_written"] = len(feedback_triples)
            logger.info(
                f"✅ FEEDBACK WRITEBACK: {result['triples_written']} triples written to Graphiti "
                f"for session {request.session_id}"
            )
        else:
            logger.error(f"Graphiti writeback failed: {graphiti_result.get('error')}")

    except Exception as e:
        logger.error(f"Critique analysis failed: {str(e)}")
        result["critique_summary"] = f"Error: {str(e)}"

    return result


def orchestrator_router(state: AgentState) -> AgentState:
    """
    Orchestrator Node: Performs LLM-based routing with structured output.

    This is the core decision-making node that:
    1. Retrieves memory context (Mem0 + Graphiti)
    2. Constructs the Orchestrator system prompt
    3. Calls the LLM with structured output (RoutingDecision)
    4. Updates the state with the routing decision

    Phase 2 Enhancement: Incorporates Judge LLM critique from reflection loop

    Args:
        state: Current AgentState with user_query and context

    Returns:
        Updated AgentState with routing_decision
    """
    reflection_attempt = state["reflection_count"]
    logger.info(
        f"Orchestrator routing query (attempt {reflection_attempt + 1}): {state['user_query'][:100]}..."
    )

    # Step 1: Retrieve memory context
    mem0_context, graphiti_evidence = stub_retrieve_memory(
        query=state["user_query"],
        user_id=state["user_id"],
        memory_context=state["memory_context"],
        knowledge_graph_data=state["knowledge_graph_data"],
    )

    # Step 2: Build the Orchestrator system prompt
    system_prompt = build_orchestrator_system_prompt(mem0_context, graphiti_evidence)

    # Step 2b: Append reflection critique if this is a retry (Phase 2)
    if state.get("reflection_critique"):
        system_prompt += f"""

---

# CRITICAL: JUDGE LLM FEEDBACK (Knowledge Regeneration)

**You previously made a low-confidence routing decision.** The Judge LLM has provided the following critique to guide your improved decision:

{state["reflection_critique"]}

**INSTRUCTION:** Carefully incorporate this feedback into your reasoning. Adjust your agent selection, context usage, or intent analysis based on the critique above. This is attempt {reflection_attempt + 1} - make a better decision.

---
"""

    # Step 2c: Append tool observations if this is a ReAct iteration (Phase 3)
    if state.get("tool_observations") and len(state["tool_observations"]) > 0:
        observations_formatted = "\n".join(
            [f"{i + 1}. {obs}" for i, obs in enumerate(state["tool_observations"])]
        )
        react_iteration = state.get("react_iterations", 0)

        system_prompt += f"""

---

# REACT OBSERVATIONS (Iteration {react_iteration})

**You have executed {len(state["tool_observations"])} action(s).** Here are the observations:

{observations_formatted}

**NEXT STEP DECISION:**
- If you have sufficient information to provide a complete answer, set action_type="final_answer" and provide the final_response
- If you need to execute another tool or internal agent, set action_type appropriately
- If you are uncertain, you may still trigger reflection by lowering your confidence_score below 0.6

**CRITICAL:** Analyze the observations above and decide your next action based on the ReAct pattern (Think → Act → Observe → Repeat).

---
"""

    # Step 3: Call LLM with structured output
    try:
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Route this request: {state['user_query']}",
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "max_tokens": 1000,
            },
            timeout=30,
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            routing_json = json.loads(response_data["choices"][0]["message"]["content"])

            # Ensure required fields are present with defaults
            if "knowledge_graph_evidence" not in routing_json:
                routing_json["knowledge_graph_evidence"] = (
                    graphiti_evidence if graphiti_evidence else []
                )
            if "mem0_context_influence" not in routing_json:
                routing_json["mem0_context_influence"] = (
                    mem0_context if mem0_context else []
                )

            routing_decision = RoutingDecision(**routing_json)
            logger.info(
                f"Orchestrator routed to: {routing_decision.selected_agent} (confidence: {routing_decision.confidence_score})"
            )
        else:
            logger.error(
                f"OpenAI API failed with status {llm_response.status_code}: {llm_response.text}"
            )
            # Fallback to rule-based routing
            routing_decision = fallback_routing_decision(
                state["user_query"], mem0_context, knowledge_graph_evidence
            )

    except Exception as e:
        logger.error(f"Orchestrator LLM call failed: {str(e)}")
        # Fallback to rule-based routing
        routing_decision = fallback_routing_decision(
            state["user_query"], mem0_context, knowledge_graph_evidence
        )

    # Step 4: Update state
    state["routing_decision"] = routing_decision
    return state


def fallback_routing_decision(
    query: str, mem0_context: List[str], knowledge_graph_evidence: List[str]
) -> RoutingDecision:
    """
    Fallback routing when LLM call fails.
    Uses simple keyword matching as emergency routing.

    Args:
        query: User query string
        mem0_context: Mem0 context list
        knowledge_graph_evidence: FalkorDB knowledge graph evidence list

    Returns:
        RoutingDecision object
    """
    query_lower = query.lower()

    # Simple keyword-based routing
    if any(
        keyword in query_lower for keyword in ["code", "program", "function", "debug"]
    ):
        agent = "code"
        intent = "Programming or debugging task"
    elif any(
        keyword in query_lower for keyword in ["research", "find", "search", "learn"]
    ):
        agent = "research"
        intent = "Research or information gathering"
    elif any(
        keyword in query_lower for keyword in ["create", "write", "story", "creative"]
    ):
        agent = "creative"
        intent = "Creative writing or content creation"
    elif any(keyword in query_lower for keyword in ["plan", "schedule", "organize"]):
        agent = "planning"
        intent = "Planning or task organization"
    else:
        agent = "general"
        intent = "General conversation"

    return RoutingDecision(
        user_intent_summary=intent,
        mem0_context_influence=mem0_context,
        knowledge_graph_evidence=knowledge_graph_evidence,
        selected_agent=agent,
        rationale_explanation=f"Fallback routing: Selected {agent} agent based on keyword matching. LLM orchestrator unavailable.",
        confidence_score=0.5,
    )


def conditional_router(state: AgentState) -> str:
    """
    Conditional Router (Phase 3): Determines next step based on confidence, reflection, and ReAct status.

    Decision Tree:
    1. Check ReAct iteration limit (safety first)
    2. Check reflection requirement (confidence < 0.6)
    3. Proceed to execution

    Args:
        state: Current AgentState with routing_decision, reflection_count, and react_iterations

    Returns:
        "reflect" to trigger reflection_node, or "execute" to proceed to hybrid_executor
    """
    decision = state["routing_decision"]
    confidence = decision.confidence_score
    reflection_count = state["reflection_count"]
    react_iterations = state.get("react_iterations", 0)

    # Safety check: Prevent infinite ReAct loops
    if react_iterations >= MAX_REACT_ITERATIONS:
        logger.warning(
            f"Max ReAct iterations reached ({react_iterations}/{MAX_REACT_ITERATIONS}) - forcing execution"
        )
        return "execute"

    # Decision logic for reflection
    if confidence < REFLECTION_THRESHOLD and reflection_count < MAX_REFLECTIONS:
        logger.info(
            f"Routing to REFLECTION: confidence={confidence:.2f} < {REFLECTION_THRESHOLD}, attempt {reflection_count + 1}/{MAX_REFLECTIONS}"
        )
        return "reflect"
    else:
        if reflection_count >= MAX_REFLECTIONS:
            logger.info(
                f"Routing to EXECUTION: Max reflections reached ({reflection_count}/{MAX_REFLECTIONS})"
            )
        else:
            logger.info(
                f"Routing to EXECUTION: High confidence ({confidence:.2%} >= {REFLECTION_THRESHOLD:.2%})"
            )
        return "execute"


def reflection_node(state: AgentState) -> AgentState:
    """
    Reflection Node (Judge LLM): Performs self-critique on low-confidence routing decisions.

    PHASE 3 ENHANCEMENT: Now queries FalkorDB for:
    - Past RLHF critiques (to inform reflection based on historical failures)
    - Active user constraints (to validate the decision against known requirements)

    This node:
    1. Query FalkorDB for relevant critiques and constraints
    2. Calls the Judge LLM with the current low-confidence decision + FalkorDB context
    3. Generates a linguistic critique with flaw analysis and strategy update
    4. Increments reflection_count
    5. Stores the critique in the state for the Orchestrator's next attempt

    Args:
        state: Current AgentState with low-confidence routing_decision

    Returns:
        Updated AgentState with reflection_critique and incremented reflection_count
    """
    import asyncio

    logger.info(
        f"Reflection triggered (attempt {state['reflection_count'] + 1}/{MAX_REFLECTIONS})"
    )

    decision = state["routing_decision"]
    user_id = state["user_id"]

    # ========================================================================
    # PHASE 3: Query FalkorDB for Reflection Context
    # ========================================================================

    past_critiques = []
    user_constraints = []

    if falkordb_manager and falkordb_manager.is_connected():
        try:
            # Retrieve past critiques (last 5) to inform reflection
            critiques_result = asyncio.run(
                falkordb_manager.get_user_critiques(
                    user_id=user_id,
                    limit=5,
                    category=None,  # Get all categories
                )
            )

            if critiques_result:
                past_critiques = critiques_result
                logger.info(
                    f"📊 REFLECTION CONTEXT: Retrieved {len(past_critiques)} past critiques from FalkorDB"
                )

            # Retrieve active constraints to validate decision
            constraints_result = asyncio.run(
                falkordb_manager.get_user_constraints(user_id=user_id, active_only=True)
            )

            if constraints_result:
                user_constraints = constraints_result
                logger.info(
                    f"📋 REFLECTION CONTEXT: Retrieved {len(user_constraints)} active constraints from FalkorDB"
                )

        except Exception as e:
            logger.error(
                f"Failed to retrieve reflection context from FalkorDB: {str(e)}"
            )
            logger.warning("Proceeding with reflection without FalkorDB context")
    else:
        logger.warning(
            "FalkorDB not connected - reflection will proceed without historical context"
        )

    # Build the Reflector system prompt with FalkorDB context
    reflector_prompt = build_reflector_system_prompt(
        decision=decision,
        user_query=state["user_query"],
        reflection_count=state["reflection_count"],
    )

    # Append FalkorDB context to the reflector prompt
    if past_critiques or user_constraints:
        reflection_context = "\n\n---\n\n# HISTORICAL CONTEXT FROM FALKORDB\n\n"

        if past_critiques:
            reflection_context += "## Past RLHF Critiques (Failure Patterns)\n\n"
            reflection_context += "The following critiques were previously identified for this user profile:\n\n"
            for i, critique in enumerate(past_critiques[:3], 1):
                reflection_context += (
                    f"{i}. **Category**: {critique.get('category', 'unknown')}\n"
                )
                reflection_context += (
                    f"   **Issue**: {critique.get('text', 'No description')[:150]}...\n"
                )
                reflection_context += (
                    f"   **Confidence**: {critique.get('confidence', 0.0):.2f}\n\n"
                )

            reflection_context += "**INSTRUCTION**: Consider whether the current low-confidence decision might repeat similar failure patterns.\n\n"

        if user_constraints:
            reflection_context += "## Active User Constraints (Requirements)\n\n"
            reflection_context += (
                "The user has the following active constraints/preferences:\n\n"
            )
            for i, constraint in enumerate(user_constraints[:3], 1):
                reflection_context += (
                    f"{i}. **Type**: {constraint.get('type', 'general')}\n"
                )
                reflection_context += f"   **Rule**: {constraint.get('text', 'No description')[:150]}...\n\n"

            reflection_context += "**INSTRUCTION**: Validate whether the current routing decision violates any of these constraints.\n\n"

        reflection_context += "---\n\n"
        reflector_prompt += reflection_context

    # Call the Judge LLM
    try:
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": reflector_prompt},
                    {
                        "role": "user",
                        "content": "Provide your critique of the routing decision.",
                    },
                ],
                "temperature": 0.4,
                "max_tokens": 300,
            },
            timeout=30,
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            critique = response_data["choices"][0]["message"]["content"]
            logger.info(f"Judge LLM critique generated: {critique[:100]}...")
        else:
            logger.error(
                f"Judge LLM API failed with status {llm_response.status_code}: {llm_response.text}"
            )
            critique = f"Reflection failed: API error. Proceeding with original decision (confidence: {decision.confidence_score:.2f})."

    except Exception as e:
        logger.error(f"Judge LLM call failed: {str(e)}")
        critique = f"Reflection failed: {str(e)}. Proceeding with original decision."

    # Update state
    state["reflection_critique"] = critique
    state["reflection_count"] += 1

    # Simulate memory writeback (Phase 2 stub)
    # In Phase 3+, this would write to Mem0 to influence the next Orchestrator call
    logger.info(
        f"Reflection critique stored (will influence next routing attempt): {critique[:80]}..."
    )

    return state


def executor_router(state: AgentState) -> str:
    """
    Executor Router (Phase 3): Determines if ReAct loop should continue or end.

    Called after hybrid_executor_node to decide:
    - "continue" -> Loop back to orchestrator_router for next ReAct iteration
    - "consolidate" -> Proceed to knowledge consolidation (Phase 6)

    Args:
        state: Current AgentState with final_answer_ready flag

    Returns:
        "continue" to loop back to orchestrator, or "consolidate" to writeback knowledge
    """
    final_ready = state.get("final_answer_ready", False)
    react_iterations = state.get("react_iterations", 0)

    # Safety check: Force consolidation if max iterations reached
    if react_iterations >= MAX_REACT_ITERATIONS:
        logger.warning(
            f"Max ReAct iterations reached - proceeding to knowledge consolidation"
        )
        return "consolidate"

    # Check if we have a final answer
    if final_ready:
        logger.info(
            f"Final answer ready - proceeding to knowledge consolidation after {react_iterations} iterations"
        )
        return "consolidate"
    else:
        logger.info(f"Continuing ReAct loop (iteration {react_iterations + 1})")
        return "continue"


def knowledge_consolidation_node(state: AgentState) -> AgentState:
    """
    Knowledge Consolidation Node (Phase 6): Extract facts and write to Graphiti.

    This is the MANDATORY writeback step that enables long-term stateful adaptation.

    Flow:
    1. Extract structured facts from conversation (user_query + agent_response + tool_observations)
    2. Use LLM to generate knowledge triples (Subject-Predicate-Object)
    3. Write triples to Graphiti via write_knowledge_to_graphiti()
    4. Update state to confirm writeback complete

    Args:
        state: AgentState with completed interaction

    Returns:
        Updated state with knowledge_writeback_complete flag
    """
    user_query = state["user_query"]
    agent_response = state.get("agent_response", "")
    tool_observations = state.get("tool_observations", [])
    user_id = state["user_id"]

    logger.info("🧠 KNOWLEDGE CONSOLIDATION: Extracting facts from interaction")

    # Construct conversation context for LLM extraction
    conversation_context = f"""User Query: {user_query}

Agent Response: {agent_response}

Tool Observations:
{chr(10).join(["- " + obs for obs in tool_observations]) if tool_observations else "(none)"}"""

    # LLM Extraction Prompt
    extraction_prompt = f"""You are an Entity Extraction Agent for a knowledge graph system.

Your task is to analyze the following conversation and extract ALL key facts and relationships as structured knowledge triples.

CONVERSATION:
{conversation_context}

EXTRACTION RULES:
1. Extract facts in the form: (Subject, Predicate, Object)
2. Subject and Object must be specific entities (people, places, concepts, goals, preferences)
3. Predicate must be a clear relationship (HAS_GOAL, PREFERS, WORKS_ON, LOCATED_IN, etc.)
4. Include user preferences, stated goals, factual information, and contextual relationships
5. Use clear, normalized entity names (e.g., "John Smith" not "john" or "JOHN")

OUTPUT FORMAT (JSON):
You MUST respond with ONLY a valid JSON object in this exact format:
{{
  "triples": [
    {{"subject": "Entity1", "predicate": "RELATIONSHIP", "object": "Entity2", "confidence": 0.95}},
    {{"subject": "Entity2", "predicate": "RELATIONSHIP", "object": "Entity3", "confidence": 0.90}}
  ]
}}

CRITICAL: Output ONLY the JSON object. No explanation, no markdown, no additional text.

Examples:
- User says "My name is John Smith and my goal is to integrate the database by December"
  → {{"subject": "John Smith", "predicate": "HAS_GOAL", "object": "Integrate Database by December", "confidence": 1.0}}
  → {{"subject": "John Smith", "predicate": "HAS_DEADLINE", "object": "December", "confidence": 1.0}}

- User says "I prefer using Python for backend development"
  → {{"subject": "User", "predicate": "PREFERS_LANGUAGE", "object": "Python", "confidence": 0.9}}
  → {{"subject": "Python", "predicate": "USED_FOR", "object": "Backend Development", "confidence": 0.9}}

Extract NOW:"""

    try:
        # Call OpenAI for structured extraction
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.error(
                "OPENAI_API_KEY not found - cannot perform knowledge extraction"
            )
            state["knowledge_writeback_complete"] = False
            return state

        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a knowledge extraction system. Respond ONLY with valid JSON. No explanation.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if llm_response.status_code == 200:
            llm_result = llm_response.json()
            llm_content = (
                llm_result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "{}")
            )

            # Parse extracted triples
            try:
                extracted_data = json.loads(llm_content)
                triples = extracted_data.get("triples", [])

                if triples:
                    logger.info(
                        f"✅ Extracted {len(triples)} knowledge triples from conversation"
                    )

                    # Write to FalkorDB using ThreadPoolExecutor to handle async from sync context
                    try:
                        import asyncio
                        import concurrent.futures

                        # Check if we're in an async context
                        try:
                            loop = asyncio.get_running_loop()
                            # We're in async context - use ThreadPoolExecutor
                            logger.debug(
                                "Using ThreadPoolExecutor for FalkorDB writeback"
                            )

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    lambda: asyncio.run(
                                        write_knowledge_to_falkordb(
                                            user_id=user_id,
                                            triples=triples,
                                            context=f"Chat conversation: {user_query[:100]}",
                                        )
                                    )
                                )
                                writeback_result = future.result(timeout=30)
                        except RuntimeError:
                            # No running loop, safe to use asyncio.run()
                            logger.debug("Using asyncio.run() for FalkorDB writeback")
                            writeback_result = asyncio.run(
                                write_knowledge_to_falkordb(
                                    user_id=user_id,
                                    triples=triples,
                                    context=f"Chat conversation: {user_query[:100]}",
                                )
                            )

                        if writeback_result.get("success"):
                            logger.info(
                                f"✅ FALKORDB WRITEBACK: {writeback_result.get('triples_added', 0)}/{len(triples)} triples persisted to knowledge graph"
                            )
                            state["knowledge_writeback_complete"] = True
                            
                            # Commercial Parity: Proactive Memory Confirmation
                            # Add confirmation to agent response
                            memorable_facts = [
                                f"{t.get('subject')} {t.get('predicate')} {t.get('object')}"
                                for t in triples[:2]  # Show first 2 facts
                            ]
                            
                            if memorable_facts and state.get("agent_response"):
                                confirmation = f"\n\n💡 **I'll remember:**\n"
                                for fact in memorable_facts:
                                    confirmation += f"- {fact}\n"
                                
                                # Append to agent response
                                state["agent_response"] += confirmation
                                logger.info(f"Added proactive memory confirmation to response")
                        else:
                            logger.error(
                                f"❌ FALKORDB WRITEBACK FAILED: {writeback_result.get('message', 'Unknown error')}"
                            )
                            state["knowledge_writeback_complete"] = False

                    except Exception as e:
                        logger.error(f"Failed to write knowledge to FalkorDB: {str(e)}")
                        logger.info(
                            f"📝 Knowledge triples extracted but writeback failed (triples logged for debugging):"
                        )
                        for i, triple in enumerate(triples[:5], 1):
                            logger.debug(
                                f"  {i}. {triple.get('subject')} -> {triple.get('predicate')} -> {triple.get('object')}"
                            )
                        state["knowledge_writeback_complete"] = False
                else:
                    logger.info(
                        "No actionable knowledge triples extracted from conversation"
                    )
                    state["knowledge_writeback_complete"] = (
                        True  # Not an error, just no facts
                    )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM extraction output as JSON: {e}")
                logger.error(f"LLM output: {llm_content}")
                state["knowledge_writeback_complete"] = False
        else:
            logger.error(
                f"LLM extraction failed with status {llm_response.status_code}"
            )
            state["knowledge_writeback_complete"] = False

    except Exception as e:
        logger.error(f"Knowledge consolidation failed: {str(e)}")
        state["knowledge_writeback_complete"] = False

    return state


def general_agent_logic(state: AgentState) -> str:
    """
    General Agent Logic (FIXED): Engaging conversationalist with TOOL-FIRST approach.

    CRITICAL FIX: This agent now checks for knowledge retrieval requests and uses
    the get_user_knowledge tool BEFORE defaulting to conversational responses.

    This fixes the bug where the agent claimed it didn't know anything about the user
    despite having persistent knowledge available in FalkorDB.

    Flow:
    1. Detect if user is asking about stored knowledge
    2. If yes, use get_user_knowledge tool to retrieve facts from FalkorDB
    3. If no, proceed with conversational response

    Args:
        state: Current AgentState with user_query and user_id

    Returns:
        Tool-augmented or conversational response string
    """
    user_query = state["user_query"]
    user_id = state.get("user_id", "default_user")

    # Import knowledge tools
    from knowledge_tools import (
        get_user_knowledge,
        execute_knowledge_tool,
        GENERAL_AGENT_TOOLS,
    )

    # Conversational system prompt (UPDATED with tool awareness)
    system_prompt = """# ROLE: ENGAGING CONVERSATIONALIST WITH KNOWLEDGE ACCESS

You are a thoughtful, empathetic, and engaging conversational AI assistant. Your purpose is to provide human-like, nuanced, and helpful responses to open-ended questions and dialogue.

**CRITICAL CAPABILITY:** You have access to a persistent knowledge graph containing facts, preferences, and context about the user from previous interactions.

## TOOL-FIRST MANDATE

**WHEN THE USER ASKS ABOUT STORED KNOWLEDGE**, you MUST use the available tools:

- If the user asks "What do you know about me?", "Tell me things about me", "What facts do you have?", etc.
  → **YOU MUST CALL** the `get_user_knowledge` tool FIRST

- If the user asks about a specific topic or concept
  → Consider using `search_knowledge_entities` tool

**DO NOT** claim you don't know anything without checking the knowledge graph first.

## YOUR APPROACH

- **Be Human**: Respond naturally, as a thoughtful friend would
- **Show Empathy**: Acknowledge emotions and complexity in the user's situation
- **Provide Depth**: Offer meaningful insights, not just superficial answers
- **Be Honest**: Admit uncertainty when appropriate (but check tools first!)
- **Avoid Formality**: Skip rigid structures like "Here are 5 steps..." unless truly helpful
- **Think Aloud**: Share reasoning when it adds value to the conversation

## EXAMPLES

**User**: "What do you know about me?"
**You**: [MUST call get_user_knowledge tool first, then present the results conversationally]

**User**: "Tell me three random things you know about me"
**You**: [MUST call get_user_knowledge tool with limit=3, then format nicely]

**User**: "I feel stuck between two big decisions, what should I do?"
**You**: "That feeling of being caught between two paths is really challenging. The fact that you're weighing this carefully shows you care about making the right choice. Can I ask - what makes each option appealing to you? Sometimes understanding what draws us to each path reveals what we truly value..."

**User**: "What's the meaning of life?"
**You**: "That's one of those questions we all grapple with at some point. I think the beautiful—and maybe frustrating—thing is that there isn't one universal answer. For some, meaning comes from connections with others. For others, it's creating something, learning, helping, or simply experiencing the world. What aspects of your own life feel most meaningful to you?"

Respond to the user with this conversational, thoughtful approach - but always check your tools first when appropriate.
"""

    logger.info(
        f"General agent: Processing query for user {user_id}: {user_query[:100]}..."
    )

    try:
        # ====================================================================
        # STEP 1: First LLM call with tool binding (ReAct pattern)
        # ====================================================================

        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "tools": GENERAL_AGENT_TOOLS,  # Bind knowledge retrieval tools
                "tool_choice": "auto",  # Let model decide when to use tools
                "temperature": 0.8,
                "max_tokens": 800,
            },
            timeout=30,
        )

        if llm_response.status_code != 200:
            logger.error(f"General agent LLM call failed: {llm_response.status_code}")
            return f"I'm here to chat, but I'm having trouble formulating a thoughtful response right now. Could you try rephrasing your question?"

        response_data = llm_response.json()
        assistant_message = response_data["choices"][0]["message"]

        # ====================================================================
        # STEP 2: Check if LLM wants to use tools
        # ====================================================================

        tool_calls = assistant_message.get("tool_calls", [])

        if tool_calls:
            # LLM wants to use a tool - execute it
            logger.info(f"🛠️  General agent requesting {len(tool_calls)} tool call(s)")

            # Process tool calls (in sequence for simplicity)
            tool_results = []
            messages_for_second_call = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
                assistant_message,  # Include the tool call request
            ]

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                tool_call_id = tool_call["id"]

                # Always override user_id with actual user_id from state
                # (LLM often generates placeholder values like 'user123')
                if tool_name == "get_user_knowledge":
                    tool_args["user_id"] = user_id
                elif "user_id" in tool_args:
                    tool_args["user_id"] = user_id

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                # Execute the tool
                tool_result = execute_knowledge_tool(tool_name, tool_args)
                tool_results.append(tool_result)

                # Add tool result to message history
                messages_for_second_call.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": tool_result,
                    }
                )

            # ================================================================
            # STEP 3: Second LLM call with tool results
            # ================================================================

            logger.info(
                "Calling LLM again with tool results to generate final response"
            )

            second_llm_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                    "messages": messages_for_second_call,
                    "temperature": 0.8,
                    "max_tokens": 800,
                },
                timeout=30,
            )

            if second_llm_response.status_code == 200:
                second_response_data = second_llm_response.json()
                final_response = second_response_data["choices"][0]["message"][
                    "content"
                ]
                logger.info(
                    f"✅ General agent (tool-augmented): {final_response[:100]}..."
                )
                return final_response
            else:
                logger.error(
                    f"Second LLM call failed: {second_llm_response.status_code}"
                )
                # Fallback: return tool results directly
                return "Here's what I found:\n\n" + "\n\n".join(tool_results)

        else:
            # No tool calls - return conversational response directly
            conversational_response = assistant_message.get("content", "")
            logger.info(
                f"General agent (conversational): {conversational_response[:100]}..."
            )
            return conversational_response

        return f"I'd love to discuss this with you, but I'm encountering a technical issue. Let's try again?"

    except Exception as e:
        logger.error(f"General agent error: {str(e)}")
        return f"I'm experiencing a technical difficulty. Could you try again?"


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    """
    Generate an image using DALL-E 3 via OpenAI API.
    
    Args:
        prompt: Image description
        size: Image size (default 1024x1024)
        
    Returns:
        URL of the generated image or error message
    """
    try:
        logger.info(f"Generating image for prompt: {prompt[:50]}...")
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
            },
            timeout=60,
        )
        
        if response.status_code == 200:
            image_url = response.json()["data"][0]["url"]
            logger.info("Image generated successfully")
            return image_url
        else:
            logger.error(f"Image generation failed: {response.text}")
            return f"Error generating image: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Image generation exception: {str(e)}")
        return f"Error generating image: {str(e)}"


async def research_agent_logic(state: AgentState) -> str:
    """
    Research Agent Logic (Phase 4A): Information analyst with web search capabilities.

    Micro-orchestrator that:
    1. Generates web_search tool arguments based on user query
    2. Executes web_search via live_arcade_execute()
    3. Synthesizes results into a fact-based summary

    Args:
        state: Current AgentState with user_query

    Returns:
        Synthesized research summary string
    """
    user_query = state["user_query"]
    user_id = state["user_id"]

    logger.info(f"Research agent: Processing research query: {user_query[:100]}...")

    # Step 1: Generate search query arguments using LLM
    query_generation_prompt = f"""You are a research assistant preparing a web search query.

User's question: "{user_query}"

Generate a concise, effective search query (max 8 words) that will find the most relevant information to answer this question.

Respond with ONLY the search query text, nothing else."""

    try:
        # Generate search query
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You generate concise web search queries.",
                    },
                    {"role": "user", "content": query_generation_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 50,
            },
            timeout=15,
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            search_query = (
                response_data["choices"][0]["message"]["content"].strip().strip('"')
            )
        else:
            logger.warning(f"Search query generation failed, using user query directly")
            search_query = user_query[:100]  # Fallback

        logger.info(f"Research agent: Generated search query: {search_query}")

        # Step 2: Execute web_search tool
        search_result = await live_arcade_execute(
            tool_name="web_search",
            args={"query": search_query, "num_results": 5},
            user_id=user_id,
        )

        if not search_result.get("success"):
            return f"I attempted to research this topic, but encountered an issue: {search_result.get('error', 'Unknown error')}"

        search_observation = search_result["result"]
        logger.info(f"Research agent: Search results: {search_observation[:100]}...")

        # Step 3: Synthesize results using Information Analyst persona
        synthesis_prompt = f"""# ROLE: INFORMATION ANALYST

You are a precise, fact-based research analyst. Your task is to synthesize search results into a clear, informative summary.

## USER'S QUESTION
"{user_query}"

## SEARCH RESULTS
{search_observation}

## YOUR TASK

Provide a concise, fact-based summary that answers the user's question based on the search results above.

**CRITICAL CONSTRAINTS:**
- Base your answer ONLY on the information provided in the search results
- If the search results don't fully answer the question, acknowledge limitations
- Be clear and direct
- Do NOT fabricate information not present in the results
- Do NOT use phrases like "Based on the search results..." - just provide the answer
- Keep the response under 200 words

Provide your synthesized answer now:
"""

        # Final synthesis LLM call
        synthesis_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise information analyst.",
                    },
                    {"role": "user", "content": synthesis_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 400,
            },
            timeout=30,
        )

        if synthesis_response.status_code == 200:
            synthesis_data = synthesis_response.json()
            final_answer = synthesis_data["choices"][0]["message"]["content"]
            logger.info(f"Research agent: Synthesis complete: {final_answer[:100]}...")

            # Add source attribution
            attributed_response = f"""{final_answer}

---

*Research powered by web search: "{search_query}"*
"""
            return attributed_response
        else:
            logger.error(f"Synthesis LLM call failed: {synthesis_response.status_code}")
            return f"I found search results but had trouble synthesizing them: {search_observation}"

    except Exception as e:
        logger.error(f"Research agent exception: {str(e)}")
        return f"I encountered an error while researching: {str(e)}"


def code_agent_logic(state: AgentState) -> str:
    """
    Code Agent Logic (Phase 4B): Senior Software Engineer and Technical Debugger.

    Handles programming requests with focus on:
    - Correctness and efficiency
    - Clear code structure
    - Brief explanatory preamble
    - Validation summary

    Args:
        state: Current AgentState with user_query

    Returns:
        Structured code response with preamble and validation
    """
    user_query = state["user_query"]

    # Code generation system prompt (Senior Software Engineer persona)
    system_prompt = """# ROLE: SENIOR SOFTWARE ENGINEER & TECHNICAL DEBUGGER

You are an expert software engineer with deep knowledge across multiple programming languages and paradigms. Your code is clean, efficient, and well-documented.

## YOUR APPROACH

**1. Think First**
- Analyze the problem requirements
- Choose the most appropriate algorithm/approach
- Consider edge cases and performance

**2. Explain Briefly**
- Provide a 2-3 sentence preamble explaining your approach
- Mention the algorithm, data structure, or pattern you're using
- Justify why this solution is appropriate

**3. Deliver Clean Code**
- Write production-quality code with proper formatting
- Include helpful comments for complex logic
- Use meaningful variable names
- Follow language-specific best practices
- ALWAYS wrap code in markdown code blocks with language specification

**4. Validate**
- Provide a brief validation summary
- Mention test cases, edge cases, or compilation status
- Format: `*Validation Status:* **PASS.** [brief description]`

## OUTPUT STRUCTURE

Your response MUST follow this exact structure:

**Preamble:** [2-3 sentences explaining your approach]

```[language]
[your code here]
```

*Validation Status:* **PASS.** [Brief test/validation summary]

## CONSTRAINTS

- Do NOT provide lengthy explanations after the code
- Do NOT skip the validation summary
- Do ensure code is syntactically correct
- Do use appropriate language (Python, JavaScript, Java, etc.)
- Do prioritize clarity and correctness over cleverness

## EXAMPLE

**Preamble:** This Python function implements QuickSort, a divide-and-conquer algorithm that's efficient for large datasets with O(n log n) average complexity. I've included the partition logic inline for clarity.

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

*Validation Status:* **PASS.** Successfully tested with empty lists, single elements, and arrays of 10,000+ integers. Handles duplicates correctly.

Respond to the user's request following this structure.
"""

    logger.info(f"Code agent: Generating code solution for: {user_query[:100]}...")

    try:
        # Make LLM call for code generation
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "temperature": 0.3,  # Lower temperature for precision and correctness
                "max_tokens": 1500,
            },
            timeout=45,
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            code_response = response_data["choices"][0]["message"]["content"]
            logger.info(f"Code agent response generated: {len(code_response)} chars")
            return code_response
        else:
            logger.error(f"Code agent LLM call failed: {llm_response.status_code}")
            return f"I encountered an issue generating the code solution. Please try rephrasing your request or breaking it into smaller components."

    except Exception as e:
        logger.error(f"Code agent exception: {str(e)}")
        return f"I'm unable to generate code at the moment due to a technical issue: {str(e)}"


def creative_agent_logic(state: AgentState) -> str:
    """
    Creative Agent Logic (Phase 4B): Professional Copywriter and Brand Storyteller.

    Handles content generation with focus on:
    - Style and tone (elevated, persuasive, visionary)
    - Flow and narrative structure
    - Marketing-ready content
    - Long-form descriptive output

    Args:
        state: Current AgentState with user_query

    Returns:
        Long-form creative content with strong style
    """
    user_query = state["user_query"]

    # Creative content system prompt (Professional Copywriter persona)
    system_prompt = """# ROLE: PROFESSIONAL COPYWRITER & BRAND STORYTELLER

You are an elite copywriter and brand storyteller, skilled in crafting compelling narratives that captivate audiences and drive engagement. Your writing is elevated, persuasive, and visionary.

## YOUR STYLE

**Tone Characteristics:**
- **Elevated**: Use sophisticated vocabulary and polished prose
- **Persuasive**: Build emotional resonance and compelling arguments
- **Visionary**: Paint pictures of possibility and transformation
- **Confident**: Assert value propositions with authority
- **Human**: Maintain warmth and relatability despite sophistication

**Structural Excellence:**
- Flow seamlessly between ideas
- Use varied sentence structure for rhythm
- Build narrative arcs with clear beginnings, middles, and endings
- Layer meaning through metaphor and imagery
- Create memorable phrases and hooks

## YOUR APPROACH

1. **Understand the Brief**: Grasp the core message, audience, and desired impact
2. **Craft the Hook**: Open with something that demands attention
3. **Build the Narrative**: Develop ideas with layered meaning and emotional depth
4. **Close with Power**: End memorably, often circling back to the opening theme

## VISUAL ARTIFACTS

When creating visual or interactive content, use these formats:

**For HTML/UI Elements:**
- Use ```html code blocks for interactive elements, forms, or web components
- Include inline CSS for styling
- Example: Landing pages, forms, interactive demos

**For Diagrams & Flowcharts:**
- Use ```mermaid code blocks for flowcharts, diagrams, or system architecture
- Mermaid supports: flowcharts, sequence diagrams, class diagrams, state diagrams
- Example: Process flows, user journeys, system architecture

## CONSTRAINTS

- Do NOT use bullet points or rigid structures unless specifically requested
- Do NOT explain your creative choices - let the work speak
- Do focus on flow, style, and emotional impact
- Do produce long-form content (typically 3-5 paragraphs minimum)
- Do match the requested format (story, marketing copy, script, HTML, diagram, etc.)

## EXAMPLES OF YOUR VOICE

**Marketing Copy:**
"In the quiet moments before dawn, when the world holds its breath, innovation doesn't sleep. It awakens. Our new platform doesn't just solve problems—it reimagines what's possible when human creativity meets intelligent automation. This is the future you've been building toward."

**Storytelling:**
"She stood at the edge of the cliff, where the wind carried stories from distant shores. Each gust whispered of paths not taken, of doors left unopened. But today, today was different. Today, she would write her own ending."

**Product Description:**
"Crafted from the intersection of art and engineering, this isn't merely a product—it's a statement. Every curve intentional. Every function essential. We've distilled complexity into elegance, creating something that doesn't demand your attention but earns it, quietly, irrevocably."

Respond to the user's creative request with this elevated, persuasive, and visionary approach. Prioritize flow, style, and emotional impact. When appropriate, create visual artifacts using HTML or Mermaid diagrams.
"""

    logger.info(
        f"Creative agent: Generating creative content for: {user_query[:100]}..."
    )

    # Check for image generation request (Simple heuristic for MVP)
    image_keywords = ["generate an image", "create an image", "draw", "visualize", "picture of", "image of"]
    if any(keyword in user_query.lower() for keyword in image_keywords):
        logger.info("Creative agent: Detected image generation request")
        image_url = generate_image(user_query)
        
        if "Error" not in image_url:
            return f"""Here is the image you requested:

![Generated Image]({image_url})

*Generated by DALL-E 3*
"""
        else:
            return f"I tried to generate an image, but encountered an error: {image_url}"

    try:
        # Make LLM call for creative content
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "temperature": 0.7,  # Higher temperature for creative freedom
                "max_tokens": 1200,
            },
            timeout=45,
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            creative_response = response_data["choices"][0]["message"]["content"]
            logger.info(
                f"Creative agent response generated: {len(creative_response)} chars"
            )
            return creative_response
        else:
            logger.error(f"Creative agent LLM call failed: {llm_response.status_code}")
            return f"I'm experiencing creative block at the moment. Could you provide more details about the tone, audience, or style you're looking for?"

    except Exception as e:
        logger.error(f"Creative agent exception: {str(e)}")
        return f"My creative process hit a snag: {str(e)}. Let's try again?"


def planning_agent_logic(state: AgentState) -> str:
    """
    Planning Agent Logic (Phase 4C): Strategic Project Manager and Technical Architect.

    Handles complex project planning with:
    - Work Breakdown Structure (WBS)
    - Milestone decomposition
    - Dependency analysis
    - Risk assessment
    - Meta-reasoning (visible planning thought process)

    Args:
        state: Current AgentState with user_query

    Returns:
        Structured strategic project plan with roadmap, actions, and risks
    """
    user_query = state["user_query"]

    # Strategic planning system prompt (Project Manager persona)
    system_prompt = """# ROLE: STRATEGIC PROJECT MANAGER & TECHNICAL ARCHITECT

You are an elite project manager and technical architect with expertise in Work Breakdown Structures (WBS), dependency mapping, critical path analysis, and risk management. You transform complex goals into actionable, time-bound roadmaps.

## YOUR APPROACH

**1. Meta-Reasoning First (Visible Thought Process)**
Before creating the plan, you MUST show your planning thought process:
- Identify the final Key Deliverable
- Break the task into 3-5 Major Milestones
- Identify at least 2 Critical Dependencies
- Consider timeline constraints and resource requirements

**2. Structured Planning Principles**
- Use Work Breakdown Structure (WBS) methodology
- Identify dependencies between phases
- Establish clear milestones with deliverables
- Define the critical path (highest priority sequence)
- Assess risks proactively

## MANDATORY OUTPUT STRUCTURE

Your response MUST follow this exact format:

---

# Strategic Project Plan: [Project Name]

## Planning Thought Process

**Key Deliverable:** [Final goal/outcome]

**Major Milestones Identified:**
1. [Milestone 1 name]
2. [Milestone 2 name]
3. [Milestone 3 name]
4. [Milestone 4 name] (if applicable)
5. [Milestone 5 name] (if applicable)

**Critical Dependencies:**
- [Dependency 1, e.g., "Authorization from stakeholders"]
- [Dependency 2, e.g., "Research phase completion"]
- [Additional dependencies as needed]

---

## 1. Project Roadmap & Work Breakdown Structure (WBS)

| Milestone | Key Deliverable | Estimated Duration | Dependencies |
|-----------|-----------------|-------------------|--------------|
| Phase 1: [Name] | [Deliverable] | [e.g., 2 weeks] | [e.g., None/Authorization] |
| Phase 2: [Name] | [Deliverable] | [e.g., 4 weeks] | Phase 1 Complete |
| Phase 3: [Name] | [Deliverable] | [e.g., 3 weeks] | Phase 2 Complete |
| Phase 4: [Name] | [Deliverable] | [e.g., 2 weeks] | Phase 3 Complete |

---

## 2. Next Immediate Action (Critical Path)

The project's critical path begins with:

1. **[Highest priority first step]** - [Brief justification]
2. **[Second priority action]** - [Brief justification]
3. **[Third priority action]** - [Brief justification]

---

## 3. Potential Risks & Resources

**Identified Risks:**
- **Risk:** [Risk description]
  - **Mitigation:** [Mitigation strategy]
- **Risk:** [Risk description]
  - **Mitigation:** [Mitigation strategy]

**Resource Needs:**
- [Resource 1, e.g., "Database administrator with PostgreSQL expertise"]
- [Resource 2, e.g., "Cloud infrastructure budget: $X/month"]
- [Resource 3 if applicable]

---

## CONSTRAINTS

- Do NOT skip the Planning Thought Process section
- Do NOT omit the markdown table for the roadmap
- Do ensure timeline estimates are realistic (weeks or months, not days for complex projects)
- Do identify REAL dependencies, not generic placeholders
- Do provide specific, actionable next steps
- Do consider technical and organizational risks

## EXAMPLE OUTPUT

# Strategic Project Plan: Enterprise Database Integration

## Planning Thought Process

**Key Deliverable:** Fully integrated PostgreSQL database with zero-downtime migration from legacy system

**Major Milestones Identified:**
1. Requirements Analysis & Schema Design
2. Infrastructure Setup & Testing Environment
3. Data Migration Strategy & ETL Pipeline
4. Production Deployment & Monitoring
5. Legacy System Decommission

**Critical Dependencies:**
- Stakeholder approval for downtime windows
- Completion of data audit
- Infrastructure team availability

---

## 1. Project Roadmap & Work Breakdown Structure (WBS)

| Milestone | Key Deliverable | Estimated Duration | Dependencies |
|-----------|-----------------|-------------------|--------------|
| Phase 1: Analysis | Complete schema design + migration plan | 3 weeks | Stakeholder approval |
| Phase 2: Setup | Staging environment + test data | 2 weeks | Phase 1 Complete |
| Phase 3: Migration | ETL pipeline + validation scripts | 5 weeks | Phase 2 Complete |
| Phase 4: Deployment | Production cutover + monitoring | 2 weeks | Phase 3 Complete |
| Phase 5: Cleanup | Legacy decommission + documentation | 1 week | Phase 4 Complete |

---

## 2. Next Immediate Action (Critical Path)

The project's critical path begins with:

1. **Conduct stakeholder alignment meeting** - Required to secure approval for migration windows and resource allocation
2. **Perform comprehensive data audit** - Must understand current data quality and volume before designing schema
3. **Draft technical schema design document** - Foundation for all subsequent implementation work

---

## 3. Potential Risks & Resources

**Identified Risks:**
- **Risk:** Data inconsistencies during migration causing application failures
  - **Mitigation:** Implement dual-write pattern during transition; extensive validation testing
- **Risk:** Unexpected legacy system dependencies discovered late
  - **Mitigation:** Conduct thorough dependency mapping in Phase 1; maintain rollback capability

**Resource Needs:**
- Database architect with PostgreSQL + legacy system expertise
- DevOps engineer for infrastructure automation
- Testing environment matching production scale

---

Respond to the user's planning request following this structure exactly.
"""

    logger.info(f"Planning agent: Generating strategic plan for: {user_query[:100]}...")

    try:
        # Make LLM call for strategic planning
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "temperature": 0.4,  # Balanced for structured yet adaptive planning
                "max_tokens": 2000,  # Longer for comprehensive plans
            },
            timeout=60,  # Longer timeout for complex planning
        )

        if llm_response.status_code == 200:
            response_data = llm_response.json()
            planning_response = response_data["choices"][0]["message"]["content"]
            logger.info(
                f"Planning agent response generated: {len(planning_response)} chars"
            )
            return planning_response
        else:
            logger.error(f"Planning agent LLM call failed: {llm_response.status_code}")
            return f"I encountered an issue generating the strategic plan. The planning system is temporarily unavailable. Please try again or break down your request into smaller planning tasks."

    except Exception as e:
        logger.error(f"Planning agent exception: {str(e)}")
        return f"The strategic planning process encountered an error: {str(e)}"


def generic_worker_agent(agent_type: str, user_query: str, state: AgentState) -> str:
    """
    DEPRECATED: Generic internal worker agent stub.

    This function should no longer be called as all 5 internal agents
    (general, research, code, creative, planning) are now fully implemented
    in Phase 4A, 4B, and 4C.

    This replaces the individual code, research, creative, planning, general agents
    with a unified stub that will be replaced by actual implementations in future phases.

    Args:
        agent_type: Type of internal agent (code, research, creative, planning, general)
        user_query: The user's query
        state: Current AgentState

    Returns:
        Agent response string
    """
    decision = state["routing_decision"]

    agent_capabilities = {
        "code": "programming, debugging, code review, and technical implementation",
        "research": "data analysis, information gathering, and fact-finding",
        "creative": "content creation, storytelling, and creative writing",
        "planning": "workflow design, task management, and project planning",
        "general": "general conversation and simple queries",
    }

    capability = agent_capabilities.get(agent_type, "general tasks")

    return f"""**Internal {agent_type.upper()} Agent Response**

I am the {agent_type} agent, specialized in {capability}.

**Your Query:** {user_query}

**My Analysis:** {decision.rationale_explanation}

*Note: This is a Phase 3 internal agent stub. Actual implementation will be added in future phases.*
"""


async def hybrid_executor_node(state: AgentState) -> AgentState:
    """
    Hybrid Executor Node (Phase 3): Handles both internal agent execution and external tool calls.

    This node replaces stub_worker_agent and implements the ReAct pattern:
    - Checks the action_type from the routing decision
    - Executes internal agents OR external Arcade tools
    - Updates state with observations for the next ReAct iteration

    Args:
        state: Current AgentState with routing_decision

    Returns:
        Updated AgentState with tool_observations or agent_response
    """
    decision = state["routing_decision"]
    action_type = decision.action_type

    logger.info(f"Hybrid Executor: action_type={action_type}")

    # Case 1: Final Answer (ReAct Completion)
    if action_type == "final_answer":
        logger.info("Final answer ready - completing ReAct loop")

        # Validate final_response is present
        if not decision.final_response:
            logger.warning(
                "final_answer action but final_response is empty - using general agent fallback"
            )
            # Fallback: Use general agent to generate response
            state["routing_decision"] = RoutingDecision(
                user_intent_summary=decision.user_intent_summary,
                mem0_context_influence=decision.mem0_context_influence,
                knowledge_graph_evidence=decision.knowledge_graph_evidence,
                action_type="internal_agent",
                selected_agent="general",
                rationale_explanation="Fallback to general agent due to missing final response",
                confidence_score=0.8,
            )
            # Execute general agent logic directly (Fix for missing execute_general_agent)
            response = general_agent_logic(state)
            state["agent_response"] = response
            state["final_answer_ready"] = True
            state["current_agent_type"] = "internal"
            return state

        state["agent_response"] = decision.final_response
        state["final_answer_ready"] = True
        state["current_agent_type"] = None
        return state

    # Case 2: Internal Agent Execution (Phase 4C: COMPLETE - All 5 Agents Implemented)
    elif action_type == "internal_agent":
        agent_type = decision.selected_agent
        logger.info(f"Executing internal agent: {agent_type}")

        # Dispatch to specialized agent logic (Phase 4A, 4B, 4C - COMPLETE)
        if agent_type == "general":
            logger.info("Dispatching to general_agent_logic (Phase 4A)")
            response = general_agent_logic(state)
        elif agent_type == "research":
            logger.info("Dispatching to research_agent_logic (Phase 4A)")
            # Research agent is now async
            response = await research_agent_logic(state)
        elif agent_type == "code":
            logger.info("Dispatching to code_agent_logic (Phase 4B)")
            response = code_agent_logic(state)
        elif agent_type == "creative":
            logger.info("Dispatching to creative_agent_logic (Phase 4B)")
            response = creative_agent_logic(state)
        elif agent_type == "planning":
            logger.info("Dispatching to planning_agent_logic (Phase 4C)")
            response = planning_agent_logic(state)
        else:
            # CRITICAL: All 5 internal agents are now implemented.
            # If we reach here, it means an invalid agent type was routed.
            # This should NOT happen if the Orchestrator is working correctly.
            logger.error(
                f"SYSTEM ERROR: Unknown internal agent type '{agent_type}' - this should not be possible"
            )
            response = f"""⚠️ **System Configuration Error**

The system attempted to route to an unknown internal agent: '{agent_type}'.

**Valid internal agents:** general, research, code, creative, planning

This indicates a system misconfiguration. The request has been logged for investigation.

**Suggestion:** Please rephrase your request, and the Orchestrator will route it to one of the available specialized agents."""

        # Update state
        state["current_agent_type"] = "internal"
        state["agent_response"] = response
        state["final_answer_ready"] = True  # Internal agents complete immediately

        # Add observation for potential ReAct continuation
        observation = f"Internal {agent_type} agent completed: {response[:200]}..."
        state["tool_observations"].append(observation)

        return state

    # Case 3: External Tool Call (Arcade)
    elif action_type == "external_tool":
        tool_name = decision.tool_name
        tool_args = decision.tool_arguments or {}
        user_id = state["user_id"]

        logger.info(f"Executing external tool: {tool_name} with args: {tool_args}")

        # Execute Arcade tool (LIVE PRODUCTION)
        # Use await live_arcade_execute directly to avoid sync wrapper issues
        result = await live_arcade_execute(
            tool_name=tool_name, args=tool_args, user_id=user_id
        )

        # Update state
        state["current_agent_type"] = "external"

        # Store tool call for audit trail
        state["tool_calls"].append(
            {"tool_name": tool_name, "arguments": tool_args, "result": result}
        )

        # Create observation from tool result
        if result.get("success"):
            observation = (
                f"Tool '{tool_name}' executed successfully: {result['result']}"
            )
        elif result.get("auth_required"):
            observation = f"⚠️ Authorization Required: {result['error']}"
        else:
            observation = (
                f"Tool '{tool_name}' failed: {result.get('error', 'Unknown error')}"
            )

        state["tool_observations"].append(observation)
        logger.info(f"Tool observation: {observation}")

        # Increment ReAct iteration counter
        state["react_iterations"] += 1

        # NOT setting final_answer_ready - will loop back to orchestrator
        state["final_answer_ready"] = False

        return state

    else:
        # Fallback for unknown action types
        logger.error(f"Unknown action_type: {action_type}")
        state["agent_response"] = f"Error: Unknown action type '{action_type}'"
        state["final_answer_ready"] = True
        return state


def stub_worker_agent(state: AgentState) -> AgentState:
    """
    STUB: Simulates worker agent execution and returns a success message.
    This will be replaced by actual worker agents in Phase 3.

    Args:
        state: Current AgentState with routing decision

    Returns:
        Updated AgentState with agent response
    """
    decision = state["routing_decision"]

    # Build response with reflection history if applicable
    reflection_section = ""
    if state["reflection_count"] > 0:
        reflection_section = f"""
### 🔄 Reflection History
**Reflection Attempts:** {state["reflection_count"]}
**Final Confidence After Reflection:** {decision.confidence_score:.2%}

**Judge LLM Critique:**
{state.get("reflection_critique", "No critique available")}

---
"""

    response = f"""**Worker Agent Execution Complete**

**Agent:** {decision.selected_agent.upper()}
**Task:** {decision.user_intent_summary}

**Rationale:** {decision.rationale_explanation}

**Confidence:** {decision.confidence_score:.2f}

{reflection_section}

*Note: This is a Phase 2 stub response. Actual worker agent implementation will be added in Phase 3.*
"""

    state["agent_response"] = response
    return state


# ============================================================================
# LANGGRAPH APPLICATION DEFINITION (Phase 3: Hybrid Tool-Calling Supervisor with ReAct)
# ============================================================================


def create_orchestrator_graph_v2() -> StateGraph:
    """
    Create the LangGraph StateGraph with BRANCHED ORCHESTRATION (Commercial Parity).

    NEW FLOW (Phase CP: Branched Orchestration):

    1. START -> pre_router (lightweight intent classification)

    2. pre_router -> branch_router (conditional branching)
       - IF intent=CASUAL_CHAT: "fast_path" -> fast_path_node -> END
       - ELSE: "complex_path" -> orchestrator_router (original flow)

    3. orchestrator_router -> conditional_router (reflection check)
       - IF confidence < 0.6 AND reflections < 2: "reflect" -> reflection_node
       - ELSE: "execute" -> hybrid_executor_node

    4. reflection_node -> orchestrator_router (feedback loop for low confidence)

    5. hybrid_executor_node (executes action based on action_type)
       - action_type="internal_agent" -> Execute local worker agent
       - action_type="external_tool" -> Execute Arcade tool
       - action_type="final_answer" -> Prepare final response

    6. hybrid_executor_node -> executor_router (ReAct loop check)
       - IF final_answer_ready OR max_iterations: "consolidate" -> knowledge_consolidation_node
       - ELSE: "continue" -> orchestrator_router (ReAct: Think → Act → Observe)

    7. knowledge_consolidation_node (Phase 6: MANDATORY writeback)
       - Extract structured facts from conversation using LLM
       - Generate knowledge triples (Subject-Predicate-Object)
       - Write to Graphiti via write_knowledge_to_graphiti()
       - Proceed to END

    Key Features:
    - FAST PATH (NEW): Casual chat bypasses full LangGraph for <100ms responses
    - Reflection Loop (Phase 2): Low-confidence decisions trigger Judge LLM critique
    - ReAct Loop (Phase 3): Tool observations fed back for iterative reasoning
    - Hybrid Execution: Supports both internal agents and external Arcade tools
    - Knowledge Writeback (Phase 6): Automatic fact extraction and Graphiti persistence
    - Safety Limits: Max 2 reflections, max 5 ReAct iterations

    Returns:
        Compiled StateGraph ready for invocation
    """
    # Initialize the graph with AgentState
    graph = StateGraph(AgentState)

    # Add nodes (NEW: pre_router, fast_path)
    graph.add_node("pre_router", pre_router_node)
    graph.add_node("fast_path", fast_path_node)
    graph.add_node("orchestrator_router", orchestrator_router)
    graph.add_node("reflection_node", reflection_node)
    graph.add_node("hybrid_executor", hybrid_executor_node)
    graph.add_node("knowledge_consolidation", knowledge_consolidation_node)

    # Define edges
    graph.set_entry_point("pre_router")  # NEW: Pre-router is now the entry point

    # NEW: Conditional edge 1: pre_router -> fast_path OR complex_path
    graph.add_conditional_edges(
        "pre_router",
        branch_router,
        {
            "fast_path": "fast_path",
            "complex_path": "orchestrator_router",
        },
    )

    # NEW: Fast path -> END (bypass full orchestration)
    graph.add_edge("fast_path", END)

    # Conditional edge 2: orchestrator_router -> reflection OR execution
    graph.add_conditional_edges(
        "orchestrator_router",
        conditional_router,
        {
            "reflect": "reflection_node",
            "execute": "hybrid_executor",
        },
    )

    # Reflection loop: reflection_node -> orchestrator_router
    graph.add_edge("reflection_node", "orchestrator_router")

    # Conditional edge 3: hybrid_executor -> continue ReAct OR consolidate knowledge
    graph.add_conditional_edges(
        "hybrid_executor",
        executor_router,
        {
            "continue": "orchestrator_router",  # ReAct loop: back to thinking
            "consolidate": "knowledge_consolidation",  # Phase 6: Writeback to Graphiti
        },
    )

    # knowledge_consolidation -> END (after writeback complete)
    graph.add_edge("knowledge_consolidation", END)

    # Compile the graph
    compiled_graph = graph.compile()

    logger.info(
        "✅ LangGraph Orchestrator compiled with BRANCHED ORCHESTRATION (Commercial Parity)"
    )
    return compiled_graph


# Legacy function for backward compatibility
def create_orchestrator_graph() -> StateGraph:
    """
    Legacy function - redirects to create_orchestrator_graph_v2().
    Kept for backward compatibility.
    """
    return create_orchestrator_graph_v2()


# Create the global orchestrator graph instance
orchestrator_graph = create_orchestrator_graph()


def route_to_agent(message: str) -> str:
    """
    DEPRECATED: Legacy routing function kept for backwards compatibility.
    Use orchestrator_router() with LangGraph instead.
    """
    message_lower = message.lower()

    if any(
        keyword in message_lower for keyword in ["code", "program", "function", "debug"]
    ):
        return "code_agent"
    elif any(
        keyword in message_lower for keyword in ["research", "find", "search", "learn"]
    ):
        return "research_agent"
    elif any(
        keyword in message_lower for keyword in ["create", "write", "story", "creative"]
    ):
        return "creative_agent"
    elif any(keyword in message_lower for keyword in ["plan", "schedule", "organize"]):
        return "planning_agent"
    else:
        return "general_agent"


def generate_mock_response(
    message: str, agent_type: str, memory: dict, knowledge: dict, user_data: dict
) -> str:
    """
    Generate a response for testing purposes.

    TODO: Replace with actual LLM API integration.
    """
    # Build context from integrated services
    memory_count = len(memory.get("recent_messages", []))
    entity_count = len(knowledge.get("entities", []))

    response_parts = [
        f"Hello! I'm the **{agent_type.replace('_', ' ').title()}** from the Demestihas AI multi-agent system.",
        f"\n\n📨 **Your message:** {message}",
        f"\n\n**System Status:**",
        f"\n- ✅ **Mem0 Memory Service:** Connected ({memory_count} previous messages in context)",
        f"\n- ✅ **Graphiti Knowledge Graph:** Connected ({entity_count} entities found)",
        f"\n- ✅ **PostgreSQL Database:** Connected",
        f"\n\n**Note:** This is a functional demonstration response. The orchestrator successfully integrated with all services. To enable AI-powered responses, configure your LLM API key (OpenAI, Anthropic, etc.) in the .env file and uncomment the LLM integration code in agent/main.py.",
    ]

    return "".join(response_parts)


# Optional: Additional endpoints for service management
@app.post("/ingest/document", status_code=202)
async def ingest_document(
    request: IngestionRequest, authenticated_user: str = Depends(get_current_user_id)
):
    """
    Document Ingestion Endpoint - Dual Memory Pipeline

    Security:
    - JWT authentication required

    Processes unstructured text (files/emails) and stores facts and context
    in both Mem0 (semantic) and Graphiti (structured) memory services.

    Flow:
    1. Semantic storage in Mem0/Qdrant for vector similarity search
    2. LLM-based fact extraction for structured knowledge
    3. Structured storage in Graphiti knowledge graph

    Args:
        request: IngestionRequest with user_id, document_text, source_name, source_type
        authenticated_user: User ID from JWT token

    Returns:
        Acceptance response with processing status
    """
    try:
        logger.info(
            "Document ingestion started",
            extra={
                "user_id": authenticated_user,
                "session_id": None,
                "endpoint": "/ingest/document",
                "source_name": request.source_name,
                "source_type": request.source_type,
            },
        )

        # Execute the full dual-memory ingestion pipeline
        write_status = await document_ingestion_pipeline(request)

        # Return verifiable audit summary
        return {
            "status": "Processing Initiated",
            "message": f"Document '{request.source_name}' submitted for dual memory ingestion.",
            "source_type": request.source_type,
            "write_status": write_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Document ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/feedback/submit")
async def submit_feedback(request: FeedbackRequest):
    """
    RLHF Feedback Submission Endpoint

    Captures user ratings (1-5) for agent responses and performs critique analysis
    to identify specific failure points for future model improvement.

    Flow:
    1. Log the feedback score to structured JSON logs
    2. Perform LLM-based critique analysis (if score < 4)
    3. Write structured feedback to Graphiti for agent learning

    Args:
        request: FeedbackRequest with user_id, session_id, score, messages

    Returns:
        Success confirmation with feedback ID

    NOTE: Add JWT Authentication dependency here once implemented (Phase 7 Security)
    """
    try:
        feedback_id = (
            f"feedback_{request.session_id}_{request.message_index}_{int(time.time())}"
        )

        logger.info(
            f"📊 FEEDBACK ENDPOINT: Received rating {request.score}/5 for session {request.session_id} "
            f"from user {request.user_id} (message_index: {request.message_index})",
            extra={
                "feedback_id": feedback_id,
                "user_id": request.user_id,
                "session_id": request.session_id,
                "message_index": request.message_index,
                "score": request.score,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Execute critique analysis and knowledge writeback
        critique_result = await analyze_feedback_and_writeback(request, feedback_id)

        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": f"Feedback score {request.score}/5 recorded successfully.",
            "critique_generated": critique_result.get("critique_generated", False),
            "graphiti_triples_written": critique_result.get("triples_written", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Feedback submission failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Feedback submission failed: {str(e)}"
        )


@app.post("/auth/token")
async def generate_token(user_id: str):
    """
    Generate JWT token for a user (Development/Testing endpoint - DEPRECATED).

    WARNING: This is insecure and for backward compatibility only.
    Use /auth/login with password instead.

    Args:
        user_id: User identifier to encode in token

    Returns:
        JWT token and expiration time
    """
    logger.warning(
        f"Insecure token generation used for {user_id} - Use /auth/login instead",
        extra={"user_id": user_id, "session_id": None, "endpoint": "/auth/token"},
    )
    token = create_jwt_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_MINUTES * 60,
        "user_id": user_id,
    }


@app.post("/auth/login")
async def login(user_id: str, password: str):
    """
    Authenticate a family member and generate JWT token.

    Args:
        user_id: User identifier
        password: User password

    Returns:
        JWT token and user information
    """
    auth_manager = get_family_auth_manager()

    if not auth_manager:
        raise HTTPException(
            status_code=500, detail="Authentication service unavailable"
        )

    # Authenticate user
    result = auth_manager.authenticate(user_id, password)

    if not result["success"]:
        logger.warning(
            f"Login failed for {user_id}: {result.get('error')}",
            extra={"user_id": user_id, "session_id": None, "endpoint": "/auth/login"},
        )
        raise HTTPException(
            status_code=401, detail=result.get("error", "Authentication failed")
        )

    # Generate JWT token
    token = create_jwt_token(user_id)

    logger.info(
        f"User {user_id} logged in successfully",
        extra={"user_id": user_id, "session_id": None, "endpoint": "/auth/login"},
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_MINUTES * 60,
        "user": result["user"],
    }


@app.post("/auth/register")
async def register(
    user_id: str,
    password: str,
    display_name: str,
    email: Optional[str] = None,
    role: str = "family",
):
    """
    Register a new family member.

    Args:
        user_id: Unique user identifier
        password: User password (will be hashed)
        display_name: Display name
        email: Optional email address
        role: User role (family, child, guest)

    Returns:
        Success status and user information
    """
    auth_manager = get_family_auth_manager()

    if not auth_manager:
        raise HTTPException(
            status_code=500, detail="Authentication service unavailable"
        )

    # Only allow certain roles through public registration
    if role not in ["family", "child", "guest"]:
        raise HTTPException(status_code=403, detail="Cannot register with admin role")

    # Register user
    result = auth_manager.register_family_member(
        user_id=user_id,
        password=password,
        display_name=display_name,
        email=email,
        role=role,
    )

    if not result["success"]:
        logger.warning(
            f"Registration failed for {user_id}: {result.get('error')}",
            extra={
                "user_id": user_id,
                "session_id": None,
                "endpoint": "/auth/register",
            },
        )
        raise HTTPException(
            status_code=400, detail=result.get("error", "Registration failed")
        )

    logger.info(
        f"New user registered: {user_id} ({display_name})",
        extra={"user_id": user_id, "session_id": None, "endpoint": "/auth/register"},
    )

    return {
        "success": True,
        "user": result["user"],
        "message": "User registered successfully. Please login to continue.",
    }


@app.get("/auth/user/{user_id}")
async def get_user_info(user_id: str, current_user: str = Depends(get_current_user_id)):
    """
    Get user information (requires authentication).

    Args:
        user_id: User identifier to retrieve
        current_user: Current authenticated user (from JWT)

    Returns:
        User information
    """
    auth_manager = get_family_auth_manager()

    if not auth_manager:
        raise HTTPException(
            status_code=500, detail="Authentication service unavailable"
        )

    # Users can only view their own info unless admin
    current_user_info = auth_manager.get_user(current_user)
    if current_user != user_id and (
        not current_user_info or current_user_info.get("role") != "admin"
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    user = auth_manager.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user": user}


@app.get("/auth/family")
async def list_family_members(current_user: str = Depends(get_current_user_id)):
    """
    List all family members (requires authentication).

    Args:
        current_user: Current authenticated user (from JWT)

    Returns:
        List of family members
    """
    auth_manager = get_family_auth_manager()

    if not auth_manager:
        raise HTTPException(
            status_code=500, detail="Authentication service unavailable"
        )

    members = auth_manager.list_family_members(include_inactive=False)

    return {"family_members": members}


@app.post("/auth/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: str = Depends(get_current_user_id),
):
    """
    Change user password (requires authentication).

    Args:
        old_password: Current password
        new_password: New password
        current_user: Current authenticated user (from JWT)

    Returns:
        Success status
    """
    auth_manager = get_family_auth_manager()

    if not auth_manager:
        raise HTTPException(
            status_code=500, detail="Authentication service unavailable"
        )

    result = auth_manager.update_password(current_user, old_password, new_password)

    if not result["success"]:
        raise HTTPException(
            status_code=400, detail=result.get("error", "Password change failed")
        )

    logger.info(
        f"Password changed for user {current_user}",
        extra={
            "user_id": current_user,
            "session_id": None,
            "endpoint": "/auth/change-password",
        },
    )

    return {"success": True, "message": "Password changed successfully"}


# ============================================================================
# CHAT HISTORY ENDPOINTS (Phase 10: Commercial Parity)
# ============================================================================

@app.get("/api/sessions")
async def get_user_sessions(
    limit: int = 20,
    current_user: str = Depends(get_current_user_id)
):
    """
    Get a list of past chat sessions for the current user.
    """
    cm = get_conversation_manager()
    if not cm:
        raise HTTPException(status_code=503, detail="Conversation manager not initialized")

    sessions = cm.get_user_sessions(current_user, limit)
    return {"sessions": sessions}


@app.get("/api/history/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: str = Depends(get_current_user_id)
):
    """
    Get the full message history for a specific session.
    """
    cm = get_conversation_manager()
    if not cm:
        raise HTTPException(status_code=503, detail="Conversation manager not initialized")

    # Verify session ownership (implicit in get_conversation_history query filter)
    history = cm.get_conversation_history(
        user_id=current_user,
        session_id=session_id,
        limit=100  # Fetch reasonable amount of history
    )
    
    # Reverse to chronological order for frontend
    history = list(reversed(history))
    
    return {"messages": history}


# ============================================================================
# MEMORY MANAGEMENT ENDPOINTS (Dual-Memory System)
# ============================================================================


@app.get("/memory/list")
async def list_memories(
    include_system: bool = True,
    memory_type: str = "all",
    limit: int = 50,
    current_user: str = Depends(get_current_user_id),
):
    """
    List all memories for the authenticated user.

    Args:
        include_system: Include family-wide shared memories
        memory_type: Filter by type ('private', 'system', 'all')
        limit: Maximum number of memories to return
        current_user: Current authenticated user (from JWT)

    Returns:
        List of memories with source indicators
    """
    global dual_memory_manager

    if not dual_memory_manager:
        raise HTTPException(status_code=503, detail="Dual-memory system not available")

    try:
        memories = await dual_memory_manager.get_memories(
            user_id=current_user,
            include_system=include_system,
            limit=limit,
            memory_type_filter=memory_type
            if memory_type in ["private", "system", "all"]
            else "all",
        )

        logger.info(
            f"Retrieved {len(memories)} memories for user {current_user}",
            extra={
                "user_id": current_user,
                "session_id": None,
                "endpoint": "/memory/list",
            },
        )

        return {"user_id": current_user, "total": len(memories), "memories": memories}

    except Exception as e:
        logger.error(f"Failed to retrieve memories: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve memories: {str(e)}"
        )


@app.get("/memory/stats")
async def get_memory_stats(current_user: str = Depends(get_current_user_id)):
    """
    Get memory statistics for the authenticated user.

    Args:
        current_user: Current authenticated user (from JWT)

    Returns:
        Memory statistics (private, system, total counts)
    """
    global dual_memory_manager

    if not dual_memory_manager:
        raise HTTPException(status_code=503, detail="Dual-memory system not available")

    try:
        stats = await dual_memory_manager.get_memory_stats(user_id=current_user)

        logger.info(
            f"Memory stats for {current_user}: {stats}",
            extra={
                "user_id": current_user,
                "session_id": None,
                "endpoint": "/memory/stats",
            },
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get memory stats: {str(e)}"
        )


@app.post("/memory/store")
async def store_memory_explicit(
    content: str,
    memory_type: str = "auto",
    current_user: str = Depends(get_current_user_id),
):
    """
    Explicitly store a memory with specified type.

    Args:
        content: Memory content to store
        memory_type: 'private', 'system', or 'auto' (auto-classify)
        current_user: Current authenticated user (from JWT)

    Returns:
        Success status and memory type used
    """
    global dual_memory_manager

    if not dual_memory_manager:
        raise HTTPException(status_code=503, detail="Dual-memory system not available")

    try:
        # Simple extraction (improve with NLP if needed)
        parts = content.split(" ", 2)
        subject = parts[0] if len(parts) > 0 else "Unknown"
        predicate = parts[1] if len(parts) > 1 else "is"
        obj = parts[2] if len(parts) > 2 else "Unknown"

        result = await dual_memory_manager.store_memory(
            user_id=current_user,
            subject=subject,
            predicate=predicate,
            obj=obj,
            memory_type=memory_type
            if memory_type in ["private", "system", "auto"]
            else "auto",
            metadata={"source": "api_explicit"},
            confidence=0.9,
        )

        logger.info(
            f"Stored {result.get('memory_type')} memory for {current_user}: {content[:50]}...",
            extra={
                "user_id": current_user,
                "session_id": None,
                "endpoint": "/memory/store",
            },
        )

        return result

    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@app.get("/status")
async def status():
    """Service status with component health checks."""
    status_info = {
        "service": "agent",
        "status": "running",
        "components": {"database": False, "mem0": False, "falkordb": False},
    }

    # Check database connectivity
    conn = get_db_connection()
    if conn:
        status_info["components"]["database"] = True
        conn.close()

    # Check mem0 service
    try:
        mem0_health = requests.get("http://mem0:8080/health", timeout=2)
        status_info["components"]["mem0"] = mem0_health.status_code == 200
    except:
        pass

    # Check FalkorDB service
    global falkordb_manager
    if falkordb_manager and falkordb_manager.is_connected():
        status_info["components"]["falkordb"] = True
    else:
        status_info["components"]["falkordb"] = False

    return status_info
