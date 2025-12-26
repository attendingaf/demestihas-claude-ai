"""
Login Page for DemestiChat Family Access
Provides secure authentication for family members.
"""

import time
from typing import Dict, Optional

import os
import requests
import streamlit as st

# Configuration
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")
AGENT_PORT = os.getenv("AGENT_PORT", "8000")
AGENT_AUTH_URL = f"http://{AGENT_HOST}:{AGENT_PORT}"


def get_jwt_token_with_password(user_id: str, password: str) -> Optional[Dict]:
    """Authenticate and get JWT token with password."""
    try:
        response = requests.post(
            f"{AGENT_AUTH_URL}/auth/login",
            params={"user_id": user_id, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Invalid username or password"}
        else:
            return {"error": f"Login failed: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "Login request timed out. Please try again."}
    except Exception as e:
        return {"error": f"Login error: {str(e)}"}


def register_new_user(
    user_id: str, password: str, display_name: str, email: str
) -> Optional[Dict]:
    """Register a new family member."""
    try:
        response = requests.post(
            f"{AGENT_AUTH_URL}/auth/register",
            params={
                "user_id": user_id,
                "password": password,
                "display_name": display_name,
                "email": email,
                "role": "family",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get("detail", "Registration failed")
            return {"error": error_detail}
    except Exception as e:
        return {"error": f"Registration error: {str(e)}"}


def show_login_page():
    """Display the login page."""

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("🌃 DemestiChat")
        st.markdown("### Family Access Login")

        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.markdown("#### Sign In")

            with st.form("login_form"):
                login_user_id = st.text_input(
                    "Username",
                    key="login_username",
                    placeholder="Enter your username",
                    help="Your unique family member username",
                )

                login_password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password",
                    placeholder="Enter your password",
                )

                submitted = st.form_submit_button("Sign In", use_container_width=True)

                if submitted:
                    if not login_user_id or not login_password:
                        st.error("Please enter both username and password")
                    else:
                        with st.spinner("Authenticating..."):
                            result = get_jwt_token_with_password(
                                login_user_id, login_password
                            )

                        if result and "error" not in result:
                            # Successful login
                            st.session_state.authenticated = True
                            st.session_state.user_id = login_user_id
                            st.session_state.jwt_token = result.get("access_token")
                            st.session_state.user_info = result.get("user", {})
                            st.success(
                                f"Welcome back, {st.session_state.user_info.get('display_name', login_user_id)}!"
                            )
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(result.get("error", "Login failed"))

            if st.button("Guest Access", key="guest_btn", use_container_width=True):
                st.info("Guest access coming soon!")

        with tab2:
            st.markdown("#### Create Account")

            reg_user_id = st.text_input(
                "Username",
                key="reg_username",
                placeholder="Choose a username",
                help="Unique identifier (letters, numbers, underscore)",
            )

            reg_display_name = st.text_input(
                "Display Name",
                key="reg_display_name",
                placeholder="Your name",
                help="How you want to be called",
            )

            reg_email = st.text_input(
                "Email (Optional)",
                key="reg_email",
                placeholder="your.email@example.com",
                help="For password recovery (future feature)",
            )

            reg_password = st.text_input(
                "Password",
                type="password",
                key="reg_password",
                placeholder="Choose a strong password",
            )

            reg_password_confirm = st.text_input(
                "Confirm Password",
                type="password",
                key="reg_password_confirm",
                placeholder="Re-enter your password",
            )

            if st.button(
                "Create Account", key="register_btn", use_container_width=True
            ):
                # Validation
                if not reg_user_id or not reg_password or not reg_display_name:
                    st.error("Please fill in username, display name, and password")
                elif reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    with st.spinner("Creating account..."):
                        result = register_new_user(
                            reg_user_id,
                            reg_password,
                            reg_display_name,
                            reg_email if reg_email else None,
                        )

                    if result and "error" not in result:
                        st.success("Account created successfully! Please sign in.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(result.get("error", "Registration failed"))

        # Information section
        st.markdown("---")
        st.markdown(
            """
        <div style='text-align: center; color: #888; font-size: 0.9em;'>
            <p>🔒 Secure family authentication with encrypted passwords</p>
            <p>💾 All your conversations and memories are private</p>
            <p>🏠 Family-friendly AI assistant powered by advanced memory</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def check_authentication() -> bool:
    """Check if user is authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "jwt_token" not in st.session_state:
        st.session_state.jwt_token = None

    if "user_info" not in st.session_state:
        st.session_state.user_info = {}

    return st.session_state.authenticated


def logout():
    """Logout the current user."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.jwt_token = None
    st.session_state.user_info = {}
    st.session_state.messages = []
    st.rerun()


def show_user_profile():
    """Show user profile in sidebar."""
    if st.session_state.get("authenticated"):
        with st.sidebar:
            st.markdown("---")
            # st.markdown("### 👤 Profile")  <-- Removed as requested

            user_info = st.session_state.get("user_info", {})
            display_name = user_info.get("display_name", st.session_state.user_id)

            st.markdown(f"**{display_name}**")

            if st.button("🚪 Logout", use_container_width=True):
                logout()
