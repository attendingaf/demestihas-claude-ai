import { Router } from 'express';
import { generateBriefing } from '../services/briefing.js';
import { sendEmail } from '../services/gmail.js';

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

        await sendEmail('menelaosdemestihas@gmail.com', subject, htmlBody);

        res.json({
            sent: true,
            sentAt: new Date().toISOString(),
            recipient: 'menelaosdemestihas@gmail.com',
            subject
        });
    } catch (err: any) {
        console.error('Email error:', err);
        res.status(500).json({ error: err.message });
    }
});

export default router;
