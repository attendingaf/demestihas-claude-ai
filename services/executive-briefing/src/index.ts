import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import { generateBriefing } from './services/briefing.js';
import { sendEmail } from './services/gmail.js';

const app = express();
const PORT = process.env.PORT || 8060;

app.use(cors());
app.use(express.json());

// Auth middleware
const authMiddleware = (req: any, res: any, next: any) => {
    // Skip auth for health checks
    if (req.path === '/health') return next();

    const token = req.headers.authorization?.replace('Bearer ', '');
    // Allow if TASK_API_KEY is set and matches
    if (process.env.TASK_API_KEY && token !== process.env.TASK_API_KEY) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    next();
};

app.use(authMiddleware);

app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'executive-briefing' });
});

// GET /briefing - Generate on-demand briefing
app.get('/briefing', async (req, res) => {
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
app.post('/briefing/email', async (req, res) => {
    try {
        console.log('Generating briefing for email...');
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

        const recipient = process.env.BRIEFING_RECIPIENT || 'menelaosdemestihas@gmail.com';
        await sendEmail(recipient, subject, htmlBody);

        console.log(`Email sent to ${recipient}`);

        res.json({
            sent: true,
            sentAt: new Date().toISOString(),
            recipient,
            subject
        });
    } catch (err: any) {
        console.error('Email error:', err);
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`Executive Briefing Service running on port ${PORT}`);
});
