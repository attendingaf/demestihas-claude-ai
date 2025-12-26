import { Router } from 'express';
import * as GoogleTasks from '../services/googleTasks.js'; // Note the .js extension for ESM import if needed, but usually tsx handles it. 
// However, in this project (Step 9 import), we see: import { initializeDb } from "./db/connection.js";
// So I should probably use .js extensions for local imports.
// The directive used: import * as GoogleTasks from '../services/googleTasks'; 
// I will try without .js first as per directive, but if it fails I'll add it.
// Actually, looking at index.ts again: import { saveMemoryTool } from "./tools/save-memory.js";
// It uses .js! I MUST use .js in the import path for ESM compatibility in this project.

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
