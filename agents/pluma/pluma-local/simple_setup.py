#!/usr/bin/env python3
"""Simplified setup script for Pluma Local - no rich dependency."""

import os
import sys
from pathlib import Path

def check_requirements():
    """Check if required dependencies are installed."""
    print("\nChecking requirements...")
    
    required_packages = [
        ('google.auth', 'google-auth'),
        ('google_auth_oauthlib', 'google-auth-oauthlib'),  
        ('googleapiclient', 'google-api-python-client'),
        ('redis', 'redis'),
        ('anthropic', 'anthropic'),
        ('dotenv', 'python-dotenv')
    ]
    
    missing = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Install with: pip3 install --user " + " ".join(missing))
        return False
    else:
        print("✓ All requirements satisfied")
    
    return True

def setup_directories():
    """Create necessary directories."""
    dirs = ['credentials', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✓ Directories created")

def setup_environment():
    """Set up environment variables."""
    print("\nEnvironment Setup")
    
    env_path = Path(".env")
    
    if env_path.exists():
        print("✓ .env file already exists")
        update = input("Update environment variables? (y/N): ")
        if update.lower() != 'y':
            return True
    
    # Get Anthropic API key
    print("\nEnter your Anthropic API key")
    print("Get one at: https://console.anthropic.com/account/keys")
    
    api_key = input("Anthropic API Key: ").strip()
    
    if not api_key:
        print("API key is required!")
        return False
    
    # Get draft style preference
    print("\nEmail draft style options: professional, casual, friendly, formal")
    draft_style = input("Draft style (default: professional): ").strip()
    if not draft_style:
        draft_style = "professional"
    
    # Write .env file
    env_content = f"""# Pluma Local Configuration
ANTHROPIC_API_KEY={api_key}
PLUMA_DRAFT_STYLE={draft_style}

# Redis configuration (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✓ Environment configured")
    return True

def setup_gmail_credentials():
    """Guide user through Gmail API setup."""
    print("\nGmail API Setup")
    
    credentials_path = Path("credentials/credentials.json")
    
    if credentials_path.exists():
        print("✓ credentials.json already exists")
        replace = input("Replace existing credentials? (y/N): ")
        if replace.lower() != 'y':
            return True
    
    print("\nFollow these steps to set up Gmail API:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Enable the Gmail API:")
    print("   - Go to 'APIs & Services' > 'Library'")
    print("   - Search for 'Gmail API'")
    print("   - Click on it and press 'Enable'")
    print("4. Create OAuth 2.0 credentials:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click 'Create Credentials' > 'OAuth client ID'")
    print("   - If prompted, configure the OAuth consent screen:")
    print("     • Choose 'External' user type")
    print("     • Fill in required fields")
    print("     • Add your email to test users")
    print("   - For Application type, choose 'Desktop app'")
    print("   - Give it a name (e.g., 'Pluma Local')")
    print("5. Download the credentials:")
    print("   - Click the download button next to your OAuth 2.0 Client ID")
    print("   - Save as 'credentials.json'")
    print(f"\nPlace credentials.json in: {credentials_path.absolute()}")
    
    input("\nPress Enter when you've placed the credentials.json file...")
    
    if not credentials_path.exists():
        print("❌ credentials.json not found")
        return False
    
    print("✓ credentials.json found")
    return True

def check_redis():
    """Check if Redis is available."""
    print("\nChecking Redis connection...")
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        print("✓ Redis is running")
        return True
    except:
        print("⚠ Redis not available")
        print("Pluma will work without caching")
        print("\nTo install Redis:")
        print("  macOS: brew install redis && brew services start redis")
        print("  Ubuntu: sudo apt-get install redis-server")
        return False

def test_gmail_auth():
    """Test Gmail authentication."""
    print("\nTesting Gmail authentication...")
    
    try:
        from gmail_auth import GmailAuthenticator
        auth = GmailAuthenticator()
        service = auth.get_service()
        
        if service:
            print("✓ Gmail authentication successful!")
            return True
        else:
            print("❌ Gmail authentication failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 50)
    print("Pluma Local Setup")
    print("Configure Gmail OAuth and environment for local testing")
    print("=" * 50)
    
    # Run setup steps
    steps = [
        ("Checking requirements", check_requirements),
        ("Creating directories", setup_directories),
        ("Setting up Gmail credentials", setup_gmail_credentials),
        ("Configuring environment", setup_environment),
        ("Checking Redis", check_redis),
        ("Testing Gmail authentication", test_gmail_auth)
    ]
    
    failed = []
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            if not step_func():
                failed.append(step_name)
        except Exception as e:
            print(f"Error in {step_name}: {e}")
            failed.append(step_name)
    
    # Summary
    print("\n" + "="*50)
    if not failed or (len(failed) == 1 and "Checking Redis" in failed):
        print("✓ Setup Complete!")
        print("\nYou can now run:")
        print("  python3 test_interface.py - Interactive testing")
        print("  python3 test_pluma_local.py - Automated tests")
        print("  python3 pluma_local.py - Direct agent usage")
    else:
        print(f"Setup incomplete. Failed steps: {', '.join(failed)}")
        print("Please address the issues and run setup again")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled")
        sys.exit(0)