# Budibase Setup Guide - DispoAssist V0
## Step-by-Step Instructions

---

## STEP 1: Create Budibase Account & New App

### Actions:
1. **Navigate to:** https://budibase.com
2. **Create account or login** with your credentials
3. **Click:** "Create New App" → "Start from scratch"
4. **App Name:** `DispoAssist Data Capture`
5. **Click:** Create App

### ✅ Checkpoint:
- [ ] Budibase account created/logged in
- [ ] New app created named "DispoAssist Data Capture"
- [ ] You're now in the app builder interface

---

## STEP 2: Connect to Supabase Database

### Actions:
1. **Click:** "Data" tab in the left sidebar
2. **Click:** "+ Add Data Source" (or similar button)
3. **Select:** "PostgreSQL" from the data source options

### Connection Configuration:
**Copy and paste these exact values:**

| Field | Value |
|-------|-------|
| **Name/Alias** | `DispoAssist Supabase` |
| **Host** | `db.wklxknnhgbnyragemqoy.supabase.co` |
| **Port** | `5432` |
| **Database** | `postgres` |
| **User** | `postgres` |
| **Password** | `DispoAssist2025!SecureDB` |
| **SSL Mode** | ✅ Required (check the box/enable) |

### Important Notes:
- ⚠️ Make sure SSL is **ENABLED** - Supabase requires SSL connections
- ⚠️ Use port **5432** (direct connection), NOT 6543 (pooler)
- ⚠️ The password is case-sensitive

### Actions After Configuration:
4. **Click:** "Test Connection" button
   - **Expected Result:** ✅ "Connection successful" or similar message
   - **If it fails:** Double-check password, SSL setting, and host
5. **Click:** "Save" or "Save Data Source"
6. **Click:** "Fetch Tables" (or it may auto-fetch)

### ✅ Checkpoint:
- [ ] Connection test successful
- [ ] 5 tables detected and visible:
  - appointments
  - barriers
  - calls
  - medications
  - tasks
- [ ] Data source saved

**📸 SCREENSHOT 1 NEEDED:** Data panel showing all 5 tables

---

## STEP 3: Build Home Screen

### Create New Screen:
1. **Click:** "Design" tab in the left sidebar
2. **Click:** "Create screen" or "+ Add Screen"
3. **Select:** "Blank" screen template
4. **Screen Name:** `Home`
5. **Route:** `/` (forward slash only)
6. **Set as default screen:** ✅ Check this option
7. **Click:** Create/Save

### Add Components to Home Screen:

#### Component 1: Heading
1. **Click:** "+ Add Component" or drag from component panel
2. **Select:** "Heading" component
3. **Configure:**
   - **Text:** `DispoAssist V0 Data Capture`
   - **Size:** H1 or H2 (your preference)
   - **Alignment:** Center (optional)

#### Component 2: Button (Start New Call)
1. **Click:** "+ Add Component"
2. **Select:** "Button" component
3. **Configure:**
   - **Text:** `Start New Call`
   - **Variant/Style:** Primary (optional, for emphasis)
4. **Click Actions/On Click:**
   - **Action Type:** Navigate To
   - **URL/Route:** `/new-call`

#### Component 3: Button (View Call History)
1. **Click:** "+ Add Component"
2. **Select:** "Button" component
3. **Configure:**
   - **Text:** `View Call History`
   - **Variant/Style:** Secondary or Default
4. **Click Actions/On Click:**
   - **Action Type:** Navigate To
   - **URL/Route:** `/call-history`

### Optional Styling:
- Adjust spacing between components
- Center align buttons (use container if needed)
- Add background color or styling

### ✅ Checkpoint:
- [ ] Home screen created at route `/`
- [ ] Set as default screen
- [ ] Heading displays "DispoAssist V0 Data Capture"
- [ ] "Start New Call" button configured with navigation to `/new-call`
- [ ] "View Call History" button configured with navigation to `/call-history`

---

## STEP 4: Preview & Validate

### Actions:
1. **Click:** "Preview" button (usually top-right corner)
2. **Verify in preview:**
   - [ ] Home screen loads automatically
   - [ ] Heading displays correctly
   - [ ] Both buttons are visible
3. **Click:** "Start New Call" button
   - **Expected:** "Page not found" or 404 error (normal - page doesn't exist yet)
4. **Click:** Back button, then "View Call History" button
   - **Expected:** "Page not found" or 404 error (normal - page doesn't exist yet)

### ✅ Checkpoint:
- [ ] Preview loads successfully
- [ ] Home screen displays as expected
- [ ] Buttons trigger navigation (even if to non-existent pages)
- [ ] No console errors or connection issues

**📸 SCREENSHOT 2 NEEDED:** Preview of home screen showing heading and both buttons

---

## REQUIRED DELIVERABLES

### Screenshot 1: Data Panel
**What to capture:**
- Budibase Data tab open
- All 5 tables visible in the data source panel:
  - appointments
  - barriers  
  - calls
  - medications
  - tasks

### Screenshot 2: Home Screen Preview
**What to capture:**
- App preview mode active
- Home screen displaying:
  - "DispoAssist V0 Data Capture" heading
  - "Start New Call" button
  - "View Call History" button

---

## TROUBLESHOOTING

### Connection Test Fails
**Error:** "Connection refused" or "Cannot connect"
- ✅ Verify SSL is enabled
- ✅ Check host: `db.wklxknnhgbnyragemqoy.supabase.co`
- ✅ Check port: `5432` (not 6543)
- ✅ Try testing connection from command line first:
  ```bash
  PGPASSWORD="DispoAssist2025!SecureDB" psql \
    "postgresql://postgres@db.wklxknnhgbnyragemqoy.supabase.co:5432/postgres?sslmode=require" \
    -c "SELECT COUNT(*) FROM calls;"
  ```

**Error:** "Authentication failed"
- ✅ Double-check password: `DispoAssist2025!SecureDB` (case-sensitive)
- ✅ Ensure username is `postgres` (lowercase)

### Tables Not Showing
- ✅ Click "Fetch Tables" or "Refresh" button
- ✅ Check that connection is saved
- ✅ Verify you're looking at the correct data source
- ✅ Try reconnecting to the database

### Buttons Not Navigating
- ✅ Ensure "On Click" action is set to "Navigate To"
- ✅ Verify routes start with `/` (e.g., `/new-call`, not `new-call`)
- ✅ "Page not found" is EXPECTED for now (pages don't exist yet)

### Preview Not Loading
- ✅ Save all changes before clicking Preview
- ✅ Check browser console for errors
- ✅ Try refreshing the preview

---

## NEXT STEPS (After This Task)

Once this setup is complete, you'll be ready to:
1. Build the "New Call" form screen
2. Build the "Call History" table view
3. Add child table forms (barriers, tasks, medications, appointments)
4. Implement form validation and data entry workflows

---

## QUICK REFERENCE: Connection Details

**For Copy-Paste:**
```
Host: db.wklxknnhgbnyragemqoy.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: DispoAssist2025!SecureDB
SSL: Required ✅
```

---

*Setup Guide Created: 2025-11-15*  
*Database: DispoAssist-V0 on Supabase*
