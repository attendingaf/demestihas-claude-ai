import time
import os
import re
from datetime import datetime

import requests
import streamlit.components.v1 as components

# Import login functionality
from login_page import check_authentication, show_login_page, show_user_profile
from memory_service import get_memory_service

import streamlit as st

# Configure page
st.set_page_config(
    page_title="DemestiChat",
    page_icon="🌃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import themes
from themes import NEO_PROFESSIONAL_CSS, LCARS_CSS, LCARS_ENHANCED_CSS, LCARS_HEADER_HTML

# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "LCARS (Star Trek)"  # Default to LCARS for family

# Inject CSS based on selected theme
if st.session_state.theme == "LCARS (Star Trek)":
    st.markdown(LCARS_ENHANCED_CSS, unsafe_allow_html=True)
else:
    st.markdown(NEO_PROFESSIONAL_CSS, unsafe_allow_html=True)

# Initialize font size in session state if not exists
if "font_size" not in st.session_state:
    st.session_state.font_size = 16

# Inject dynamic font size CSS
dynamic_font_css = f"""
<style>
/* Dynamic font sizing for chat messages */
.stChatMessage {{
    font-size: {st.session_state.font_size}px;
}}

.stChatMessage p {{
    font-size: {st.session_state.font_size}px;
}}

.stMarkdown {{
    font-size: {st.session_state.font_size}px;
}}
</style>
"""
st.markdown(dynamic_font_css, unsafe_allow_html=True)

# ============================================================================
# ARTIFACT DETECTION & RENDERING FUNCTIONS
# ============================================================================

def detect_artifacts(content):
    """
    Detect HTML and Mermaid code blocks in markdown content.
    Returns: (html_blocks, mermaid_blocks) as lists of tuples (code, start_pos, end_pos)
    """
    html_pattern = r'```html\n(.*?)```'
    mermaid_pattern = r'```mermaid\n(.*?)```'
    
    html_matches = [(m.group(1), m.start(), m.end()) for m in re.finditer(html_pattern, content, re.DOTALL)]
    mermaid_matches = [(m.group(1), m.start(), m.end()) for m in re.finditer(mermaid_pattern, content, re.DOTALL)]
    
    return html_matches, mermaid_matches

def render_html_artifact(html_code, index=0):
    """Render HTML in an iframe with preview."""
    with st.expander(f"🎨 HTML Preview #{index + 1}", expanded=True):
        components.html(html_code, height=400, scrolling=True)

def render_mermaid_artifact(mermaid_code, index=0):
    """Render Mermaid diagram using mermaid.js."""
    with st.expander(f"📊 Diagram Preview #{index + 1}", expanded=True):
        # Use mermaid.js via HTML component
        mermaid_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script>
                mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
            </script>
        </head>
        <body style="background-color: transparent; margin: 0; padding: 20px;">
            <div class="mermaid">
{mermaid_code}
            </div>
        </body>
        </html>
        """
        components.html(mermaid_html, height=400, scrolling=True)

def render_content_with_artifacts(content):
    """
    Render markdown content and detect/render any HTML or Mermaid artifacts.
    """
    # Detect artifacts
    html_blocks, mermaid_blocks = detect_artifacts(content)
    
    # If no artifacts, just render the content normally
    if not html_blocks and not mermaid_blocks:
        st.markdown(content)
        return
    
    # Render content with artifacts
    st.markdown(content)
    
    # Render HTML artifacts
    for idx, (html_code, _, _) in enumerate(html_blocks):
        render_html_artifact(html_code, idx)
    
    # Render Mermaid artifacts
    for idx, (mermaid_code, _, _) in enumerate(mermaid_blocks):
        render_mermaid_artifact(mermaid_code, idx)

# ============================================================================
# AGENT SERVICE CONFIGURATION
# ============================================================================

# Agent service configuration
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")
AGENT_PORT = os.getenv("AGENT_PORT", "8000")
AGENT_SERVICE_URL = f"http://{AGENT_HOST}:{AGENT_PORT}"
AGENT_STATUS_URL = f"{AGENT_SERVICE_URL}/health"
AGENT_AUTH_URL = AGENT_SERVICE_URL  # Alias for auth endpoints

# Check authentication status
if not check_authentication():
    # Show login page if not authenticated
    show_login_page()
    st.stop()  # Stop execution here until user logs in

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_id" not in st.session_state:
    st.session_state.chat_id = f"chat_{int(time.time())}"

if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = (
        set()
    )  # Track which message indices have feedback


# Initialize Memory Service
@st.cache_resource
def init_memory_service():
    """Initialize memory service with caching"""
    try:
        service = get_memory_service()
        return service
    except Exception as e:
        return None


memory_service = init_memory_service()

# Main title with LCARS header
st.title("🌃 DemestiChat")

# Add LCARS animated header if using LCARS theme
if st.session_state.theme == "LCARS (Star Trek)":
    st.markdown(LCARS_HEADER_HTML, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # 1. Chat History Section (New Commercial Feature)
    st.header("Chat History")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_id = f"chat_{int(time.time())}"
        st.rerun()
        
    # Fetch sessions from backend
    st.caption("Recent")
    with st.container():
        try:
            # Prepare headers with JWT token
            headers = {}
            if st.session_state.get("jwt_token"):
                headers["Authorization"] = f"Bearer {st.session_state.jwt_token}"
            
            # Fetch sessions from API
            sessions_response = requests.get(
                f"{AGENT_AUTH_URL}/api/sessions",
                params={"user_id": st.session_state.user_id, "limit": 10},
                headers=headers,
                timeout=5
            )
            
            if sessions_response.status_code == 200:
                sessions = sessions_response.json().get("sessions", [])
                
                if not sessions:
                    st.info("No recent chats")
                
                for session in sessions:
                    s_id = session.get("session_id")
                    # Format label: Use summary if available, else Date only (no time)
                    summary = session.get("summary")
                    ts_str = session.get("ended_at", "")
                    
                    if summary:
                        label = summary
                    elif ts_str:
                        try:
                            dt = datetime.fromisoformat(ts_str)
                            label = dt.strftime("%b %d") # Date only, no time
                        except:
                            label = "Chat"
                    else:
                        label = "Chat"
                            
                    # Highlight current session
                    type_ = "primary" if s_id == st.session_state.chat_id else "secondary"
                    
                    if st.button(label, key=f"sess_{s_id}", use_container_width=True, type=type_):
                        # Switch session
                        st.session_state.chat_id = s_id
                        st.session_state.messages = [] # Clear current view
                        
                        # Fetch history for this session
                        with st.spinner("Loading history..."):
                            hist_response = requests.get(
                                f"{AGENT_AUTH_URL}/api/history/{s_id}",
                                params={"user_id": st.session_state.user_id},
                                headers=headers,
                                timeout=10
                            )
                            if hist_response.status_code == 200:
                                st.session_state.messages = hist_response.json().get("messages", [])
                                st.rerun()
            elif sessions_response.status_code == 403 or sessions_response.status_code == 401:
                st.error("Session expired. Please login again.")
            else:
                st.error(f"Failed to load history: {sessions_response.status_code}")
                
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

    st.divider()

    # 2. Document Upload (Simplified & Collapsed)
    with st.expander("📎 Attach Documents", expanded=False):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "docx", "txt"],
            help="Upload documents for context",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            if st.button("📤 Upload", use_container_width=True):
                with st.spinner("Processing..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"user_id": st.session_state.user_id}
                        
                        # Upload to agent service
                        response = requests.post(
                            "http://agent:8000/api/documents/upload",
                            files=files,
                            data=data,
                            timeout=60,
                        )

                        if response.status_code == 200:
                            st.success("✅ Uploaded!")
                        else:
                            st.error("❌ Failed")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # 3. Settings (Consolidated)
    with st.expander("⚙️ Settings", expanded=False):
        # Theme
        st.caption("Theme")
        selected_theme = st.radio(
            "Theme",
            ["Neo-Professional", "LCARS (Star Trek)"],
            index=0 if st.session_state.theme == "Neo-Professional" else 1,
            label_visibility="collapsed"
        )
        if selected_theme != st.session_state.theme:
            st.session_state.theme = selected_theme
            st.rerun()
            
        st.divider()
        
        # Font Size
        st.caption("Text Size")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("➖", use_container_width=True):
                if st.session_state.font_size > 10:
                    st.session_state.font_size -= 2
                    st.rerun()
        with col2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px;'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
        with col3:
            if st.button("➕", use_container_width=True):
                if st.session_state.font_size < 32:
                    st.session_state.font_size += 2
                    st.rerun()
                    
        st.divider()
        
        # Clear Chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_id = f"chat_{int(time.time())}"
            st.rerun()

    st.divider()

    # 4. User Profile (Bottom)
    show_user_profile()

# Display chat messages from history
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # For assistant messages, separate reasoning trace from final answer
        if message["role"] == "assistant":
            full_content = message["content"]
            reasoning_trace = ""
            final_answer = full_content

            # Check if response contains the orchestrator walk-through
            # PRIORITY 1: Check for the robust separator
            separator = "===ORCHESTRATOR_SEPARATOR==="
            if separator in full_content:
                parts = full_content.split(separator)
                # Everything before the last separator is reasoning trace
                reasoning_trace = separator.join(parts[:-1]).strip()
                # Everything after is final answer
                final_answer = parts[-1].strip()
            
            # PRIORITY 2: Fallback for legacy messages (using "---")
            elif "## 🧠 Orchestrator Decision Walk-Through" in full_content and "---" in full_content:
                 # Find all occurrences of "---" separator
                separator_indices = [
                    i
                    for i, line in enumerate(full_content.split("\n"))
                    if line.strip() == "---"
                ]

                if len(separator_indices) >= 2:
                    # The final answer starts after the last "---" separator
                    lines = full_content.split("\n")
                    last_separator_idx = separator_indices[-1]

                    # Everything up to and including the last separator is reasoning trace
                    reasoning_trace = "\n".join(lines[: last_separator_idx + 1])

                    # Everything after the last separator is the final answer
                    final_answer = "\n".join(lines[last_separator_idx + 1 :]).strip()

                # If final answer is empty or too short, fall back to showing full content
                if not final_answer or len(final_answer) < 10:
                    final_answer = full_content
                    reasoning_trace = ""

            # Display final answer
            if final_answer:
                render_content_with_artifacts(final_answer)

            # Display the reasoning trace in collapsible expander (HIDDEN by default)
            if reasoning_trace:
                with st.expander("🔎 Orchestrator Reasoning Trace"):
                    st.markdown(reasoning_trace, unsafe_allow_html=True)

            # RLHF Rating Widget (only for assistant messages, only if feedback not yet submitted)
            if idx not in st.session_state.feedback_submitted:
                st.caption("**Rate this response:**")
                rating_key = f"rating_{idx}_{st.session_state.chat_id}"
                rating = st.radio(
                    "Score",
                    options=[1, 2, 3, 4, 5],
                    horizontal=True,
                    key=rating_key,
                    label_visibility="collapsed",
                )

                if st.button(
                    "Submit Feedback", key=f"submit_{idx}_{st.session_state.chat_id}"
                ):
                    # Submit feedback to backend
                    try:
                        # Find the corresponding user message (previous message)
                        user_msg = (
                            st.session_state.messages[idx - 1]["content"]
                            if idx > 0
                            and st.session_state.messages[idx - 1]["role"] == "user"
                            else ""
                        )

                        feedback_response = requests.post(
                            "http://agent:8000/feedback/submit",
                            json={
                                "user_id": st.session_state.user_id,
                                "session_id": st.session_state.chat_id,
                                "message_index": idx,
                                "score": rating,
                                "user_message": user_msg,
                                "agent_response": full_content,
                            },
                            timeout=10,
                        )

                        if feedback_response.status_code == 200:
                            st.session_state.feedback_submitted.add(idx)
                            st.success("✅ Feedback submitted successfully!")
                            st.rerun()
                        else:
                            st.error(
                                f"⚠️ Failed to submit feedback (Status {feedback_response.status_code})"
                            )
                    except Exception as e:
                        st.error(f"❌ Error submitting feedback: {str(e)}")
            else:
                st.caption("✅ Feedback submitted for this response")
        else:
            # For user messages, display as-is
            st.markdown(message["content"])

        # Display metadata if available
        if "metadata" in message and message["metadata"]:
            with st.expander("Message Details"):
                if "agent_type" in message["metadata"]:
                    st.caption(f"**Agent:** {message['metadata']['agent_type']}")
                if "timestamp" in message["metadata"]:
                    st.caption(f"**Time:** {message['metadata']['timestamp']}")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }
    )

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response with thinking indicator
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🤔 Thinking...")

        try:
            # Make POST request to agent service
            # Ensure we have a valid JWT token
            if not st.session_state.jwt_token:
                st.session_state.jwt_token = get_jwt_token(st.session_state.user_id)

            if not st.session_state.jwt_token:
                message_placeholder.error(
                    "❌ Authentication failed. Please refresh the page."
                )
                st.stop()

            response = requests.post(
                f"{AGENT_SERVICE_URL}/chat",
                headers={"Authorization": f"Bearer {st.session_state.jwt_token}"},
                json={
                    "message": prompt,
                    "user_id": st.session_state.user_id,
                    "chat_id": st.session_state.chat_id,
                },
                timeout=30,
            )

            # Handle successful response
            if response.status_code == 200:
                response_data = response.json()
                full_response = response_data.get("response", "No response received")
                agent_type = response_data.get("agent_type", "unknown")
                metadata = response_data.get("metadata", {})

                # Separate reasoning trace from final answer
                # The agent response format is:
                # ## 🧠 Orchestrator Decision Walk-Through
                # [reasoning content]
                # ---
                # [final answer]

                reasoning_trace = ""
                final_answer = full_response

                # Check if response contains the orchestrator walk-through
                # PRIORITY 1: Check for the robust separator
                separator = "===ORCHESTRATOR_SEPARATOR==="
                if separator in full_response:
                    parts = full_response.split(separator)
                    # Everything before the last separator is reasoning trace
                    reasoning_trace = separator.join(parts[:-1]).strip()
                    # Everything after is final answer
                    final_answer = parts[-1].strip()
                
                # PRIORITY 2: Fallback for legacy messages (using "---")
                elif "## 🧠 Orchestrator Decision Walk-Through" in full_response and "---" in full_response:
                     # Find all occurrences of "---" separator
                    separator_indices = [
                        i
                        for i, line in enumerate(full_response.split("\n"))
                        if line.strip() == "---"
                    ]

                    if len(separator_indices) >= 2:
                        # The final answer starts after the last "---" separator
                        lines = full_response.split("\n")
                        last_separator_idx = separator_indices[-1]

                        # Everything up to and including the last separator is reasoning trace
                        reasoning_trace = "\n".join(lines[: last_separator_idx + 1])

                        # Everything after the last separator is the final answer
                        final_answer = "\n".join(lines[last_separator_idx + 1 :]).strip()

                    # If final answer is empty or too short, fall back to showing full content
                    if not final_answer or len(final_answer) < 10:
                        final_answer = full_response
                        reasoning_trace = ""

                # Display the final answer immediately (ALWAYS visible)
                message_placeholder.markdown(final_answer)

                # Add assistant message to chat history (store full response)
                message_idx = len(st.session_state.messages)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": full_response,
                        "metadata": {
                            "agent_type": agent_type,
                            "timestamp": metadata.get(
                                "timestamp", datetime.utcnow().isoformat()
                            ),
                        },
                    }
                )

            # Handle error responses
            elif response.status_code == 422:
                error_message = "⚠️ Invalid request format. Please try again."
                message_placeholder.error(error_message)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "metadata": {"error": True},
                    }
                )

            elif response.status_code == 500:
                error_message = (
                    "⚠️ Agent service encountered an error. Please try again later."
                )
                message_placeholder.error(error_message)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "metadata": {"error": True},
                    }
                )

            else:
                error_message = f"⚠️ Unexpected response (Status {response.status_code}). Please try again."
                message_placeholder.error(error_message)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "metadata": {"error": True},
                    }
                )

        except requests.exceptions.Timeout:
            error_message = "⏱️ Request timed out. The agent service is taking too long to respond. Please try again."
            message_placeholder.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "metadata": {"error": True},
                }
            )

        except requests.exceptions.ConnectionError:
            error_message = "❌ Unable to connect to the agent service. Please ensure the service is running and try again."
            message_placeholder.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "metadata": {"error": True},
                }
            )

        except requests.exceptions.RequestException as e:
            error_message = f"❌ Network error: {str(e)}"
            message_placeholder.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "metadata": {"error": True},
                }
            )

        except Exception as e:
            error_message = f"❌ Unexpected error: {str(e)}"
            message_placeholder.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "metadata": {"error": True},
                }
            )

# Footer
st.divider()
st.caption(
    "DemestiChat Multi-Agent Orchestration System | Powered by FastAPI, Streamlit, Mem0, Graphiti & PostgreSQL"
)
