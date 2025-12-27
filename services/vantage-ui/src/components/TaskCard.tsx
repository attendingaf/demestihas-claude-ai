import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { QUADRANT_COLORS } from '../types';
import type { Task } from '../types';

interface Props {
    task: Task;
    onComplete?: (task: Task) => void;
    onDelete?: (task: Task) => void;
}

export const TaskCard: React.FC<Props> = ({ task, onComplete, onDelete }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: task.id, data: { type: 'Task', task } });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    const quadrantColor = QUADRANT_COLORS[task.quadrant];

    if (isDragging) {
        return (
            <div
                ref={setNodeRef}
                className="task-card"
                style={{
                    ...style,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    borderColor: '#00FFFF',
                    boxShadow: '0 0 20px #00FFFF',
                    height: '80px',
                    opacity: 0.8
                }}
            />
        );
    }

    return (
        <div
            ref={setNodeRef}
            style={style}
            className="task-card"
            {...attributes}
            {...listeners}
        >
            <div
                className="task-card-strip"
                style={{ '--strip-color': quadrantColor } as React.CSSProperties}
            />

            <div className="task-card-content">
                {/* Scrollable Content Area */}
                <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '5px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <h3 className="task-title">{task.title}</h3>
                    </div>

                    {task.context && (
                        <p className="task-context" style={{ whiteSpace: 'normal', overflow: 'visible' }}>
                            {task.context}
                        </p>
                    )}

                    {task.deadline && (
                        <div style={{ marginTop: '8px', fontSize: '10px', color: '#cc5500', fontWeight: 'bold', textTransform: 'uppercase' }}>
                            Due: {new Date(task.deadline).toLocaleDateString()}
                        </div>
                    )}
                </div>

                {/* Action Buttons (Fixed at bottom) */}
                <div style={{ marginTop: '10px', display: 'flex', gap: '10px', justifyContent: 'flex-end', flexShrink: 0 }}>
                    {onComplete && (
                        <button
                            onPointerDown={(e) => e.stopPropagation()} // Prevent drag start
                            onClick={(e) => { e.stopPropagation(); onComplete(task); }}
                            style={{
                                background: '#333',
                                color: '#fff',
                                border: '1px solid #555',
                                borderRadius: '4px',
                                padding: '2px 8px',
                                fontSize: '10px',
                                cursor: 'pointer',
                                textTransform: 'uppercase',
                                fontFamily: 'Oswald'
                            }}>
                            COMPLETE
                        </button>
                    )}
                    {onDelete && (
                        <button
                            onPointerDown={(e) => e.stopPropagation()}
                            onClick={(e) => { e.stopPropagation(); onDelete(task); }}
                            style={{
                                background: 'transparent',
                                color: '#666',
                                border: '1px solid #333',
                                borderRadius: '4px',
                                padding: '2px 8px',
                                fontSize: '10px',
                                cursor: 'pointer',
                                textTransform: 'uppercase',
                                fontFamily: 'Oswald'
                            }}>
                            DELETE
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};
