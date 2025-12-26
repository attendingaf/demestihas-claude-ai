# Pluma Local - Gmail Email Agent for Claude Desktop

A standalone local implementation of the Pluma email agent for testing with Claude Desktop. This version runs entirely on your local machine without Docker containers.

## Features

- ✉️ Gmail OAuth2 authentication
- 📧 Fetch and read latest emails
- 🤖 Generate draft replies using Claude API
- 📝 Create drafts directly in Gmail
- 💾 Local Redis caching (optional)
- 🎨 Interactive test interface

## Prerequisites

- Python 3.8+
- Gmail account
- Anthropic API key
- Redis (optional, for caching)
- Google Cloud Project with Gmail API enabled

## Quick Start

### 1. Clone and Navigate

```bash
cd pluma-local
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Gmail API

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your project name

#### Step 2: Enable Gmail API

1. In your Google Cloud project, go to **APIs & Services > Library**
2. Search for "Gmail API"
3. Click on it and press **Enable**

#### Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - Choose **External** user type
   - Fill required fields:
     - App name: "Pluma Local"
     - User support email: your email
     - Developer contact: your email
   - Add scopes: `https://www.googleapis.com/auth/gmail.modify`
   - Add your email as a test user
4. For Application type, choose **Desktop app**
5. Name it "Pluma Local"
6. Click **Create**

#### Step 4: Download Credentials

1. Find your OAuth 2.0 Client ID in the credentials list
2. Click the download button (⬇)
3. Save as `credentials.json` in `pluma-local/credentials/`

### 4. Run Setup Script

```bash
python setup.py
```

This will:
- Check dependencies
- Create necessary directories
- Guide you through Gmail setup
- Configure environment variables
- Test Gmail authentication
- Check Redis connection

### 5. First-Time Authentication

When you first run the setup, a browser window will open for Gmail authentication:
1. Choose your Gmail account
2. Review permissions (read/modify emails)
3. Click "Allow"
4. Authentication token will be saved locally

## Usage

### Interactive Test Interface

The easiest way to test Pluma:

```bash
python test_interface.py
```

Features:
- Fetch latest emails
- Generate draft replies with Claude
- Create Gmail drafts
- View email details
- Monitor cache statistics

### Direct Python Usage

```python
from pluma_local import LocalPlumaAgent

# Initialize agent
agent = LocalPlumaAgent()
agent.initialize()

# Fetch emails
emails = agent.fetch_latest_emails(max_results=5)

# Generate draft reply
if emails:
    draft = agent.generate_draft_reply(
        emails[0], 
        instructions="Be friendly and professional"
    )
    
    # Create Gmail draft
    draft_id = agent.create_gmail_draft(emails[0], draft)
    print(f"Draft created: {draft_id}")
```

### Run Automated Tests

```bash
python test_pluma_local.py
```

## Configuration

### Environment Variables (.env)

```env
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
PLUMA_DRAFT_STYLE=professional  # or casual, friendly, formal

# Redis (optional - uses defaults)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Redis Setup (Optional)

Pluma works without Redis, but caching improves performance.

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Use WSL or Docker:
```bash
docker run -d -p 6379:6379 redis
```

## File Structure

```
pluma-local/
├── credentials/           # Gmail OAuth credentials (gitignored)
│   ├── credentials.json   # OAuth client config (from Google)
│   └── token.pickle      # Stored auth token
├── logs/                 # Application logs
├── gmail_auth.py         # Gmail OAuth handler
├── pluma_local.py        # Main agent implementation
├── test_interface.py     # Interactive testing UI
├── test_pluma_local.py   # Automated tests
├── setup.py              # Setup wizard
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
└── README.md            # This file
```

## Troubleshooting

### Gmail Authentication Issues

**"Access blocked" error:**
- Ensure OAuth consent screen is configured
- Add your email as a test user
- Check that Gmail API is enabled

**Token expired:**
```bash
rm credentials/token.pickle
python setup.py  # Re-authenticate
```

### Redis Connection Failed

Pluma works without Redis. To disable warnings:
- Continue without Redis (caching disabled)
- Or install/start Redis per instructions above

### API Key Issues

**Anthropic API errors:**
- Verify API key in `.env` file
- Check key validity at [Anthropic Console](https://console.anthropic.com/)
- Ensure you have API credits

### Permission Errors

**"Insufficient permission" from Gmail:**
- Delete `credentials/token.pickle`
- Re-run `python setup.py`
- Ensure scope includes `gmail.modify`

## Security Notes

- **Never commit** `credentials.json` or `token.pickle`
- Keep `.env` file local (gitignored)
- Token expires after 7 days of inactivity
- Use test Gmail account for development

## Testing Workflow

1. **Setup**: Run `setup.py` to configure everything
2. **Test Auth**: Verify Gmail connection works
3. **Fetch Emails**: Use test interface to fetch recent emails
4. **Generate Drafts**: Test Claude API integration
5. **Create Drafts**: Verify Gmail draft creation
6. **Check Gmail**: Open Gmail to see created drafts

## Limitations

- Desktop application OAuth (not web-based)
- Single Gmail account at a time
- Rate limits apply (Gmail API and Claude API)
- Draft creation only (no sending)

## Next Steps

After local testing succeeds:
1. Deploy to VPS for production use
2. Set up web-based OAuth flow
3. Add multiple account support
4. Implement email sending features

## Support

For issues:
- Check troubleshooting section
- Review logs in `logs/pluma_local.log`
- Verify all setup steps completed
- Ensure APIs are enabled and keys valid