import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN || null
});

export const tasksClient = google.tasks({ version: 'v1', auth: oauth2Client });

// List all task lists (needed to mapping names to IDs)
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
        if (list.id) {
            const tasks = await listTasks(list.id);
            allTasks.push(...tasks.map(t => ({
                ...t,
                listId: list.id,
                listName: list.title
            })));
        }
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
        .filter((t: any) => t.notes && waitingOnRegex.test(t.notes))
        .map((t: any) => {
            const match = t.notes!.match(waitingOnRegex);
            return {
                ...t,
                waitingOn: match?.[1]?.trim(),
                waitingContext: match?.[2]?.trim()
            };
        });
}
