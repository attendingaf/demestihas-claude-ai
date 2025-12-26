# Task System - Phase 2 Dev Directive

**PM**: Claude (Desktop)  
**Implementer**: Senior Dev Agent (CLI)  
**Status**: Phase 1 Complete, Phase 2 Ready

---

## Phase 1 Recap (Complete)

- ✓ Google Tasks CRUD working
- ✓ All 5 project lists accessible
- ✓ Deployed to VPS (pm2)
- ✓ External access verified
- ✓ Skill updated

---

## Phase 2: Briefing & Email (Days 4-6)

### Objective
Add calendar integration, Claude-synthesized briefings, and 5am email delivery.

### Step 2.1: Google Calendar Client

**Create file: `src/services/googleCalendar.ts`**

```typescript
import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
  refresh_token: process.env.GOOGLE_REFRESH_TOKEN
});

const calendar = google.calendar({ version: 'v3', auth: oauth2Client });

export async function getTodayEvents() {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  
  const res = await calendar.events.list({
    calendarId: 'primary',
    timeMin: startOfDay.toISOString(),
    timeMax: endOfDay.toISOString(),
    singleEvents: true,
    orderBy: 'startTime'
  });
  
  return res.data.items || [];
}

export async function getEventsInRange(timeMin: string, timeMax: string) {
  const res = await calendar.events.list({
    calendarId: 'primary',
    timeMin,
    timeMax,
    singleEvents: true,
    orderBy: 'startTime'
  });
  
  return res.data.items || [];
}
```

### Step 2.2: Gmail Client

**Create file: `src/services/gmail.ts`**

```typescript
import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
  refresh_token: process.env.GOOGLE_REFRESH_TOKEN
});

const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

export async function sendEmail(to: string, subject: string, body: string) {
  const message = [
    `To: ${to}`,
    `Subject: ${subject}`,
    'Content-Type: text/html; charset=utf-8',
    '',
    body
  ].join('\n');
  
  const encodedMessage = Buffer.from(message)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  
  const res = await gmail.users.messages.send({
    userId: 'me',
    requestBody: {
      raw: encodedMessage
    }
  });
  
  return res.data;
}
```

### Step 2.3: Briefing Service

**Create file: `src/services/briefing.ts`**

```typescript
import Anthropic from '@anthropic-ai/sdk';
import { listAllTasks, getBlockedTasks } from './googleTasks';
import { getTodayEvents } from './googleCalendar';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY
});

interface BriefingData {
  generatedAt: string;
  calendar: {
    events: any[];
    count: number;
  };
  tasks: {
    all: any[];
    blocked: any[];
    byList: Record<string, any[]>;
  };
  synthesis: string;
  recommendedNextAction: string;
}

export async function generateBriefing(): Promise<BriefingData> {
  const [tasks, blocked, events] = await Promise.all([
    listAllTasks(),
    getBlockedTasks(),
    getTodayEvents()
  ]);
  
  // Group tasks by list
  const byList: Record<string, any[]> = {};
  for (const task of tasks) {
    const listName = task.listName || 'Unknown';
    if (!byList[listName]) byList[listName] = [];
    byList[listName].push(task);
  }
  
  // Identify quick wins (15 min or less in notes)
  const quickWins = tasks.filter(t => 
    t.notes?.includes('15 min') || t.notes?.includes('Quick')
  );
  
  // Identify high cognitive load tasks
  const highCognitive = tasks.filter(t => 
    t.notes?.includes('HIGH COGNITIVE LOAD')
  );
  
  const now = new Date();
  const dayOfWeek = now.toLocaleDateString('en-US', { weekday: 'long' });
  const currentTime = now.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    timeZone: 'America/New_York'
  });
  
  const prompt = `You are generating a morning briefing for Mene, a physician executive with ADHD-hyperactive.

## User Context
- Timezone: America/New_York
- Current time: ${currentTime}
- Day of week: ${dayOfWeek}
- Peak energy window: 9-11am

## Today's Calendar
${events.length > 0 ? events.map(e => `- ${e.start?.dateTime || e.start?.date}: ${e.summary}`).join('\n') : 'No events scheduled'}

## All Incomplete Tasks (${tasks.length} total)
${Object.entries(byList).map(([list, items]) => 
  `### ${list} (${items.length})\n${items.map(t => `- ${t.title}${t.notes ? ` (${t.notes})` : ''}`).join('\n')}`
).join('\n\n')}

## Blocked Items (${blocked.length})
${blocked.map(b => `- ${b.title} — waiting on ${b.waitingOn}${b.waitingContext ? ` (${b.waitingContext})` : ''}`).join('\n') || 'None'}

## Quick Wins Available
${quickWins.map(t => `- ${t.title} (${t.listName})`).join('\n') || 'None identified'}

## High Cognitive Load Tasks (for 9-11am)
${highCognitive.map(t => `- ${t.title} (${t.listName})`).join('\n') || 'None identified'}

