# Task System - Dev Directive

**PM**: Claude (Desktop)  
**Implementer**: Senior Dev Agent (CLI)  
**VPS**: claude.beltlineconsulting.co  
**Pattern**: Extend existing Express monolith (src/index-sse.ts)

---

## Current State

- VPS already running Express with FalkorDB endpoints
- Auth pattern: `Authorization: Bearer <token>`
- Existing endpoints: `/graph/query`, `/graph/nodes`
- Google OAuth infrastructure: **NOT YET SET UP**

## Target State (V1)

- Task CRUD via Google Tasks API
- Morning briefing email at 5am ET
- On-demand briefing via API
- Same auth pattern as existing endpoints

---

## Phase 1: Foundation (Days 1-3)

### Objective
Get task CRUD working. No briefing, no email, no Claude synthesis yet. Just raw Google Tasks API wrapper.

### Step 1.1: Google OAuth Setup

**Create OAuth credentials in Google Cloud Console:**
1. Enable APIs: Google Tasks, Google Calendar, Gmail
2. Create OAuth 2.0 credentials (Desktop app type)
3. Run initial auth flow to get refresh token
4. Store refresh token securely

**Environment variables to add (.env):**
```bash
# Task System
TASK_API_KEY=<generate new secure token>
GOOGLE_CLIENT_ID=<from console>
GOOGLE_CLIENT_SECRET=<from console>
GOOGLE_REFRESH_TOKEN=<from initial auth flow>
```

**Deliverable**: Refresh token stored, APIs enabled

### Step 1.2: Google Tasks Client

**Create file: `src/services/googleTasks.ts`**

```typescript
import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
  refresh_token: process.env.GOOGLE_REFRESH_TOKEN
});

export const tasksClient = google.tasks({ version: 'v1', auth: oauth2Client });

// List all task lists (needed to map names to IDs)
export async function listTaskLists() {
  const res = await tasksClient.tasklists.list();
  return res.data.items || [];
}

// List incomplete tasks in a specific list
export async function listTasks(tasklistId: string) {
  const res = await tasksClient.tasks.list({
    tasklist: tasklistId,
    showCompleted: false,
    showHidden: false
  });
  return res.data.items || [];
}

// List all incomplete tasks across all lists
export async function listAllTasks() {
  const lists = await listTaskLists();
  const allTasks = [];
  
  for (const list of lists) {
    const tasks = await listTasks(list.id!);
    allTasks.push(...tasks.map(t => ({
      ...t,
      listId: list.id,
      listName: list.title
    })));
  }
  
  return allTasks;
}

// Create task
export async function createTask(tasklistId: string, task: {
  title: string;
  notes?: string;
  due?: string; // RFC 3339
}) {
  const res = await tasksClient.tasks.insert({
    tasklist: tasklistId,
    requestBody: task
  });
  return res.data;
}

// Update task
export async function updateTask(tasklistId: string, taskId: string, updates: {
  title?: string;
  notes?: string;
  due?: string;
}) {
  const res = await tasksClient.tasks.patch({
    tasklist: tasklistId,
    task: taskId,
    requestBody: updates
  });
  return res.data;
}

// Delete task
export async function deleteTask(tasklistId: string, taskId: string) {
  await tasksClient.tasks.delete({
    tasklist: tasklistId,
    task: taskId
  });
  return { deleted: true };
}

// Complete task
export async function completeTask(tasklistId: string, taskId: string) {
  const res = await tasksClient.tasks.patch({
    tasklist: tasklistId,
    task: taskId,
    requestBody: { status: 'completed' }
  });
  return res.data;
}

// Get blocked tasks (parse WAITING ON from notes)
export async function getBlockedTasks() {
  const allTasks = await listAllTasks();
  const waitingOnRegex = /WAITING ON:\s*([^(]+)\s*(?:\(([^)]+)\))?/i;
  
  return allTasks
    .filter(t => t.notes && waitingOnRegex.test(t.notes))
    .map(t => {
      const match = t.notes!.match(waitingOnRegex);
      return {
        ...t,
        waitingOn: match?.[1]?.trim(),
        waitingContext: match?.[2]?.trim()
      };
    });
}
```

**Test command after creation:**
```bash
# Run from VPS project directory
npx ts-node -e "
const { listTaskLists } = require('./src/services/googleTasks');
listTaskLists().then(console.log).catch(console.error);
"
```

**Deliverable**: googleTasks.ts compiles, listTaskLists() returns your task lists

### Step 1.3: Task Routes

**Create file: `src/routes/tasks.ts`**

