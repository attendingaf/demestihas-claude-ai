import { useEffect, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  defaultDropAnimationSideEffects,
} from '@dnd-kit/core';
import type {
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
  DropAnimation,
} from '@dnd-kit/core';
import { arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { vantageApi } from './services/api';
import type { Task, TasksByQuadrant, QuadrantType } from './types';
import { Quadrant } from './components/Quadrant';
import { TaskCard } from './components/TaskCard';
import { createPortal } from 'react-dom';
import { Plus } from 'lucide-react';

const dropAnimation: DropAnimation = {
  sideEffects: defaultDropAnimationSideEffects({
    styles: {
      active: { opacity: '0.5' },
    },
  }),
};

function App() {
  const [tasks, setTasks] = useState<TasksByQuadrant>({
    do_now: [],
    schedule: [],
    delegate: [],
    defer: []
  });
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await vantageApi.getDashboard();
      setTasks({
        do_now: data.do_now || [],
        schedule: data.schedule || [],
        delegate: data.delegate || [],
        defer: data.defer || []
      });
    } catch (err) {
      console.error(err);
    }
  };

  // ... (Keep drag handlers same)
  const findContainer = (id: number | QuadrantType): QuadrantType | undefined => {
    if ((id as QuadrantType) in tasks) {
      return id as QuadrantType;
    }
    return (Object.keys(tasks) as QuadrantType[]).find((key) =>
      tasks[key].find((t) => t.id === id)
    );
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = (active.data.current?.task as Task);
    setActiveTask(task);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    const overId = over?.id;

    if (!overId || active.id === overId) return;

    const activeContainer = findContainer(active.id as number);
    const overContainer = findContainer(overId as (number | QuadrantType));

    if (!activeContainer || !overContainer || activeContainer === overContainer) {
      return;
    }

    setTasks((prev) => {
      const activeItems = prev[activeContainer];
      const overItems = prev[overContainer];
      const activeIndex = activeItems.findIndex((t) => t.id === active.id);
      const overIndex = overItems.findIndex((t) => t.id === overId);

      let newIndex;
      if (overId in prev) {
        newIndex = overItems.length + 1;
      } else {
        const isBelowOverItem =
          over &&
          active.rect.current.translated &&
          active.rect.current.translated.top > over.rect.top + over.rect.height;

        const modifier = isBelowOverItem ? 1 : 0;
        newIndex = overIndex >= 0 ? overIndex + modifier : overItems.length + 1;
      }

      return {
        ...prev,
        [activeContainer]: [
          ...prev[activeContainer].filter((item) => item.id !== active.id),
        ],
        [overContainer]: [
          ...prev[overContainer].slice(0, newIndex),
          prev[activeContainer][activeIndex],
          ...prev[overContainer].slice(newIndex, prev[overContainer].length),
        ],
      };
    });
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    const activeId = active.id;
    const overId = over?.id;

    if (!overId) {
      setActiveTask(null);
      return;
    }

    const activeContainer = findContainer(activeId as number);
    const overContainer = findContainer(overId as (number | QuadrantType));

    if (activeContainer && overContainer) {
      const activeIndex = tasks[activeContainer].findIndex((t) => t.id === activeId);
      const overIndex = tasks[overContainer].findIndex((t) => t.id === overId);

      if (activeContainer !== overContainer) {
        const task = tasks[overContainer].find(t => t.id === activeId);
        if (task) {
          await vantageApi.updateTask(task.id, { quadrant: overContainer }, `Moved to ${overContainer}`);
          task.quadrant = overContainer;
        }
      } else if (activeIndex !== overIndex) {
        setTasks((prev) => ({
          ...prev,
          [activeContainer]: arrayMove(prev[activeContainer], activeIndex, overIndex),
        }));
      }
    }

    setActiveTask(null);
  };

  const handleCompleteTask = async (task: Task) => {
    // 1. Optimistic Update
    setTasks(prev => ({
      ...prev,
      [task.quadrant]: prev[task.quadrant].filter(t => t.id !== task.id)
    }));
    // 2. API Call
    try {
      await vantageApi.updateTask(task.id, { status: 'completed' }, 'Market completed via UI');
    } catch (err) {
      console.error("Failed to complete task", err);
      // Revert? (For prototype, assume success)
    }
  };

  const handleDeleteTask = async (task: Task) => {
    // 1. Optimistic Update
    setTasks(prev => ({
      ...prev,
      [task.quadrant]: prev[task.quadrant].filter(t => t.id !== task.id)
    }));
    // 2. API Call
    try {
      await vantageApi.updateTask(task.id, { status: 'archived' }, 'Deleted/Archived via UI');
    } catch (err) {
      console.error("Failed to delete task", err);
    }
  };
  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCreateTask = async (task: Partial<Task>) => {
    try {
      const created = await vantageApi.createTask(task);
      setTasks(prev => ({
        ...prev,
        [created.quadrant]: [created, ...prev[created.quadrant]]
      }));
      setIsModalOpen(false);
    } catch (err) {
      console.error("Failed to create task", err);
    }
  };
  // ... End Drag Handlers

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <div className="lcars-column-left">
        <div className="lcars-elbow-header">
          {/* Empty elbow header now, sidebar reduced */}
        </div>
        <div className="lcars-sidebar-bar"></div>
      </div>

      {/* Main Content */}
      <div className="lcars-main">
        {/* Top Bar */}
        <div className="lcars-top-bar">
          <span className="lcars-title-text">VANTAGE LCARS</span>

          {/* Controls */}
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              background: 'black',
              color: '#00BFFF',
              border: '2px solid #00BFFF',
              borderRadius: '20px',
              padding: '5px 15px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              fontFamily: 'Oswald',
              fontWeight: 'bold'
            }}>
            <Plus size={18} /> NEW TASK
          </button>
        </div>

        {/* New Task Modal */}
        {isModalOpen && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
          }}>
            <div style={{
              backgroundColor: '#111', border: '2px solid #FF9C00', borderRadius: '20px', padding: '30px', width: '500px',
              color: '#FF9C00', fontFamily: 'Oswald'
            }}>
              <h2 style={{ marginTop: 0, marginBottom: '20px', borderBottom: '1px solid #FF9C00' }}>INITIALIZE NEW TASK</h2>
              <form onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const newTask = {
                  title: formData.get('title') as string,
                  quadrant: formData.get('quadrant') as QuadrantType,
                  context: formData.get('context') as string,
                  deadline: formData.get('deadline') as string
                };
                handleCreateTask(newTask);
              }}>
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>TASK TITLE</label>
                  <input name="title" required style={{ width: '100%', padding: '10px', background: '#222', border: '1px solid #444', color: 'white' }} />
                </div>
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>QUADRANT</label>
                  <select name="quadrant" style={{ width: '100%', padding: '10px', background: '#222', border: '1px solid #444', color: 'white' }}>
                    <option value="do_now">DO NOW</option>
                    <option value="schedule">SCHEDULE</option>
                    <option value="delegate">DELEGATE</option>
                    <option value="defer">NOT TO DO</option>
                  </select>
                </div>
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>CONTEXT / NOTES</label>
                  <textarea name="context" rows={3} style={{ width: '100%', padding: '10px', background: '#222', border: '1px solid #444', color: 'white' }} />
                </div>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>DEADLINE (OPTIONAL)</label>
                  <input name="deadline" type="date" style={{ width: '100%', padding: '10px', background: '#222', border: '1px solid #444', color: 'white' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button type="button" onClick={() => setIsModalOpen(false)} style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #666', color: '#666', cursor: 'pointer' }}>CANCEL</button>
                  <button type="submit" style={{ padding: '10px 20px', background: '#FF9C00', border: 'none', color: 'black', fontWeight: 'bold', cursor: 'pointer' }}>ENGAGE</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Matrix */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="matrix-grid">
            <Quadrant id="do_now" tasks={tasks.do_now} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
            <Quadrant id="schedule" tasks={tasks.schedule} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
            <Quadrant id="delegate" tasks={tasks.delegate} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
            <Quadrant id="defer" tasks={tasks.defer} onComplete={handleCompleteTask} onDelete={handleDeleteTask} />
          </div>

          {createPortal(
            <DragOverlay dropAnimation={dropAnimation}>
              {activeTask ? <TaskCard task={activeTask} /> : null}
            </DragOverlay>,
            document.body
          )}
        </DndContext>
      </div>
    </div >
  );
}

export default App;
