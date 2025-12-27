import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { QUADRANT_LABELS, QUADRANT_COLORS } from '../types';
import type { Task, QuadrantType } from '../types';
import { TaskCard } from './TaskCard';

interface Props {
    id: QuadrantType;
    tasks: Task[];
    onComplete?: (task: Task) => void;
    onDelete?: (task: Task) => void;
}

export const Quadrant: React.FC<Props> = ({ id, tasks, onComplete, onDelete }) => {
    const { setNodeRef } = useDroppable({
        id,
        data: { type: 'Quadrant', quadrant: id }
    });

    const label = QUADRANT_LABELS[id];
    const color = QUADRANT_COLORS[id];

    const LCARS_LABELS: Record<string, string> = {
        do_now: 'DO NOW',
        schedule: 'SCHEDULE',
        delegate: 'DELEGATE',
        defer: 'NOT TO DO',
    };

    return (
        <div className="quadrant-container">
            <div className="mb-4">
                <div
                    className="quadrant-header-pill"
                    style={{
                        '--q-color': color,
                        '--q-glow': `${color}60`
                    } as React.CSSProperties}
                >
                    {LCARS_LABELS[id] || label.toUpperCase()}
                </div>
            </div>

            <div
                ref={setNodeRef}
                className={`quadrant-bg ${['do_now', 'schedule', 'delegate'].includes(id) ? 'single-col' : ''}`}
            >
                <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
                    {/* Removed wrapping div to allow grid layout to work on direct children */}
                    {tasks.map(task => (
                        <TaskCard
                            key={task.id}
                            task={task}
                            onComplete={onComplete}
                            onDelete={onDelete}
                        />
                    ))}
                </SortableContext>
            </div>
        </div>
    );
};
