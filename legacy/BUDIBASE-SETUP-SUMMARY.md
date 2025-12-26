# Budibase Setup - Quick Start Summary
## DispoAssist V0 Data Capture App

---

## ✅ PRE-SETUP VERIFICATION COMPLETE

**Database Status:** Ready for Budibase connection
- ✅ 5 tables available and accessible
- ✅ RLS enabled on all tables
- ✅ Connection tested successfully
- ✅ Test data present (1 call with child records)

---

## 🎯 YOUR TASKS

### 1. Create Budibase Account & App
**Go to:** https://budibase.com

1. Sign up or login
2. Click "Create New App" → "Start from scratch"
3. Name: `DispoAssist Data Capture`

---

### 2. Connect to Supabase Database

**Navigate to:** Data tab → + Add Data Source → PostgreSQL

**Copy these exact values:**

| Field | Value |
|-------|-------|
| Host | `db.wklxknnhgbnyragemqoy.supabase.co` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres` |
| Password | `DispoAssist2025!SecureDB` |
| SSL | ✅ **REQUIRED** (must enable) |

**After entering:**
1. Click "Test Connection" → should show success
2. Click "Save"
3. Click "Fetch Tables" → should show 5 tables:
   - appointments
   - barriers
   - calls
   - medications
   - tasks

**📸 TAKE SCREENSHOT 1:** Data panel showing all 5 tables

---

### 3. Build Home Screen

**Navigate to:** Design tab → Create Screen → Blank

**Screen Settings:**
- Name: `Home`
- Route: `/`
- Default Screen: ✅ Yes

**Add 3 Components:**

**Component 1 - Heading:**
- Type: Heading
- Text: `DispoAssist V0 Data Capture`

**Component 2 - Button:**
- Type: Button
- Text: `Start New Call`
- On Click: Navigate To → `/new-call`

**Component 3 - Button:**
- Type: Button  
- Text: `View Call History`
- On Click: Navigate To → `/call-history`

---

### 4. Preview & Validate

1. Click "Preview" button (top-right)
2. Verify home screen loads with heading and 2 buttons
3. Click both buttons (will show "page not found" - this is normal)

**📸 TAKE SCREENSHOT 2:** Preview showing home screen with heading and buttons

---

## 📋 DELIVERABLES

### Required Screenshots:

1. **Data Panel:** Showing all 5 connected tables in Budibase
2. **Home Screen Preview:** Showing heading and both navigation buttons

---

## 💡 QUICK TIPS

- **SSL is mandatory** - Supabase won't connect without it
- Use port **5432** (direct), not 6543 (pooler)
- Password is case-sensitive: `DispoAssist2025!SecureDB`
- Routes must start with `/` (e.g., `/new-call`)
- "Page not found" errors are expected for now

---

## 🆘 TROUBLESHOOTING

**Connection fails?**
```bash
# Run this test from command line:
bash /root/budibase-connection-test.sh
```

**Tables not showing?**
- Click "Fetch Tables" or "Refresh Tables" button
- Ensure SSL is enabled
- Save and reconnect to data source

**Buttons not working?**
- Verify On Click action = "Navigate To"
- Check routes have leading `/`
- Save changes before previewing

---

## 📚 DETAILED GUIDES AVAILABLE

- `/root/BUDIBASE-SETUP-GUIDE.md` - Full step-by-step instructions
- `/root/BUDIBASE-CHECKLIST.md` - Detailed checklist
- `/root/dispoassist-v0-credentials.txt` - All credentials
- `/root/budibase-connection-test.sh` - Connection test script

---

## ⏱️ TIME ESTIMATE: ~35 minutes

Good luck! The database is ready and waiting for your Budibase app. 🚀
