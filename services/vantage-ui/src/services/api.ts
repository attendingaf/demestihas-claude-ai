import type { Task, TasksByQuadrant } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3005';
const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || 'MISSING_AUTH_TOKEN';

const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`
};

export const vantageApi = {
    getDashboard: async (): Promise<TasksByQuadrant> => {
        const res = await fetch(`${API_URL}/vantage/dashboard`, { headers });
        if (!res.ok) throw new Error('Failed to fetch dashboard');
        return res.json();
    },

    updateTask: async (id: number, updates: Partial<Task>, reason: string): Promise<Task> => {
        const res = await fetch(`${API_URL}/vantage/tasks/${id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({ ...updates, reason })
        });
        if (!res.ok) throw new Error('Failed to update task');
        return res.json();
    },

    createTask: async (task: Partial<Task>): Promise<Task> => {
        const res = await fetch(`${API_URL}/vantage/tasks`, {
            method: 'POST',
            headers,
            body: JSON.stringify(task)
        });
        if (!res.ok) throw new Error('Failed to create task');
        return res.json();
    }
};
