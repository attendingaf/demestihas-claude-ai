"""
Lyco 2.0 Database Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TaskSignal(BaseModel):
    """Raw signal from reality sources"""
    id: UUID = Field(default_factory=uuid4)
    source: str
    raw_content: str
    processed: bool = False
    processor_version: str = "2.0.0"
    confidence_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None  # Will be set based on email context


class Task(BaseModel):
    """Processed actionable task"""
    id: UUID = Field(default_factory=uuid4)
    signal_id: Optional[UUID] = None
    content: str
    next_action: str
    energy_level: str = "any"
    time_estimate: int = 15
    context_required: List[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    skipped_at: Optional[datetime] = None
    skipped_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedTask(BaseModel):
    """LLM processing result"""
    is_task: bool
    content: Optional[str] = None
    next_action: Optional[str] = None
    energy_level: Optional[str] = None
    time_estimate: Optional[int] = 15
    context_required: Optional[List[str]] = None
    confidence: Optional[float] = 0.0
