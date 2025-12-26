#!/bin/bash
LOG=/var/log/briefing-cron.log
# Updated to hit the isolated Executive Briefing Service locally
API_URL="http://localhost:8060"
# Using the TASK_API_KEY from .env
AUTH="Bearer foXuVEE3kQbZt7Epg8mGhfM86KwY8"

echo "[$(date)] Starting briefing..." >> $LOG

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/briefing/email" -H "Authorization: $AUTH")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "[$(date)] SUCCESS: $BODY" >> $LOG
    curl -fsS -m 10 --retry 5 https://hc-ping.com/6058ead7-d341-4f0e-82d1-afbd0b6d0bf7 >> $LOG 2>&1
else
    echo "[$(date)] FAILED: HTTP $HTTP_CODE - $BODY" >> $LOG
    # Send failure alert? (Note: The alert endpoint might not exist in the new service yet, removing the failover call to avoid double error)
fi
