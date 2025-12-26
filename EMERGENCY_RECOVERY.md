# 🚨 EMERGENCY: Bot Not Responding - Quick Recovery

**Status:** Bot deployment failed - immediate action required  
**Priority:** High (family dependency)

## Immediate Diagnosis (SSH Required)

```bash
ssh root@178.156.170.161
cd /root/demestihas-ai

# Check if bot process is running
ps aux | grep "python.*bot" | grep -v grep

# Check recent logs for errors
tail -20 bot.log
```

## Most Likely Causes & Fixes

### 1. Bot Process Died During Startup (Most Common)
**Symptoms:** No Python process found  
**Quick Fix:**
```bash
# Restore last working backup
cp bot.py.backup.[timestamp] bot.py
nohup python3 bot.py > bot.log 2>&1 &
```

### 2. Import Error in Health Check Code
**Symptoms:** "ModuleNotFoundError" or "ImportError" in logs  
**Quick Fix:**
```bash
# Check what's missing
python3 -c "import aiohttp" || echo "aiohttp missing"

# Install if needed
pip3 install aiohttp

# Or restore backup if complex
cp bot.py.backup.[timestamp] bot.py
nohup python3 bot.py > bot.log 2>&1 &
```

### 3. Port 8080 Already in Use
**Symptoms:** "Address already in use" in logs  
**Quick Fix:**
```bash
# Kill whatever is using port 8080
sudo lsof -ti:8080 | xargs kill -9

# Restart bot
nohup python3 bot.py > bot.log 2>&1 &
```

### 4. Environment Variables Missing
**Symptoms:** Telegram token or API key errors  
**Quick Fix:**
```bash
# Check .env file exists
cat .env | grep TELEGRAM_BOT_TOKEN

# If missing, restore or recreate
```

## Emergency Rollback (Guaranteed Working)

If all else fails, restore to last known working state:

```bash
cd /root/demestihas-ai

# Stop any running processes
pkill -f "python.*bot"

# Find most recent backup
ls -la bot.py.backup.*

# Restore most recent backup (replace timestamp)
cp bot.py.backup.20250901_XXXX bot.py

# Start bot
nohup python3 bot.py > bot.log 2>&1 &

# Verify it's running
sleep 5
ps aux | grep "python.*bot" | grep -v grep

# Test on Telegram
echo "Test @LycurgusBot now"
```

## Quick Test Commands

```bash
# After any fix, verify:
ps aux | grep bot                    # Process running?
tail -5 bot.log                      # Any errors?
curl http://localhost:8080/health    # Health endpoint (if applicable)
```

## Report Back

After running emergency recovery, please report:
1. **What error was in bot.log?**
2. **Which fix worked?**
3. **Is bot responding on Telegram now?**

## Prevention for Next Time

Before any deployment:
1. Always create timestamped backup
2. Test import statements manually first  
3. Check log file immediately after restart
4. Have rollback plan ready

---

**Priority:** Get bot working first, debug health check later. Family dependency takes precedence over feature additions.

