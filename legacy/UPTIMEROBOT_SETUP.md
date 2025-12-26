# UptimeRobot Setup Guide

## What is UptimeRobot?

UptimeRobot is a free uptime monitoring service that checks if your website is online and alerts you when it goes down.

## Setup Instructions

### Step 1: Create Account

1. Go to <https://uptimerobot.com>
2. Click **"Sign Up Free"**
3. Use your email to create an account
4. Verify your email

### Step 2: Add Monitors

Once logged in, click **"Add New Monitor"**

#### Monitor 1: Website Uptime

- **Monitor Type**: HTTPS
- **Friendly Name**: `DemestiChat Website`
- **URL**: `https://demestichat.beltlineconsulting.co/`
- **Monitoring Interval**: 5 minutes
- Click **"Create Monitor"**

#### Monitor 2: API Health Check

- **Monitor Type**: HTTP(s)
- **Friendly Name**: `DemestiChat API Health`
- **URL**: `http://178.156.170.161:8000/health`
- **Monitoring Interval**: 5 minutes
- **Keyword**: `healthy` (optional - checks response contains this word)
- Click **"Create Monitor"**

### Step 3: Configure Alerts

Click on **"My Settings"** → **"Alert Contacts"**

#### Email Alerts (Default)

- Already configured with your signup email
- You'll receive emails when monitors go down/up

#### Discord Alerts (Optional)

1. In Discord, go to your server
2. Right-click the channel → **Edit Channel** → **Integrations** → **Webhooks**
3. Click **"New Webhook"**
4. Copy the **Webhook URL**
5. In UptimeRobot:
   - Click **"Add Alert Contact"**
   - Type: **Web-Hook**
   - Friendly Name: `Discord Alerts`
   - URL: Paste your Discord webhook URL
   - POST Value (JSON):

     ```json
     {
       "content": "🚨 **Alert**: *monitorFriendlyName* is *alertTypeFriendlyName* (*monitorURL*)"
     }
     ```

   - Click **"Create Alert Contact"**

6. Go back to your monitors and add this alert contact to each

#### Slack Alerts (Optional)

1. In Slack, go to <https://api.slack.com/apps>
2. Click **"Create New App"** → **"From scratch"**
3. Name it "UptimeRobot" and select your workspace
4. Click **"Incoming Webhooks"** → Enable it
5. Click **"Add New Webhook to Workspace"**
6. Select a channel and click **"Allow"**
7. Copy the **Webhook URL**
8. In UptimeRobot:
   - Click **"Add Alert Contact"**
   - Type: **Slack**
   - Webhook URL: Paste your Slack webhook URL
   - Click **"Create Alert Contact"**

### Step 4: Test Alerts

1. In UptimeRobot, click on one of your monitors
2. Click **"Send Test Alert"**
3. Verify you receive the alert via email/Discord/Slack

## What You'll Get

- ✅ **Instant Alerts** when your site goes down
- ✅ **Uptime Reports** (daily, weekly, monthly)
- ✅ **Response Time Tracking**
- ✅ **Status Page** (optional - public page showing uptime)

## Dashboard

Your UptimeRobot dashboard will show:

- Current status of all monitors (green = up, red = down)
- Uptime percentage (e.g., 99.9%)
- Response time graphs
- Recent downtime events

## Free Tier Limits

- 50 monitors
- 5-minute check intervals
- Unlimited alert contacts
- 2-month log retention

This is more than enough for DemestiChat!

## Next Steps

After setting up UptimeRobot:

1. You'll be notified immediately if the site goes down
2. You can view uptime history and trends
3. Optional: Create a public status page to share with users

### Estimated Setup Time

10 minutes
