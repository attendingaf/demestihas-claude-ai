# OAuth Client Setup Instructions

## Quick Setup (5 minutes)

### Step 1: Create OAuth Client in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project: **md2-4444**
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. Application type: **Desktop app**
6. Name: **Huata Calendar Agent**
7. Click **CREATE**
8. Click **DOWNLOAD JSON** on the popup

### Step 2: Save OAuth Client Credentials

1. Rename the downloaded file to `oauth_client_secret.json`
2. Move it to this directory: `/Users/menedemestihas/Projects/demestihas-ai/huata/credentials/`
3. The file should be at: `credentials/oauth_client_secret.json`

### Step 3: Run OAuth Setup

```bash
cd /Users/menedemestihas/Projects/demestihas-ai/huata
python setup_oauth.py
```

- A browser window will open
- Sign in as **menelaos4@gmail.com**
- Click **Allow** to grant calendar access
- Setup will complete automatically

### Step 4: Verify Setup

```bash
# Restart Huata with new OAuth
docker-compose down
docker-compose up -d

# Check OAuth status
docker exec huata-calendar-agent python claude_interface.py check
```

You should see:
```
✅ OAuth initialized: 6 calendars accessible
```

## File Structure After Setup

```
credentials/
├── oauth_client_secret.json       # OAuth client config (from Google)
├── oauth_tokens.enc              # Encrypted user tokens (created by setup)
├── encryption.key                # Encryption key (created by setup)
├── OAUTH_SETUP_INSTRUCTIONS.md  # This file
└── oauth_client_secret.json.template  # Template for reference
```

## Troubleshooting

### "Credentials not found"
- Ensure `oauth_client_secret.json` is in the `credentials/` directory
- Check file name is exactly `oauth_client_secret.json`

### "No refresh token received"
1. Go to https://myaccount.google.com/permissions
2. Remove "Huata Calendar Agent" if it exists
3. Run `python setup_oauth.py` again
4. Make sure to click "Allow" on all requested permissions

### "Calendar not accessible"
- Ensure you logged in as menelaos4@gmail.com
- Check all 6 calendars are visible in Google Calendar web
- Re-run setup if needed

### Docker can't find tokens
- Ensure Docker volume mapping is correct in docker-compose.yml
- Check credentials directory has read permissions
- Restart Docker containers after OAuth setup

## Security Notes

- `oauth_tokens.enc` contains encrypted access tokens
- `encryption.key` is the decryption key - keep secure
- Never commit these files to git (they're in .gitignore)
- Tokens auto-refresh, no manual renewal needed

## Next Steps

After successful OAuth setup:
1. Test natural language queries return real events
2. Create/update/delete test events
3. Remove old service account files (optional)
4. Update MCP configuration to use OAuth Huata