```typescript
import { Router } from 'express';
import * as GoogleTasks from '../services/googleTasks';

const router = Router();

// Auth middleware (same pattern as graph routes)
const authMiddleware = (req: any, res: any, next: any) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (token !== process.env.TASK_API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

router.use(authMiddleware);

// GET /tasks - List all incomplete tasks
router.get('/', async (req, res) => {
  try {
    const tasks = await GoogleTasks.listAllTasks();
    res.json({ tasks, count: tasks.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// GET /tasks/lists - List all task lists (useful for mapping)
router.get('/lists', async (req, res) => {
  try {
    const lists = await GoogleTasks.listTaskLists();
    res.json({ lists });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// GET /tasks/:listId - List tasks in a specific list
router.get('/:listId', async (req, res) => {
  try {
    const tasks = await GoogleTasks.listTasks(req.params.listId);
    res.json({ tasks, count: tasks.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// POST /tasks - Create task
router.post('/', async (req, res) => {
  try {
    const { listId, title, notes, due } = req.body;
    if (!listId || !title) {
      return res.status(400).json({ error: 'listId and title required' });
    }
    const task = await GoogleTasks.createTask(listId, { title, notes, due });
    res.json({ id: task.id, listId, title: task.title, created: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// PATCH /tasks/:taskId - Update task
router.patch('/:taskId', async (req, res) => {
  try {
    const { listId, title, notes, due } = req.body;
    if (!listId) {
      return res.status(400).json({ error: 'listId required' });
    }
    const task = await GoogleTasks.updateTask(listId, req.params.taskId, { title, notes, due });
    res.json({ id: task.id, updated: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /tasks/:taskId - Delete task
router.delete('/:taskId', async (req, res) => {
  try {
    const { listId } = req.body;
    if (!listId) {
      return res.status(400).json({ error: 'listId required' });
    }
    await GoogleTasks.deleteTask(listId, req.params.taskId);
    res.json({ deleted: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// POST /tasks/:taskId/complete - Mark complete
router.post('/:taskId/complete', async (req, res) => {
  try {
    const { listId } = req.body;
    if (!listId) {
      return res.status(400).json({ error: 'listId required' });
    }
    const task = await GoogleTasks.completeTask(listId, req.params.taskId);
    res.json({ 
      id: task.id, 
      title: task.title, 
      completed: true, 
      completedAt: task.completed 
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// GET /tasks/blocked - Get blocked tasks
router.get('/blocked', async (req, res) => {
  try {
    const blocked = await GoogleTasks.getBlockedTasks();
    res.json({ blocked, count: blocked.length });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
```

### Step 1.4: Register Routes

**In `src/index-sse.ts` (or main entry)**, add:

```typescript
import taskRoutes from './routes/tasks';

// ... existing setup ...

app.use('/tasks', taskRoutes);
```

### Step 1.5: Verification Tests

**Run these curl commands after deployment:**

```bash
export TASK_API_KEY="your-task-api-key"
export BASE_URL="https://claude.beltlineconsulting.co"

# 1. List all task lists (get IDs for next steps)
curl -s -X GET "$BASE_URL/tasks/lists" \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# 2. List all tasks
curl -s -X GET "$BASE_URL/tasks" \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# 3. Create a test task (use a listId from step 1)
curl -s -X POST "$BASE_URL/tasks" \
  -H "Authorization: Bearer $TASK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"listId": "YOUR_LIST_ID", "title": "Test task from API", "notes": "15 min task"}' | jq .

# 4. List tasks in specific list
curl -s -X GET "$BASE_URL/tasks/YOUR_LIST_ID" \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# 5. Update the test task
curl -s -X PATCH "$BASE_URL/tasks/YOUR_TASK_ID" \
  -H "Authorization: Bearer $TASK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"listId": "YOUR_LIST_ID", "notes": "Updated notes - WAITING ON: John (context)"}' | jq .

# 6. Get blocked tasks
curl -s -X GET "$BASE_URL/tasks/blocked" \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# 7. Complete the test task
curl -s -X POST "$BASE_URL/tasks/YOUR_TASK_ID/complete" \
  -H "Authorization: Bearer $TASK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"listId": "YOUR_LIST_ID"}' | jq .
```

---

## Phase 1 Completion Criteria

All of the following must work before moving to Phase 2:

- [ ] GET /tasks/lists returns your Google Tasks lists
- [ ] GET /tasks returns all incomplete tasks
- [ ] POST /tasks creates a new task
- [ ] PATCH /tasks/:taskId updates task
- [ ] POST /tasks/:taskId/complete marks task done
- [ ] GET /tasks/blocked returns tasks with "WAITING ON" in notes
- [ ] DELETE /tasks/:taskId removes task

---

## Phase 2 Preview (Days 4-6)

After Phase 1 is verified, we'll add:
- Google Calendar client for event context
- GET /briefing endpoint (JSON response)
- Claude API integration for synthesis
- Gmail API for sending briefing email
- POST /briefing/email manual trigger

---

## Notes for Dev Agent

1. **Don't modify existing graph routes** - this is additive only
2. **Use same auth pattern** - Bearer token, 401 on failure
3. **Error handling**: Return 500 with error message, don't crash server
4. **TypeScript**: Match existing project patterns
5. **Test each step before proceeding** - if OAuth fails, stop and debug

## Questions to Resolve

1. Where is the current VPS project directory? Need to confirm file structure.
2. Is `googleapis` package already installed, or needs npm install?
3. What's the process for adding env vars on the VPS?

---

**Phase 1 Go**: Start with Step 1.1 (Google OAuth setup). Report back with task list IDs once you have the refresh token working.
