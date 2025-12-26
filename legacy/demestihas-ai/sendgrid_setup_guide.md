# SendGrid Email Integration Setup Guide

## Quick Setup (5 minutes)

### 1. Create SendGrid Account
- Go to https://sendgrid.com/pricing/
- Sign up for **Free Plan** (100 emails/day)
- Verify your email address

### 2. Generate API Key
```bash
# In SendGrid Dashboard:
# Settings > API Keys > Create API Key
# Name: "Email-to-Task Integration"
# Permissions: Full Access (or Mail Send + Inbound Parse)
```

### 3. Set up Inbound Parse
```bash
# In SendGrid Dashboard:
# Settings > Inbound Parse > Add Host & URL

Host & URL Settings:
- Subdomain: tasks
- Domain: demestihas.com (or your domain)  
- Destination URL: http://178.156.170.161:8090/email/webhook
- Check "POST the raw, full MIME message"
```

### 4. DNS Configuration
```bash
# Add MX record to your domain:
# Type: MX
# Host/Name: tasks (or subdomain you chose)
# Value/Points to: mx.sendgrid.net  
# Priority: 10
# TTL: 3600 (1 hour)
```

### 5. Add Environment Variable
```bash
# SSH to VPS
ssh root@178.156.170.161

# Edit environment file
cd /root/demestihas-ai
echo "SENDGRID_WEBHOOK_KEY=your_api_key_here" >> .env
```

## Alternative: Email Provider Forwarding

If you don't want to set up MX records, use email forwarding:

### Gmail Forwarding
1. Set up email filter in Gmail
2. Forward emails matching criteria to: webhook-email@your-service.com
3. Use email service webhook to trigger our endpoint

### Postmark/Mailgun Alternative
Similar inbound email processing services that work with our webhook.

## Testing the Integration

### 1. Deploy the service
```bash
cd /root/demestihas-ai
./deploy_email_service.sh
```

### 2. Test webhook endpoint
```bash
./test_email_service.sh
```

### 3. Send test email
Send email to: tasks@demestihas.com (or your configured address)
- Subject: "Review quarterly report"
- Body: "Please review the Q4 report by Friday EOD"

### 4. Verify task creation
- Check Notion database for new task
- Monitor: `docker logs -f demestihas-email`
- Queue status: `curl http://localhost:8090/queue/status`

## Success Criteria

✅ **Email received** → Webhook endpoint receives POST  
✅ **AI parsing** → Tasks extracted from email content  
✅ **Task creation** → New entries in Notion database  
✅ **Context preserved** → Email details saved in task description  

## Troubleshooting

### Webhook not receiving emails
```bash
# Check SendGrid Event Webhook logs in dashboard
# Verify DNS MX record: dig MX tasks.demestihas.com
# Test webhook directly: curl -X POST http://178.156.170.161:8090/email/webhook
```

### Tasks not created
```bash
# Check service logs
docker logs demestihas-email

# Verify Anthropic API key
curl -s http://localhost:8090/health

# Check Notion integration
docker logs demestihas-yanay | grep -i notion
```

### Common Issues
- **SendGrid quota exceeded**: Upgrade plan or wait 24h reset
- **MX record not propagated**: Wait up to 24h for DNS propagation  
- **Webhook SSL issues**: Use HTTP endpoint until SSL configured
- **Task parsing errors**: Check Anthropic API key and credits

## Usage Examples

### Executive Email → Task
```
From: assistant@company.com
Subject: Board meeting prep
Body: Please prepare slides for board meeting next Tuesday

→ Creates task: "Prepare slides for board meeting" (Due: Next Tuesday, High priority)
```

### Project Email → Multiple Tasks  
```
From: project-manager@company.com
Subject: Sprint tasks
Body: We need to: 1) Update documentation, 2) Deploy to staging, 3) Schedule demo

→ Creates 3 tasks with extracted priorities and contexts
```

## Cost & Scaling

### SendGrid Free Tier
- **100 emails/day**: Sufficient for personal/small team use
- **Unlimited contacts**: No restriction on senders
- **Inbound Parse**: Included in free tier

### Anthropic Usage
- **Email parsing**: ~200 tokens per email (Claude Haiku)
- **Cost**: ~$0.0005 per email 
- **Daily estimate**: 100 emails = $0.05/day

### System Resources
- **Container**: ~50MB RAM, minimal CPU
- **Redis storage**: ~1KB per processed email
- **Processing time**: ~2-5 seconds per email

## Next Steps

After email integration is working:
1. **Family rollout** - Train family members on email forwarding
2. **Nina enhancement** - Calendar integration for scheduling emails
3. **Token tracking** - Monitor AI usage and costs
4. **Advanced parsing** - Handle attachments, email threads, priority detection
