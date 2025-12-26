# DispoAssist V0 - Budibase Setup Checklist
## Quick Reference for Setup Process

---

## 📋 PRE-FLIGHT CHECK

✅ **Database Connection Verified**
- 5 tables available: appointments, barriers, calls, medications, tasks
- RLS enabled on all tables
- Current test data: 1 call, 1 task, 1 medication, 1 appointment

---

## 🔧 STEP 1: BUDIBASE ACCOUNT (5 minutes)

**URL:** https://budibase.com

**Actions:**
- [ ] Navigate to budibase.com
- [ ] Create account or login
- [ ] Click "Create New App"
- [ ] Select "Start from scratch"
- [ ] Name: **DispoAssist Data Capture**
- [ ] Confirm app created

---

## 🔌 STEP 2: CONNECT DATABASE (10 minutes)

**Location:** Data Tab → + Add Data Source → PostgreSQL

### Connection Details (Copy-Paste Ready):

```
Name: DispoAssist Supabase
Host: db.wklxknnhgbnyragemqoy.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: DispoAssist2025!SecureDB
SSL: ✅ REQUIRED (must enable)
```

### Verification Steps:
- [ ] All fields entered correctly
- [ ] SSL/TLS enabled
- [ ] Click "Test Connection" → should show ✅ success
- [ ] Click "Save" or "Save Data Source"
- [ ] Click "Fetch Tables" (may auto-fetch)
- [ ] Verify 5 tables appear:
  - [ ] appointments
  - [ ] barriers
  - [ ] calls
  - [ ] medications
  - [ ] tasks

### 📸 SCREENSHOT 1: Data panel with 5 tables visible

---

## 🎨 STEP 3: BUILD HOME SCREEN (15 minutes)

**Location:** Design Tab → Create Screen → Blank

### Screen Configuration:
```
Name: Home
Route: /
Default Screen: ✅ Yes
```

### Component 1: Heading
```
Type: Heading
Text: DispoAssist V0 Data Capture
Size: H1 or H2
Alignment: Center (optional)
```

- [ ] Heading component added
- [ ] Text displays correctly

### Component 2: Button - Start New Call
```
Type: Button
Text: Start New Call
Style: Primary (optional)
On Click Action: Navigate To
Route: /new-call
```

- [ ] Button added
- [ ] Text set to "Start New Call"
- [ ] Navigation configured to /new-call

### Component 3: Button - View Call History
```
Type: Button
Text: View Call History
Style: Secondary/Default (optional)
On Click Action: Navigate To
Route: /call-history
```

- [ ] Button added
- [ ] Text set to "View Call History"
- [ ] Navigation configured to /call-history

### Layout Tips:
- Use a container to center buttons
- Add spacing between components
- Adjust button widths for consistency

---

## ✅ STEP 4: VALIDATE & PREVIEW (5 minutes)

**Location:** Preview Button (top-right)

### Preview Checks:
- [ ] Click "Preview" button
- [ ] Home screen loads automatically
- [ ] Heading displays: "DispoAssist V0 Data Capture"
- [ ] "Start New Call" button visible
- [ ] "View Call History" button visible
- [ ] Click "Start New Call" → expect "Page not found" (NORMAL)
- [ ] Go back, click "View Call History" → expect "Page not found" (NORMAL)

### 📸 SCREENSHOT 2: Home screen preview showing heading and both buttons

---

## 📦 DELIVERABLES CHECKLIST

### Required Screenshots:
- [ ] **Screenshot 1:** Budibase Data tab showing all 5 connected tables
- [ ] **Screenshot 2:** App preview of Home screen with heading and 2 buttons

### What to Include in Screenshots:

**Screenshot 1 should show:**
- Budibase interface with Data tab selected
- Data source named "DispoAssist Supabase" or similar
- All 5 tables listed:
  - appointments
  - barriers
  - calls
  - medications
  - tasks

**Screenshot 2 should show:**
- App in preview mode
- Home screen displaying
- "DispoAssist V0 Data Capture" heading
- "Start New Call" button
- "View Call History" button
- Clean, functional layout

---

## ⚠️ COMMON ISSUES & FIXES

### Issue: Connection Test Fails
**Solutions:**
- ✅ Verify SSL is enabled (critical for Supabase)
- ✅ Check host: `db.wklxknnhgbnyragemqoy.supabase.co`
- ✅ Check port: `5432` (NOT 6543)
- ✅ Verify password: `DispoAssist2025!SecureDB` (case-sensitive)
- ✅ Run pre-flight test: `bash /root/budibase-connection-test.sh`

### Issue: Tables Not Appearing
**Solutions:**
- ✅ Click "Fetch Tables" or "Refresh Tables" button
- ✅ Ensure data source is saved
- ✅ Check connection is active (green indicator)
- ✅ Try disconnecting and reconnecting

### Issue: Buttons Not Working in Preview
**Solutions:**
- ✅ Verify "On Click" action is set to "Navigate To"
- ✅ Check routes have leading slash: `/new-call` not `new-call`
- ✅ "Page not found" is EXPECTED - those pages don't exist yet
- ✅ Save all changes before previewing

### Issue: Home Screen Not Default
**Solutions:**
- ✅ Edit screen settings
- ✅ Ensure "Set as default" or "Home screen" is checked
- ✅ Verify route is exactly `/` (just forward slash)

---

## 🎯 SUCCESS CRITERIA

You're done when:
- ✅ Budibase account created
- ✅ App "DispoAssist Data Capture" created
- ✅ PostgreSQL data source connected to Supabase
- ✅ Connection test passes
- ✅ 5 tables fetched and visible
- ✅ Home screen created at route `/`
- ✅ Heading displays correctly
- ✅ Both navigation buttons configured and visible
- ✅ Preview works (buttons navigate, even if to 404)
- ✅ Screenshots captured

---

## 📚 REFERENCE FILES

All setup documentation available:
- `/root/BUDIBASE-SETUP-GUIDE.md` - Detailed step-by-step guide
- `/root/BUDIBASE-CHECKLIST.md` - This checklist
- `/root/budibase-connection-test.sh` - Pre-flight connection test
- `/root/dispoassist-v0-credentials.txt` - All credentials
- `/root/DispoAssist-V0-DELIVERABLE-REPORT.md` - Full database documentation

---

## ⏱️ ESTIMATED TIME

- Step 1 (Account): 5 minutes
- Step 2 (Database): 10 minutes
- Step 3 (Home Screen): 15 minutes
- Step 4 (Validate): 5 minutes

**Total: ~35 minutes**

---

## 🚀 NEXT PHASE (After This Task)

Once complete, you'll build:
1. New Call Form screen (`/new-call`)
2. Call History table view (`/call-history`)
3. Child data entry forms (barriers, tasks, meds, appointments)
4. Form validation and workflows

---

*Checklist Created: 2025-11-15*  
*Ready for Budibase Setup*
