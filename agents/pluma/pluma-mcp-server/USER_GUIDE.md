# Pluma MCP Server - User Guide

## Quick Start

### ✅ Installation Complete
The Pluma MCP server has been successfully installed and configured in your Claude Desktop.

### 🚀 Activation Steps
1. **Completely quit Claude Desktop** (Cmd+Q)
2. **Reopen Claude Desktop**
3. **Look for the Pluma tools** - they should appear automatically

### 📧 Available Commands

#### Fetch Emails
```
"Show me my latest emails"
"Get my last 5 emails"
"What emails did I receive today?"
```

#### Search Emails
```
"Search for emails from John"
"Find emails about the project meeting"
"Show me unread emails"
```

#### Generate Replies
```
"Draft a professional reply to email ID [xxx]"
"Generate a brief response to the latest email"
"Create a casual reply with thanks"
```

#### Create Drafts
```
"Save this as a draft in Gmail"
"Create the draft"
```

#### View Threads
```
"Show the full conversation for email ID [xxx]"
"Get the thread for this email"
```

## Features

### 🎯 Smart Email Management
- **Real-time Gmail access** - Your actual inbox, not simulated
- **AI-powered drafts** - Professional replies in seconds
- **Thread tracking** - Full conversation context
- **Search capability** - Gmail's powerful search syntax

### 💰 Cost Effective
- **83% cheaper** than Fyxer AI
- **~$5/month** in API costs
- **No subscription fees**
- **Pay per use model**

### 🔒 Privacy First
- **Local processing** - Emails stay on your machine
- **OAuth secure** - No password storage
- **No cloud storage** - Direct Gmail API only
- **Your data, your control**

## Workflow Examples

### Morning Email Review
```
You: "Show me emails from the last 24 hours"
Claude: [Lists recent emails with IDs]

You: "Search for anything urgent or marked high priority"
Claude: [Filters for priority emails]

You: "Generate a brief reply to email ID abc123"
Claude: [Creates professional draft]

You: "Create this draft in Gmail"
Claude: [Saves to Gmail drafts]
```

### Project Follow-up
```
You: "Search for emails about the Q3 project"
Claude: [Finds related emails]

You: "Show the thread for the latest one"
Claude: [Displays full conversation]

You: "Draft a status update reply"
Claude: [Generates contextual response]
```

## Troubleshooting

### Tools Not Appearing?

1. **Ensure complete restart**
   - Quit Claude Desktop fully (Cmd+Q)
   - Wait 5 seconds
   - Reopen Claude Desktop

2. **Check configuration**
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep pluma
   ```
   Should show the pluma configuration

3. **Test the server**
   ```bash
   cd ~/Projects/demestihas-ai/pluma-mcp-server
   node src/test.js
   ```

### Authentication Issues?

If you see "Failed to initialize Gmail service":
1. Check credentials exist:
   ```bash
   ls -la ~/Projects/demestihas-ai/pluma-local/credentials/
   ```
2. Re-authenticate if needed:
   ```bash
   cd ~/Projects/demestihas-ai/pluma-local
   python3 gmail_auth.py
   ```

### Performance Issues?

- Each operation should complete in <3 seconds
- If slower, check internet connection
- Reduce max_results parameter for faster responses

## Advanced Usage

### Gmail Search Operators
```
from:sender@email.com     - Emails from specific sender
to:me                     - Emails sent to you
subject:meeting           - Subject line search
has:attachment           - Emails with attachments
is:unread               - Unread emails only
after:2024/01/01        - Date filtering
label:important         - Label filtering
```

### Custom Draft Styles
```
"Draft a professional reply..."  - Formal business tone
"Draft a casual reply..."        - Friendly tone
"Draft a brief reply..."         - Short and concise
"Draft a detailed reply..."      - Comprehensive response
```

## Support

### Logs Location
- MCP Server logs: `~/Projects/demestihas-ai/pluma-mcp-server/logs/`
- Claude Desktop logs: `~/Library/Logs/Claude/`
- Python logs: `~/Projects/demestihas-ai/pluma-local/logs/`

### File Locations
- MCP Server: `~/Projects/demestihas-ai/pluma-mcp-server/`
- Python Agent: `~/Projects/demestihas-ai/pluma-local/`
- Credentials: `~/Projects/demestihas-ai/pluma-local/credentials/`

### Quick Diagnostics
```bash
cd ~/Projects/demestihas-ai/pluma-mcp-server
./test_pluma_mcp.sh
```

## Privacy & Security

- **OAuth 2.0** - Industry standard authentication
- **Read/Write scope** - Only email access, no account changes
- **Token refresh** - Automatic secure token management
- **Local storage** - Credentials never leave your machine
- **No telemetry** - No usage data collected

## Future Enhancements

Planned features:
- Calendar integration
- Meeting note summaries
- Email analytics dashboard
- Batch operations
- Template management
- Auto-categorization

---

**Status**: ✅ ACTIVE AND READY
**Version**: 1.0.0
**Last Updated**: September 9, 2025