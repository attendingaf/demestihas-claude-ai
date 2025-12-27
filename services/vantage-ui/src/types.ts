export type QuadrantType = 'do_now' | 'schedule' | 'delegate' | 'defer';

export interface Task {
    id: number;
    title: string;
    quadrant: QuadrantType;
    status: 'pending' | 'completed' | 'archived';
    owner: string;
    context?: string;
    deadline?: string;
    created_at?: string;
}

export type TasksByQuadrant = Record<QuadrantType, Task[]>;

export const QUADRANT_LABELS: Record<QuadrantType, string> = {
    do_now: 'Do Now',
    schedule: 'Schedule',
    delegate: 'Delegate',
    defer: 'Delete / Defer',
};

export const QUADRANT_COLORS: Record<QuadrantType, string> = {
    do_now: '#E0E0E0',    // Lightest Grey
    schedule: '#B0B0B0',  // Light Grey
    delegate: '#808080',  // Medium Grey
    defer: '#505050',     // Dark Grey
};