## Instructions
Generate a briefing that:
1. Leads with today's calendar commitments and any conflicts
2. Identifies the ONE recommended next action based on current time and energy
3. Highlights quick wins for momentum building
4. Flags tasks marked HIGH COGNITIVE LOAD for the 9-11am window
5. Lists blocked items with how long they've been waiting
6. Keeps total length scannable in 30 seconds
7. Uses n-dashes with spaces for lists, never bullets
8. Ends with an encouraging but not saccharine closing

Do not use headers like "Good morning!" — just dive into the content.`;

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }]
  });
  
  const synthesis = response.content[0].type === 'text' 
    ? response.content[0].text 
    : '';
  
  // Extract recommended action from synthesis (first actionable item)
  const recommendedMatch = synthesis.match(/recommended.*?:?\s*[–-]\s*(.+?)(?:\n|$)/i);
  const recommendedNextAction = recommendedMatch?.[1] || 
    (quickWins[0]?.title ? `${quickWins[0].title} (${quickWins[0].listName})` : 'Review your task list');
  
  return {
    generatedAt: now.toISOString(),
    calendar: {
      events: events.map(e => ({
        title: e.summary,
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date
      })),
      count: events.length
    },
    tasks: {
      all: tasks,
      blocked,
      byList
    },
    synthesis,
    recommendedNextAction
  };
}
```

### Step 2.4: Briefing Routes

**Create file: `src/routes/briefing.ts`**

```typescript
import { Router } from 'express';
import { generateBriefing } from '../services/briefing';
import { sendEmail } from '../services/gmail';

const router = Router();

// Auth middleware
const authMiddleware = (req: any, res: any, next: any) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (token !== process.env.TASK_API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

router.use(authMiddleware);

// GET /briefing - Generate on-demand briefing
router.get('/', async (req, res) => {
  try {
    const briefing = await generateBriefing();
    
    if (req.query.format === 'markdown') {
      res.type('text/markdown').send(briefing.synthesis);
    } else {
      res.json(briefing);
    }
  } catch (err: any) {
    console.error('Briefing error:', err);
    res.status(500).json({ error: err.message });
  }
});

// POST /briefing/email - Send briefing email
router.post('/email', async (req, res) => {
  try {
    const briefing = await generateBriefing();
    
    const dayOfWeek = new Date().toLocaleDateString('en-US', { weekday: 'long' });
    const taskCount = briefing.tasks.all.length;
    const eventCount = briefing.calendar.count;
    
    const subject = `${dayOfWeek} Briefing — ${taskCount} tasks, ${eventCount} events`;
    
    // Convert synthesis to HTML
    const htmlBody = `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
        ${briefing.synthesis.split('\n').map(line => `<p>${line}</p>`).join('')}
        <hr style="margin-top: 24px; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
          Generated at ${new Date().toLocaleTimeString('en-US', { timeZone: 'America/New_York' })} ET
        </p>
      </div>
    `;
    
    await sendEmail('menelaos4@gmail.com', subject, htmlBody);
    
    res.json({
      sent: true,
      sentAt: new Date().toISOString(),
      recipient: 'menelaos4@gmail.com',
      subject
    });
  } catch (err: any) {
    console.error('Email error:', err);
    res.status(500).json({ error: err.message });
  }
});

export default router;
```

### Step 2.5: Register Routes

**In `src/index-sse.ts`**, add:

```typescript
import briefingRoutes from './routes/briefing';

// ... existing setup ...

app.use('/briefing', briefingRoutes);
```

### Step 2.6: Environment Variables

**Add to .env:**
```
ANTHROPIC_API_KEY=<from 1Password or Anthropic dashboard>
```

### Step 2.7: Install Dependencies

```bash
npm install @anthropic-ai/sdk
```

### Step 2.8: Verification Tests

```bash
# Test briefing generation
curl -s https://claude.beltlineconsulting.co/briefing \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# Test email sending
curl -s -X POST https://claude.beltlineconsulting.co/briefing/email \
  -H "Authorization: Bearer $TASK_API_KEY" | jq .

# Check inbox for email
```

---

## Phase 2 Completion Criteria

- [ ] GET /briefing returns JSON with synthesis
- [ ] GET /briefing?format=markdown returns raw markdown
- [ ] POST /briefing/email sends email to menelaos4@gmail.com
- [ ] Calendar events included in briefing
- [ ] Blocked tasks identified correctly
- [ ] Claude synthesis is coherent and follows format

---

## Phase 3 Preview (Days 7-9)

- Cron job for 5am daily briefing
- Health endpoint
- Error alerting via backup SMTP
- Retry logic for API failures

---

## Notes

1. Reuse the same OAuth2 client pattern from googleTasks.ts
2. Claude API key is separate from Google OAuth
3. Test email sending carefully — check spam folder
4. Briefing synthesis should be <30 second read

---

**Phase 2 Go**: Start with Step 2.1 (Calendar client). Report back when briefing generation works.
