#!/usr/bin/env python3
"""Setup script for Pluma Local - handles Gmail OAuth and environment configuration."""

import os
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

console = Console()

def check_requirements():
    """Check if required dependencies are installed."""
    console.print("\n[yellow]Checking requirements...[/yellow]")
    
    required_packages = [
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client',
        'redis',
        'anthropic',
        'python-dotenv',
        'rich'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        console.print(f"[red]Missing packages: {', '.join(missing)}[/red]")
        if Confirm.ask("Install missing packages?"):
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
            console.print("[green]✓ Packages installed[/green]")
        else:
            console.print("[red]Please install requirements manually:[/red]")
            console.print("pip install -r requirements.txt")
            return False
    else:
        console.print("[green]✓ All requirements satisfied[/green]")
    
    return True

def setup_directories():
    """Create necessary directories."""
    dirs = ['credentials', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    console.print("[green]✓ Directories created[/green]")

def setup_gmail_credentials():
    """Guide user through Gmail API setup."""
    console.print("\n[bold cyan]Gmail API Setup[/bold cyan]")
    
    credentials_path = Path("credentials/credentials.json")
    
    if credentials_path.exists():
        console.print("[green]✓ credentials.json already exists[/green]")
        if not Confirm.ask("Replace existing credentials?", default=False):
            return True
    
    console.print("\n[yellow]Follow these steps to set up Gmail API:[/yellow]\n")
    
    steps = [
        "1. Go to https://console.cloud.google.com/",
        "2. Create a new project or select an existing one",
        "3. Enable the Gmail API:",
        "   - Go to 'APIs & Services' > 'Library'",
        "   - Search for 'Gmail API'",
        "   - Click on it and press 'Enable'",
        "4. Create OAuth 2.0 credentials:",
        "   - Go to 'APIs & Services' > 'Credentials'",
        "   - Click 'Create Credentials' > 'OAuth client ID'",
        "   - If prompted, configure the OAuth consent screen first:",
        "     • Choose 'External' user type",
        "     • Fill in the required fields",
        "     • Add your email to test users",
        "   - For Application type, choose 'Desktop app'",
        "   - Give it a name (e.g., 'Pluma Local')",
        "5. Download the credentials:",
        "   - Click the download button (⬇) next to your OAuth 2.0 Client ID",
        "   - Save as 'credentials.json'"
    ]
    
    for step in steps:
        console.print(f"   {step}")
    
    console.print("\n[cyan]Once downloaded, place credentials.json in:[/cyan]")
    console.print(f"   {credentials_path.absolute()}")
    
    input("\nPress Enter when you've placed the credentials.json file...")
    
    if not credentials_path.exists():
        console.print("[red]❌ credentials.json not found[/red]")
        return False
    
    console.print("[green]✓ credentials.json found[/green]")
    return True

def setup_environment():
    """Set up environment variables."""
    console.print("\n[bold cyan]Environment Setup[/bold cyan]")
    
    env_path = Path(".env")
    
    if env_path.exists():
        console.print("[green]✓ .env file already exists[/green]")
        if not Confirm.ask("Update environment variables?", default=False):
            return True
    
    # Get Anthropic API key
    console.print("\n[yellow]Enter your Anthropic API key[/yellow]")
    console.print("Get one at: https://console.anthropic.com/account/keys")
    
    api_key = Prompt.ask("Anthropic API Key", password=True)
    
    # Get draft style preference
    draft_style = Prompt.ask(
        "Email draft style",
        choices=["professional", "casual", "friendly", "formal"],
        default="professional"
    )
    
    # Write .env file
    env_content = f"""# Pluma Local Configuration
ANTHROPIC_API_KEY={api_key}
PLUMA_DRAFT_STYLE={draft_style}

# Redis configuration (optional - uses defaults if not set)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    console.print("[green]✓ Environment configured[/green]")
    return True

def test_gmail_auth():
    """Test Gmail authentication."""
    console.print("\n[yellow]Testing Gmail authentication...[/yellow]")
    
    try:
        from gmail_auth import GmailAuthenticator
        auth = GmailAuthenticator()
        service = auth.get_service()
        
        if service:
            console.print("[green]✓ Gmail authentication successful![/green]")
            return True
        else:
            console.print("[red]❌ Gmail authentication failed[/red]")
            return False
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False

def check_redis():
    """Check if Redis is available."""
    console.print("\n[yellow]Checking Redis connection...[/yellow]")
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        console.print("[green]✓ Redis is running[/green]")
        return True
    except:
        console.print("[yellow]⚠ Redis not available[/yellow]")
        console.print("Pluma will work without caching")
        console.print("\nTo install Redis:")
        console.print("  macOS: brew install redis && brew services start redis")
        console.print("  Ubuntu: sudo apt-get install redis-server")
        console.print("  Windows: Use WSL or Docker")
        return False

def main():
    """Main setup function."""
    console.clear()
    rprint(Panel.fit(
        "[bold cyan]Pluma Local Setup[/bold cyan]\n"
        "Configure Gmail OAuth and environment for local testing",
        border_style="cyan"
    ))
    
    # Run setup steps
    steps = [
        ("Checking requirements", check_requirements),
        ("Creating directories", setup_directories),
        ("Setting up Gmail credentials", setup_gmail_credentials),
        ("Configuring environment", setup_environment),
        ("Testing Gmail authentication", test_gmail_auth),
        ("Checking Redis", check_redis)
    ]
    
    failed = []
    for step_name, step_func in steps:
        console.print(f"\n[bold]{step_name}...[/bold]")
        try:
            if not step_func():
                failed.append(step_name)
        except Exception as e:
            console.print(f"[red]Error in {step_name}: {e}[/red]")
            failed.append(step_name)
    
    # Summary
    console.print("\n" + "="*50)
    if not failed or (len(failed) == 1 and "Checking Redis" in failed):
        rprint(Panel.fit(
            "[bold green]✓ Setup Complete![/bold green]\n\n"
            "You can now run:\n"
            "  python test_interface.py - Interactive testing\n"
            "  python test_pluma_local.py - Automated tests\n"
            "  python pluma_local.py - Direct agent usage",
            border_style="green"
        ))
    else:
        console.print(f"[red]Setup incomplete. Failed steps: {', '.join(failed)}[/red]")
        console.print("Please address the issues and run setup again")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
        sys.exit(0)