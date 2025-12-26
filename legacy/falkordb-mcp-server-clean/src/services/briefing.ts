import Anthropic from '@anthropic-ai/sdk';
import { listAllTasks, getBlockedTasks } from './googleTasks.js';
import { getTodayEvents } from './googleCalendar.js';

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
    const quickWins = tasks.filter((t: any) =>
        t.notes?.includes('15 min') || t.notes?.includes('Quick')
    );

    // Identify high cognitive load tasks
    const highCognitive = tasks.filter((t: any) =>
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
${events.length > 0 ? events.map((e: any) => `- ${e.start?.dateTime || e.start?.date}: ${e.summary}`).join('\n') : 'No events scheduled'}

## All Incomplete Tasks (${tasks.length} total)
${Object.entries(byList).map(([list, items]) =>
        `### ${list} (${items.length})\n${items.map((t: any) => `- ${t.title}${t.notes ? ` (${t.notes})` : ''}`).join('\n')}`
    ).join('\n\n')}

## Blocked Items (${blocked.length})
${blocked.map((b: any) => `- ${b.title} — waiting on ${b.waitingOn}${b.waitingContext ? ` (${b.waitingContext})` : ''}`).join('\n') || 'None'}

## Quick Wins Available
${quickWins.map((t: any) => `- ${t.title} (${t.listName})`).join('\n') || 'None identified'}

## High Cognitive Load Tasks (for 9-11am)
${highCognitive.map((t: any) => `- ${t.title} (${t.listName})`).join('\n') || 'None identified'}

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
        model: process.env.ANTHROPIC_MODEL || 'claude-3-haiku-20240307',
        max_tokens: 1024,
        messages: [{ role: 'user', content: prompt }]
    });

    const firstBlock = response.content[0];
    const synthesis = (firstBlock && firstBlock.type === 'text')
        ? firstBlock.text
        : '';

    // Extract recommended action from synthesis (first actionable item)
    const recommendedMatch = synthesis.match(/recommended.*?:?\s*[–-]\s*(.+?)(?:\n|$)/i);
    const recommendedNextAction = recommendedMatch?.[1] ||
        (quickWins[0]?.title ? `${quickWins[0].title} (${quickWins[0].listName})` : 'Review your task list');

    return {
        generatedAt: now.toISOString(),
        calendar: {
            events: events.map((e: any) => ({
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
