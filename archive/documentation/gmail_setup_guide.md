# Gmail OAuth Setup for Pluma Agent

**Pluma Agent Gmail Integration Setup**  
*Required for email drafting, inbox management, and meeting notes*

## Quick Setup (5 minutes)

### 1. Google Cloud Console Setup

1. **Visit**: https://console.cloud.google.com/
2. **Create Project** (if needed): "Demestihas AI Gmail"
3. **Enable Gmail API**:
   - APIs & Services → Library → Search "Gmail API" → Enable
4. **Create OAuth Credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client IDs
   - Application Type: "Desktop application"
   - Name: "Pluma Agent"
   - Download the JSON file as `credentials.json`

### 2. Upload Credentials to VPS

```bash
# Create credentials directory on VPS
ssh root@178.156.170.161 'mkdir -p /root/demestihas-ai/google_credentials'

# Upload credentials file
scp ~/Downloads/credentials.json root@178.156.170.161:/root/demestihas-ai/google_credentials/
```

### 3. Run OAuth Authorization

```bash
# Connect to VPS
ssh root@178.156.170.161

# Navigate to project
cd /root/demestihas-ai

# Run OAuth setup
docker exec -it demestihas-pluma python -c "
import os
os.chdir('/app')
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

flow = InstalledAppFlow.from_client_secrets_file('/app/google_credentials/credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save token
with open('/app/google_credentials/token.json', 'w') as token:
    token.write(creds.to_json())

print('✅ Gmail OAuth setup complete!')
"
```

**Alternative Method (if server doesn't have browser):**

```bash
# Generate auth URL
docker exec demestihas-pluma python -c "
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
flow = InstalledAppFlow.from_client_secrets_file('/app/google_credentials/credentials.json', SCOPES)
auth_url, _ = flow.authorization_url(prompt='consent')
print(f'Visit this URL: {auth_url}')
"

# Then paste the authorization code when prompted
```

### 4. Test Gmail Connection

```bash
# Test Pluma Gmail integration
docker exec demestihas-pluma python -c "
import asyncio
import sys
sys.path.append('/app')
from pluma import PlumaAgent

async def test_gmail():
    agent = PlumaAgent()
    if agent.gmail_service:
        profile = agent.gmail_service.users().getProfile(userId='me').execute()
        print(f'✅ Gmail connected: {profile[\"emailAddress\"]}')
        return True
    else:
        print('❌ Gmail not connected')
        return False

result = asyncio.run(test_gmail())
"
```

### 5. Test Email Functionality

```bash
# Test via @LycurgusBot
# Message: "draft reply to latest email"
# Message: "check my inbox status"
# Message: "organize my inbox"
```

## Troubleshooting

### "Authentication failed"
- Check that Gmail API is enabled in Google Cloud Console
- Verify credentials.json is in `/root/demestihas-ai/google_credentials/`
- Ensure OAuth consent screen is configured (internal use is fine)

### "Insufficient permissions"
- Required scopes: `https://www.googleapis.com/auth/gmail.modify`
- Re-run OAuth flow if scope was changed

### "Container can't access credentials"
- Verify volume mount: `./google_credentials:/app/google_credentials:ro`
- Check file permissions: `chmod 644 /root/demestihas-ai/google_credentials/*`

### "Rate limit exceeded" 
- Gmail API has quotas: 1 billion units/day (sufficient for personal use)
- Check Google Cloud Console → APIs & Services → Quotas

## Security Notes

- **Credentials are local**: OAuth tokens stored only in VPS container
- **Minimal scopes**: Only Gmail modify permission (read/write emails)
- **No data sharing**: All processing happens on your VPS
- **Revoke access**: Google Account → Security → Third-party apps (if needed)

## Usage After Setup

Once Gmail is connected, Pluma agent supports:

- **Email Drafting**: Learns your writing tone from sent emails
- **Smart Replies**: Context-aware responses matching your style
- **Inbox Management**: Auto-labeling, priority detection, newsletter filtering
- **Meeting Integration**: Convert Hermes transcripts to actionable summaries
- **Executive Assistant**: Email status, bulk operations, follow-up tracking

**Cost**: ~$5-10/month (Claude API) vs $336/year Fyxer AI = 83% savings

## Quick Commands Reference

```bash
# Check Pluma health
docker exec demestihas-pluma python -c "import asyncio; import sys; sys.path.append('/app'); from pluma import PlumaAgent; agent = PlumaAgent(); health = asyncio.run(agent.health_check()); print(health)"

# View Pluma logs
docker logs -f demestihas-pluma

# Restart Pluma (after credential changes)
docker-compose restart pluma

# Test latest email draft
docker exec demestihas-pluma python -c "
import asyncio
import sys
sys.path.append('/app')
from pluma import PlumaAgent

async def test_draft():
    agent = PlumaAgent()
    latest_id = await agent.get_latest_email_id()
    if latest_id:
        draft = await agent.draft_reply(latest_id)
        print(f'Draft confidence: {draft.confidence}')
        print(f'Subject: {draft.subject}')
    else:
        print('No emails found')

asyncio.run(test_draft())
"
```

---

**Next**: After Gmail setup, test complete integration via @LycurgusBot messaging for seamless family email assistance.
