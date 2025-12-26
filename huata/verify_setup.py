#!/usr/bin/env python3
"""
Verify Huata Calendar Setup
Checks that all components are properly configured
"""

import os
import json
import sys

def check_credentials():
    """Check if Google credentials are present and valid"""
    cred_path = "/Users/menedemestihas/Projects/demestihas-ai/huata/credentials/huata-service-account.json"

    if not os.path.exists(cred_path):
        print(f"❌ Credentials file not found at: {cred_path}")
        return False

    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
            if 'client_email' in creds:
                print(f"✅ Found valid credentials for: {creds['client_email']}")
                return True
            else:
                print("❌ Credentials file missing client_email")
                return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def check_files():
    """Check if all required files exist"""
    required_files = [
        'calendar_tools.py',
        'claude_interface.py',
        'huata.py',
        'main.py',
        'Dockerfile',
        'docker-compose.yml',
        'requirements.txt'
    ]

    base_path = "/Users/menedemestihas/Projects/demestihas-ai/huata"
    all_present = True

    for file in required_files:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_present = False

    return all_present

def check_docker():
    """Check if Docker is running"""
    import subprocess
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is running")
            return True
        else:
            print("❌ Docker is not running")
            return False
    except:
        print("❌ Docker command not found")
        return False

def main():
    print("🔍 Verifying Huata Calendar Setup\n")

    print("📁 Checking required files:")
    files_ok = check_files()
    print()

    print("🔑 Checking Google credentials:")
    creds_ok = check_credentials()
    print()

    print("🐳 Checking Docker:")
    docker_ok = check_docker()
    print()

    if files_ok and creds_ok and docker_ok:
        print("✅ All checks passed! Ready to deploy.")
        print("\nNext steps:")
        print("1. Run: bash test_fixes.sh")
        print("2. Check logs: docker logs huata-calendar-agent")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
