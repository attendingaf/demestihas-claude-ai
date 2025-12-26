#!/usr/bin/env python3
"""
EA Profile Ingestion Script

This script ingests the comprehensive EA user profile into FalkorDB
via the document ingestion API endpoint.

The profile will be:
1. Stored in Mem0 for semantic retrieval
2. Extracted into knowledge triples by LLM
3. Persisted in FalkorDB as structured facts

Usage:
    python ingest_ea_profile.py [--user USER_ID] [--jwt-token TOKEN]
"""

import os
import sys
import argparse
import requests
import json
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8000")
INGEST_ENDPOINT = f"{AGENT_SERVICE_URL}/ingest/document"
PROFILE_FILE = "/root/EA Agent: Preferences and Personality Profile"
DEFAULT_USER_ID = "default_user"


# ============================================================================
# PROFILE INGESTION
# ============================================================================


def read_profile_file(file_path: str) -> str:
    """
    Reads the EA profile file.

    Args:
        file_path: Path to profile file

    Returns:
        Profile text content
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"✅ Successfully read profile file: {file_path}")
        print(f"   Content length: {len(content)} characters")
        print(f"   Lines: {content.count(chr(10)) + 1}")

        return content

    except FileNotFoundError:
        print(f"❌ Error: Profile file not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading profile file: {str(e)}")
        sys.exit(1)


def create_jwt_token(user_id: str, secret: str) -> str:
    """
    Creates a JWT token for authentication.

    This is a simple implementation for testing.
    In production, tokens should be issued by the auth service.

    Args:
        user_id: User identifier
        secret: JWT secret key

    Returns:
        Encoded JWT token
    """
    try:
        from jose import jwt
        from datetime import timedelta

        expiration = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": user_id,
            "exp": expiration,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, secret, algorithm="HS256")
        print(f"✅ Generated JWT token for user: {user_id}")

        return token

    except ImportError:
        print("⚠️  Warning: python-jose not installed. Using provided token only.")
        return ""
    except Exception as e:
        print(f"⚠️  Warning: Could not generate JWT token: {str(e)}")
        return ""


def ingest_profile(
    profile_text: str,
    user_id: str,
    jwt_token: str = None,
    source_name: str = "EA_Profile_Master",
    source_type: str = "file",
) -> dict:
    """
    Ingests the EA profile via the document ingestion API.

    Args:
        profile_text: Full profile text
        user_id: User identifier
        jwt_token: JWT authentication token (optional for local testing)
        source_name: Name of the source document
        source_type: Type of source (file, email, manual)

    Returns:
        API response dictionary
    """
    print(f"\n{'=' * 60}")
    print("INGESTING EA PROFILE INTO FALKORDB")
    print(f"{'=' * 60}")
    print(f"  Endpoint: {INGEST_ENDPOINT}")
    print(f"  User ID: {user_id}")
    print(f"  Source: {source_name}")
    print(f"  Type: {source_type}")
    print(f"  Auth: {'Enabled' if jwt_token else 'Disabled (local mode)'}")
    print(f"{'=' * 60}\n")

    # Prepare request payload
    payload = {
        "user_id": user_id,
        "document_text": profile_text,
        "source_name": source_name,
        "source_type": source_type,
    }

    # Prepare headers
    headers = {"Content-Type": "application/json"}

    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    try:
        print("📤 Sending ingestion request...")
        print(f"   Payload size: {len(json.dumps(payload))} bytes")
        print(f"   Profile length: {len(profile_text)} characters\n")

        # Make the request
        response = requests.post(
            INGEST_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=60,  # Allow up to 60 seconds for processing
        )

        print(f"📥 Response received: HTTP {response.status_code}\n")

        # Parse response
        if response.status_code in [200, 202]:
            result = response.json()

            print("✅ INGESTION SUCCESSFUL!\n")
            print(f"{'=' * 60}")
            print("INGESTION RESULTS")
            print(f"{'=' * 60}")
            print(f"Status: {result.get('status', 'Unknown')}")
            print(f"Message: {result.get('message', 'No message')}")
            print(f"Timestamp: {result.get('timestamp', 'Unknown')}")
            print(f"{'=' * 60}\n")

            # Show write status details
            write_status = result.get("write_status", {})

            if write_status:
                print("WRITE STATUS DETAILS:")
                print(f"{'=' * 60}")

                # Mem0 status
                mem0_status = write_status.get("mem0_status", {})
                if mem0_status:
                    mem0_success = mem0_status.get("success", False)
                    print(
                        f"Mem0 (Semantic):     {'✅ Success' if mem0_success else '❌ Failed'}"
                    )
                    if not mem0_success:
                        print(f"  Error: {mem0_status.get('error', 'Unknown')}")

                # Graphiti/FalkorDB status
                graphiti_status = write_status.get("graphiti_status", {})
                if graphiti_status:
                    graphiti_success = graphiti_status.get("success", False)
                    triples_added = graphiti_status.get("triples_added", 0)
                    total_triples = graphiti_status.get("total_triples", 0)

                    print(
                        f"FalkorDB (Structured): {'✅ Success' if graphiti_success else '❌ Failed'}"
                    )
                    print(f"  Triples extracted: {total_triples}")
                    print(f"  Triples persisted: {triples_added}")

                    if not graphiti_success:
                        print(f"  Error: {graphiti_status.get('error', 'Unknown')}")
                        print(
                            f"  Message: {graphiti_status.get('message', 'No message')}"
                        )

                    # Show any errors
                    errors = graphiti_status.get("errors", [])
                    if errors:
                        print(f"\n  Errors encountered ({len(errors)}):")
                        for i, error in enumerate(errors[:3], 1):
                            print(f"    {i}. {error}")
                        if len(errors) > 3:
                            print(f"    ... and {len(errors) - 3} more")

                # Triples extracted count
                triples_extracted = write_status.get("triples_extracted", 0)
                print(f"\nTotal Knowledge Facts: {triples_extracted}")
                print(f"{'=' * 60}\n")

            return result

        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED")
            print("   Status: 401 Unauthorized")
            print("   Message: Invalid or missing JWT token")
            print("\n💡 TIP: Provide a valid JWT token with --jwt-token")
            print("   Or generate one with:")
            print("   python ingest_ea_profile.py --generate-token\n")
            return {"error": "authentication_failed", "status_code": 401}

        elif response.status_code == 422:
            print("❌ VALIDATION ERROR")
            print("   Status: 422 Unprocessable Entity")
            print("   Message: Request payload validation failed")
            print(f"\n   Response: {response.text}\n")
            return {"error": "validation_failed", "status_code": 422}

        else:
            print(f"❌ INGESTION FAILED")
            print(f"   Status: HTTP {response.status_code}")
            print(f"   Response: {response.text}\n")
            return {"error": "ingestion_failed", "status_code": response.status_code}

    except requests.exceptions.Timeout:
        print("❌ REQUEST TIMEOUT")
        print("   The ingestion request took longer than 60 seconds.")
        print("   The processing may still be ongoing in the background.\n")
        return {"error": "timeout"}

    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR")
        print(f"   Could not connect to agent service at {AGENT_SERVICE_URL}")
        print("   Make sure the agent service is running:\n")
        print("   docker-compose ps agent")
        print("   docker logs demestihas-agent --tail 20\n")
        return {"error": "connection_failed"}

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def verify_ingestion(user_id: str, jwt_token: str = None) -> bool:
    """
    Verifies that the profile was successfully ingested by querying the chat endpoint.

    Args:
        user_id: User identifier
        jwt_token: JWT authentication token

    Returns:
        True if verification successful
    """
    print(f"\n{'=' * 60}")
    print("VERIFYING INGESTION")
    print(f"{'=' * 60}\n")

    chat_endpoint = f"{AGENT_SERVICE_URL}/chat"

    payload = {"message": "Tell me three things you know about me", "user_id": user_id}

    headers = {"Content-Type": "application/json"}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    try:
        print("📤 Testing knowledge retrieval...")
        print(f"   Query: {payload['message']}\n")

        response = requests.post(
            chat_endpoint, json=payload, headers=headers, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            agent_response = result.get("response", "")

            print("✅ VERIFICATION SUCCESSFUL!\n")
            print("Agent Response (first 500 chars):")
            print(f"{'=' * 60}")
            print(agent_response[:500])
            if len(agent_response) > 500:
                print("...")
            print(f"{'=' * 60}\n")

            # Check if response contains knowledge (not "I don't know")
            if (
                "don't know" in agent_response.lower()
                or "don't have" in agent_response.lower()
            ):
                print("⚠️  WARNING: Agent claims it doesn't know anything about you")
                print("   This might indicate the ingestion didn't work properly")
                print("   Or the knowledge hasn't been extracted yet\n")
                return False
            else:
                print("✅ Agent successfully retrieved knowledge about you!\n")
                return True
        else:
            print(f"❌ Verification failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}\n")
            return False

    except Exception as e:
        print(f"❌ Verification error: {str(e)}\n")
        return False


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest EA Profile into FalkorDB Knowledge Graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest profile for default user (no auth)
  python ingest_ea_profile.py

  # Ingest with specific user ID
  python ingest_ea_profile.py --user EA

  # Ingest with JWT authentication
  python ingest_ea_profile.py --jwt-token YOUR_TOKEN_HERE

  # Generate JWT token for user
  python ingest_ea_profile.py --generate-token --user EA

  # Verify existing ingestion
  python ingest_ea_profile.py --verify-only
        """,
    )

    parser.add_argument(
        "--user",
        type=str,
        default=DEFAULT_USER_ID,
        help=f"User ID for profile ingestion (default: {DEFAULT_USER_ID})",
    )

    parser.add_argument(
        "--jwt-token",
        type=str,
        default=None,
        help="JWT authentication token (optional for local testing)",
    )

    parser.add_argument(
        "--generate-token",
        action="store_true",
        help="Generate a JWT token for the specified user (requires JWT_SECRET env var)",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing ingestion, don't ingest again",
    )

    parser.add_argument(
        "--profile-file",
        type=str,
        default=PROFILE_FILE,
        help=f"Path to profile file (default: {PROFILE_FILE})",
    )

    args = parser.parse_args()

    # Handle token generation
    if args.generate_token:
        jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        token = create_jwt_token(args.user, jwt_secret)
        if token:
            print(f"\nGenerated JWT Token:")
            print(f"{'=' * 60}")
            print(token)
            print(f"{'=' * 60}\n")
            print("Use this token with:")
            print(f"python ingest_ea_profile.py --jwt-token {token}\n")
        sys.exit(0)

    # Handle verify-only mode
    if args.verify_only:
        verify_ingestion(args.user, args.jwt_token)
        sys.exit(0)

    # Read profile file
    profile_text = read_profile_file(args.profile_file)

    # Show preview
    print(f"\nProfile Preview (first 300 characters):")
    print(f"{'=' * 60}")
    print(profile_text[:300])
    print("...")
    print(f"{'=' * 60}\n")

    # Confirm ingestion
    print("⚠️  About to ingest profile into FalkorDB")
    print(f"   User: {args.user}")
    print(f"   This will extract knowledge triples and persist them.\n")

    confirmation = input("Continue? (yes/no): ")
    if confirmation.lower() not in ["yes", "y"]:
        print("❌ Ingestion cancelled by user.\n")
        sys.exit(0)

    # Ingest profile
    result = ingest_profile(
        profile_text=profile_text,
        user_id=args.user,
        jwt_token=args.jwt_token,
        source_name="EA_Profile_Master_v1",
        source_type="file",
    )

    # Check result
    if result.get("error"):
        print("❌ Ingestion failed. See error details above.\n")
        sys.exit(1)

    # Verify ingestion
    print("\nWould you like to verify the ingestion by testing knowledge retrieval?")
    verify_confirmation = input("Run verification? (yes/no): ")

    if verify_confirmation.lower() in ["yes", "y"]:
        verify_ingestion(args.user, args.jwt_token)

    print("\n✅ Profile ingestion complete!\n")


if __name__ == "__main__":
    main()
