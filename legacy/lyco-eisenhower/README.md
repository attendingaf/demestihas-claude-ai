# Lyco Eisenhower Matrix Task Manager

A simple, family-focused task management system using the Eisenhower Matrix, designed for ADHD-friendly interaction via Telegram.

## 🎯 Quick Start

### For Family Users (Mene & Cindy)

1. **Open Telegram** and search for `@LycurgusBot`
2. **Send `/start`** to begin
3. **Add tasks naturally:**
   - "Schedule Persy's soccer registration due Friday"
   - "Add task: Review insurance documents urgent"
   - Just type any task and it will be added

### Common Commands

- **View tasks:**
  - "Show today" - See urgent tasks and today's due items
  - "Show matrix" - View all tasks in Eisenhower quadrants
  - "Show week" - Review tasks for the week
  
- **Task shortcuts:**
  - `/today` - Today's tasks
  - `/matrix` - Full matrix view
  - `/week` - Weekly tasks
  - `/help` - Command help

## 📊 Understanding the Eisenhower Matrix

Tasks are automatically sorted into four quadrants:

1. **🔴 DO FIRST** (Urgent & Important)
   - Crisis situations, deadlines today
   - Medical emergencies, critical family needs
   
2. **🟡 SCHEDULE** (Important, Not Urgent)  
   - Planning, prevention, improvement
   - Family activities, health checkups
   
3. **🟢 DELEGATE** (Urgent, Not Important)
   - Interruptions, some emails/calls
   - Tasks others could handle
   
4. **⚪ DON'T DO** (Not Urgent, Not Important)
   - Time wasters, busywork
   - Low-value activities

## 🚀 VPS Deployment Guide

### Prerequisites

- VPS with Docker and Docker Compose installed
- Telegram Bot Token (from @BotFather)
- Anthropic API Key (for Claude Haiku)
- Notion Integration Token and Database ID

### Step 1: Setup VPS

```bash
# SSH to your VPS
ssh root@178.156.170.161

# Navigate to project directory
cd /root/demestihas-ai

# Clone or update the repository
git pull origin main  # or upload files via SCP
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

Required configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ANTHROPIC_API_KEY=your_claude_api_key
NOTION_API_KEY=your_notion_integration_token
NOTION_TASKS_DATABASE_ID=your_notion_database_id
```

### Step 3: Deploy

```bash
# Run deployment script
./deploy.sh

# Or manually:
docker-compose build
docker-compose up -d
```

### Step 4: Verify

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f lyco

# Test the bot in Telegram
# Send "help" to @LycurgusBot
```

## 🔧 Maintenance

### View Logs
```bash
docker-compose logs -f lyco
```

### Restart Services
```bash
docker-compose restart lyco
```

### Update Code
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

## 📝 Notion Database Setup

Create a Notion database with these properties:

| Property | Type | Options |
|----------|------|---------|
| Title | Title | - |
| Status | Select | new, in_progress, complete, cancelled |
| Urgency | Number | 1-5 |
| Importance | Number | 1-5 |
| Quadrant | Select | Q1, Q2, Q3, Q4 |
| Assigned To | Select | Mene, Cindy, Both |
| Due Date | Date | - |
| Description | Text | - |
| Tags | Multi-select | work, personal, family, medical |

## 🐛 Troubleshooting

### Bot not responding
1. Check logs: `docker-compose logs lyco`
2. Verify token: Ensure TELEGRAM_BOT_TOKEN is correct
3. Check network: Ensure VPS can reach Telegram servers

### Tasks not saving
1. Verify Notion credentials in `.env`
2. Check Notion database permissions
3. Ensure database has required properties

### Redis connection issues
1. Check Redis container: `docker-compose ps redis`
2. Restart Redis: `docker-compose restart redis`

### High API costs
- The system uses Claude Haiku (cheapest model)
- Monitor usage in Anthropic dashboard
- Consider caching frequent queries

## 💡 Usage Tips

### For ADHD Management
- **Quick capture**: Just type tasks as they come to mind
- **Visual organization**: Matrix view shows priorities at a glance
- **Daily routine**: Check "today" view each morning
- **Weekly planning**: Review matrix on Sundays

### Natural Language Examples
- "Pick up prescription tomorrow" → Urgent + Important
- "Plan summer vacation" → Important + Not Urgent
- "Reply to school email" → Urgent + Not Important
- "Watch TV show" → Not Urgent + Not Important

### Family Coordination
- Tasks can be assigned to Mene, Cindy, or Both
- Weekly review shows everyone's tasks
- Shared visibility helps coordination

## 📊 Cost Estimation

- **Claude Haiku API**: ~$0.25 per 1M input tokens
- **Expected usage**: 100-200 tasks/month
- **Estimated cost**: < $5/month for family use
- **Notion API**: Free tier sufficient
- **VPS**: Existing infrastructure

## 🔒 Security Notes

- Never commit `.env` file to git
- Rotate API keys periodically
- Use environment variables for all secrets
- Run containers as non-root user
- Keep Docker images updated

## 📈 Future Enhancements

Planned improvements:
- [ ] Voice message support
- [ ] Task completion from Telegram
- [ ] Recurring tasks
- [ ] Task templates
- [ ] Daily/weekly summaries
- [ ] Integration with calendar

## 🆘 Support

For issues or questions:
1. Check logs first: `docker-compose logs`
2. Review this documentation
3. Contact system administrator

## 📄 License

Private family project - not for distribution

---

**Built with simplicity in mind for Mene & Cindy's family task management**