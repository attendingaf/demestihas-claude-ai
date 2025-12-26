#!/usr/bin/env python3
"""
EA Agent Profile Bootstrap Script

This script reads the EA Agent personality profile and ingests it into
both Mem0 (semantic) and Graphiti (structured) memory systems.
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
USER_ID = "executive_mene"
SOURCE_NAME = "Preferences_and_Personality_Profile"
SOURCE_TYPE = "manual"
API_ENDPOINT = "http://localhost:8000/ingest/document"

# File paths to try
POSSIBLE_FILE_PATHS = [
    "/root/EA Agent: Preferences and Personality Profile",
    "/root/EA Agent - Preferences and Personality Profile.txt",
    "/root/EA_Agent_Preferences_and_Personality_Profile.txt",
    "./EA Agent: Preferences and Personality Profile",
]


def find_profile_file():
    """Locate the EA Agent profile file."""
    for file_path in POSSIBLE_FILE_PATHS:
        path = Path(file_path)
        if path.exists() and path.is_file():
            print(f"✓ Found profile file: {file_path}")
            return path

    print("✗ Profile file not found. Tried the following paths:")
    for path in POSSIBLE_FILE_PATHS:
        print(f"  - {path}")
    return None


def read_profile_content(file_path):
    """Read the complete profile content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"✓ Read {len(content)} characters from profile file")
        return content
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return None


def ingest_profile(document_text):
    """Send profile to the ingestion endpoint."""

    payload = {
        "user_id": USER_ID,
        "document_text": document_text,
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
    }

    print(f"\n📄 Initiating ingestion...")
    print(f"   User ID: {USER_ID}")
    print(f"   Source: {SOURCE_NAME}")
    print(f"   Type: {SOURCE_TYPE}")
    print(f"   Content length: {len(document_text)} characters")

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=60)

        print(f"\n📡 HTTP Status Code: {response.status_code}")

        if response.status_code == 202:
            result = response.json()
            print(f"✓ Ingestion accepted!")
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))

            # Extract write status
            write_status = result.get("write_status", {})
            mem0_success = write_status.get("mem0_status", {}).get("success", False)
            graphiti_success = write_status.get("graphiti_status", {}).get(
                "success", False
            )
            triples_count = write_status.get("triples_extracted", 0)

            print(f"\n{'=' * 60}")
            print(f"INGESTION SUMMARY")
            print(f"{'=' * 60}")
            print(f"Mem0 (Semantic):     {'✅' if mem0_success else '❌'}")
            print(f"Graphiti (Structured): {'✅' if graphiti_success else '❌'}")
            print(f"Triples Extracted:   {triples_count}")
            print(f"{'=' * 60}")

            if mem0_success and graphiti_success:
                print(f"\n🎉 BOOTSTRAP COMPLETE - EA Agent profile activated!")
                return True
            else:
                print(f"\n⚠️  Partial success - check logs for details")
                return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("✗ Request timed out - ingestion may still be processing")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to agent service - is it running?")
        return False
    except Exception as e:
        print(f"✗ Error during ingestion: {e}")
        return False


def main():
    """Main execution flow."""
    print("=" * 60)
    print("EA AGENT PROFILE BOOTSTRAP")
    print("=" * 60)

    # Step 1: Find the profile file
    file_path = find_profile_file()
    if not file_path:
        print("\n❌ Cannot proceed without profile file")
        print("\nTo use this script:")
        print("1. Place the profile file at one of the expected locations")
        print("2. Or provide the content via stdin:")
        print("   cat 'profile.txt' | python3 bootstrap_ea_profile.py --stdin")
        sys.exit(1)

    # Step 2: Read the profile content
    content = read_profile_content(file_path)
    if not content:
        print("\n❌ Failed to read profile content")
        sys.exit(1)

    # Step 3: Ingest the profile
    success = ingest_profile(content)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    # Check for stdin mode
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        print("Reading profile from stdin...")
        content = sys.stdin.read()
        if content:
            success = ingest_profile(content)
            sys.exit(0 if success else 1)
        else:
            print("✗ No content received from stdin")
            sys.exit(1)
    else:
        main()
