import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load env vars
dotenv.config({ path: path.join(__dirname, '../../.env') }); // services/.env
dotenv.config({ path: path.join(__dirname, '../../../.env') }); // Demestihas-AI/.env
dotenv.config({ path: path.join(__dirname, '../../../../.env') }); // Backup
dotenv.config({ path: path.join(__dirname, '../../../../claude-desktop-rag/.env') });

const app = express();
const PORT = process.env.PORT || 3005;
const AUTH_TOKEN = 'foXuVEE3kQbZt7Epg8mGhfM86KwY8';

// Supabase Setup
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('❌ Missing SUPABASE_URL or SUPABASE_KEY/ANON_KEY');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

// Middleware
app.use(express.json());
app.use(cors());
app.use(morgan('dev'));

// Auth Middleware
const authenticate = (req: express.Request, res: express.Response, next: express.NextFunction) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ') || authHeader.split(' ')[1] !== AUTH_TOKEN) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    next();
};

app.use(authenticate);

// --- Helpers ---

const logChange = async (taskId: string, type: string, prev: any, curr: any, reason: string, agent: string = 'API') => {
    await supabase.from('vantage_changelog').insert({
        task_id: taskId,
        change_type: type,
        previous_value: prev,
        new_value: curr,
        reason: reason,
        agent_id: agent
    });
};

// --- Routes ---

