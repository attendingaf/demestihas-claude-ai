# HANDOFF #025: Gmail App-Specific Password Configuration

**FROM**: PM-Opus
**TO**: User/Developer  
**DATE**: 2025-08-26T14:00:00Z
**PRIORITY**: IMMEDIATE (15-minute task)
**ATOMIC SCOPE**: Configure Gmail app-specific password for hermesaudio444@gmail.com

## CONTEXT
- Hermes container: ✅ Running stable (ID: e05d6640d542)
- Authentication: ❌ Regular password failing IMAP access
- Family impact: Email interface blocked, forcing CLI usage

## IMPLEMENTATION STEPS

### Step 1: Generate App-Specific Password (User Action)
1. Go to https://myaccount.google.com/security
2. Sign in to hermesaudio444@gmail.com
3. Enable 2-Step Verification (if not already enabled)
4. Navigate to "2-Step Verification" → "App passwords"
5. Generate new app password:
   - Select app: "Mail"
   - Select device: "Other" → Name it "Hermes VPS"
6. Copy the 16-character password (format: xxxx xxxx xxxx xxxx)

### Step 2: Update VPS Configuration
```bash
# SSH to VPS
ssh root@178.156.170.161

# Update password in .env
cd /root/lyco-ai
nano .env

# Find and update this line:
HERMES_EMAIL_PASSWORD=<paste-16-char-app-password-no-spaces>

# Save and exit (Ctrl+X, Y, Enter)
```

### Step 3: Restart Container
```bash
# Restart Hermes container with new credentials
docker-compose restart hermes_audio

# Verify authentication success (wait 30 seconds)
docker logs hermes_audio --tail 20
```

## SUCCESS TEST
```bash
# Look for these success indicators in logs:
# ✅ "Successfully connected to hermesaudio444@gmail.com"
# ✅ "📭 Hermes: No new audio emails found" (without auth errors)
# ❌ No "AUTHENTICATIONFAILED" errors
```

## VALIDATION TEST
1. Send test email with audio attachment to hermesaudio444@gmail.com
2. Within 60 seconds, check logs for processing activity:
   ```bash
   docker logs hermes_audio --tail 50 -f
   ```
3. Verify task creation in Notion database

## ROLLBACK PLAN
If authentication still fails:
1. Verify app password copied correctly (no spaces)
2. Check 2-Step Verification is enabled on account
3. Try regenerating app password
4. Document exact error for troubleshooting

## FAMILY COMMUNICATION
Once verified working, send family message:
```
🎉 Email audio processing is now live!

How to use:
1. Record voice memo on your phone
2. Email to: hermesaudio444@gmail.com
3. Tasks automatically appear in Notion within 2 minutes

That's it! No apps, no folders, just email and go.
```

## REPORTING
Update thread_log.md with:
- Timestamp of successful authentication
- First test email processing time
- Any issues encountered

---

**Time Estimate**: 15 minutes
**Risk Level**: Low (configuration change only)
**Family Value**: HIGH (unlocks intuitive interface)