// 1. GET /vantage/dashboard
app.get('/vantage/dashboard', async (req, res) => {
    try {
        const { data: tasks, error } = await supabase
            .from('vantage_tasks')
            .select('*')
            .eq('status', 'active')
            .order('created_at', { ascending: false });

        if (error) throw error;

        const dashboard = {
            do_now: tasks.filter(t => t.quadrant === 'do_now'),
            schedule: tasks.filter(t => t.quadrant === 'schedule'),
            delegate: tasks.filter(t => t.quadrant === 'delegate'),
            defer: tasks.filter(t => t.quadrant === 'defer'),
            inbox: tasks.filter(t => t.quadrant === 'inbox' || !t.quadrant)
        };

        res.json(dashboard);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// 2. POST /vantage/tasks
app.post('/vantage/tasks', async (req, res) => {
    try {
        const { title, quadrant, context, deadline, owner = 'Mene' } = req.body;

        if (!title || !quadrant || !context) {
            return res.status(400).json({ error: 'Missing required fields: title, quadrant, context' });
        }

        const { data, error } = await supabase
            .from('vantage_tasks')
            .insert({
                title,
                quadrant,
                context,
                deadline,
                owner,
                status: 'active'
            })
            .select()
            .single();

        if (error) throw error;

        // Log creation
        await logChange(data.id, 'creation', null, data, "Task Created via API");

        res.status(201).json(data);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// 3. PATCH /vantage/tasks/:id
app.patch('/vantage/tasks/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { reason, ...updates } = req.body;

        if (!reason) {
            return res.status(400).json({ error: 'Reason is MANDATORY for updates' });
        }

        // Get current state
        const { data: current, error: fetchError } = await supabase
            .from('vantage_tasks')
            .select('*')
            .eq('id', id)
            .single();

        if (fetchError) return res.status(404).json({ error: 'Task not found' });

        // Update
        const { data: updated, error: updateError } = await supabase
            .from('vantage_tasks')
            .update({ ...updates, updated_at: new Date() })
            .eq('id', id)
            .select()
            .single();

        if (updateError) throw updateError;

        await logChange(id, 'update', current, updated, reason);

        res.json(updated);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// 4. GET /vantage/tasks/:id/history
app.get('/vantage/tasks/:id/history', async (req, res) => {
    try {
        const { id } = req.params;
        const { data, error } = await supabase
            .from('vantage_changelog')
            .select('*')
            .eq('task_id', id)
            .order('changed_at', { ascending: false });

        if (error) throw error;
        res.json(data);
    } catch (err: any) {
        res.status(500).json({ error: err.message });
    }
});

// 5. POST /vantage/sync
app.post('/vantage/sync', async (req, res) => {
    try {
        console.log('🔄 Starting Sync from Google Tasks Proxy...');

        // Fetch from Google Tasks Proxy
        const proxyRes = await fetch('https://claude.beltlineconsulting.co/tasks', {
            headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` }
        });

        if (!proxyRes.ok) {
            throw new Error(`Proxy fetch failed: ${proxyRes.status} ${proxyRes.statusText}`);
        }

        const rawBody = await proxyRes.text();
        console.log('📥 Raw Proxy Response:', rawBody.substring(0, 500) + '...'); // Log first 500 chars

        let gTasks: any[] = [];
        try {
            const parsed = JSON.parse(rawBody);
            if (Array.isArray(parsed)) {
                gTasks = parsed;
            } else if (parsed.tasks && Array.isArray(parsed.tasks)) {
                gTasks = parsed.tasks;
            } else if (parsed.data && Array.isArray(parsed.data)) {
                gTasks = parsed.data;
            } else {
                // If it's an error object, log it specially
                if (parsed.error) {
                    throw new Error(`Proxy Error: ${parsed.error}`);
                }
                throw new Error(`Unexpected response format: ${typeof parsed}`);
            }
        } catch (e: any) {
            throw new Error(`Failed to parse proxy response: ${e.message} | Raw: ${rawBody.substring(0, 50)}...`);
        }

        console.log(`📥 Parsed ${gTasks.length} tasks from Google.`);

        const results = {
            processed: 0,
            created: 0,
            updated: 0,
            errors: 0
        };

        for (const task of gTasks) {
            results.processed++;

            // Logic for auto-classification
            let quadrant = 'inbox';
            let context = 'Synced from Google Tasks';
            let scheduleMeta: any = {};
            const notes = (task.notes || '').toUpperCase();
            const title = task.title;
            const now = new Date();
            const due = task.due ? new Date(task.due) : null;

            // 1. HIGH COGNITIVE LOAD -> Schedule 9-11am
            if (notes.includes('HIGH COGNITIVE LOAD')) {
                quadrant = 'schedule';
                context = 'High Cognitive Load - Recommended for 9-11am Peak Window';
            }
            // 2. WAITING ON -> Inbox (Blocked)
            else if (notes.includes('WAITING ON') || title.toUpperCase().startsWith('WAITING ON')) {
                quadrant = 'inbox'; // Keeps it visible but distinct
                context = `Blocked/Waiting: ${notes}`;
            }
            // 3. Overdue -> Do Now
            else if (due && due < now) {
                quadrant = 'do_now';
                context = `Overdue task (Due: ${task.due})`;
            }

            // Sync Payload
            const payload = {
                title: task.title,
                source_ref: task.id, // Requires migration!
                quadrant: quadrant,
                context: context,
                deadline: task.due,
                updated_at: new Date()
            };

            // Check if exists
            const { data: existing } = await supabase
                .from('vantage_tasks')
                .select('*')
                .eq('source_ref', task.id)
                .single();

            if (existing) {
                // Update only if changed (simple check)
                // Actually, for sync, maybe we just update metadata or leave quadrant alone if explicitly set?
                // PRD implies "upsert", implying we overwrite.
                // But we don't want to overwrite a user-set quadrant.
                // Strategy: Only update if context/title changed, or if it's new.
                // Let's just update title/deadline basically.

                const { error: upError } = await supabase
                    .from('vantage_tasks')
                    .update({
                        title: payload.title,
                        deadline: payload.deadline,
                        updated_at: new Date()
                    })
                    .eq('id', existing.id);

                if (!upError) results.updated++;
            } else {
                // Create
                const { error: insError } = await supabase
                    .from('vantage_tasks')
                    .insert({
                        ...payload,
                        owner: 'Mene',
                        status: 'active'
                    });

                if (insError) {
                    console.error(`Failed to insert ${task.title}:`, insError);
                    results.errors++;
                } else {
                    results.created++;
                }
            }
        }

        res.json({ message: 'Sync complete', results });

    } catch (err: any) {
        console.error('Sync Error:', err);
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`🦅 Vantage API running on port ${PORT}`);
});
