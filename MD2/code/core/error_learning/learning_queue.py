"""
学习队列 - 失败样本进入专项训练队列
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
import threading
import queue


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    ERROR_ANALYSIS = "error_analysis"
    PATTERN_LEARNING = "pattern_learning"
    SKILL_IMPROVEMENT = "skill_improvement"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    MODEL_FINE_TUNING = "model_fine_tuning"
    FEEDBACK_INTEGRATION = "feedback_integration"


T = TypeVar('T')


@dataclass
class LearningTask(Generic[T]):
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    
    source: str
    description: str
    
    input_data: T
    expected_output: Optional[Any] = None
    
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    status: TaskStatus = TaskStatus.PENDING
    
    retry_count: int = 0
    max_retries: int = 3
    
    result: Optional[Any] = None
    error: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "source": self.source,
            "description": self.description,
            "context": self.context,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class QueueStats:
    total_tasks: int = 0
    pending_tasks: int = 0
    processing_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    avg_processing_time_ms: float = 0.0
    
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "pending_tasks": self.pending_tasks,
            "processing_tasks": self.processing_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "by_type": self.by_type,
            "by_priority": self.by_priority,
        }


class LearningQueue:
    
    def __init__(self, max_size: int = 10000, num_workers: int = 4):
        self.max_size = max_size
        self.num_workers = num_workers
        
        self._tasks: Dict[str, LearningTask] = {}
        self._pending_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_size)
        self._type_index: Dict[TaskType, List[str]] = {}
        self._source_index: Dict[str, List[str]] = {}
        
        self._handlers: Dict[TaskType, Callable] = {}
        self._workers: List[threading.Thread] = []
        self._running = False
        
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        
        self._processing_times: List[float] = []
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        self._handlers[task_type] = handler
    
    def submit(
        self,
        task_type: TaskType,
        source: str,
        description: str,
        input_data: Any,
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> LearningTask:
        import uuid
        
        task = LearningTask(
            task_id=f"learn-{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            priority=priority,
            source=source,
            description=description,
            input_data=input_data,
            context=context or {},
            tags=tags or [],
        )
        
        with self._lock:
            self._tasks[task.task_id] = task
            
            if task_type not in self._type_index:
                self._type_index[task_type] = []
            self._type_index[task_type].append(task.task_id)
            
            if source not in self._source_index:
                self._source_index[source] = []
            self._source_index[source].append(task.task_id)
        
        self._pending_queue.put((priority.value, task.created_at.timestamp(), task.task_id))
        task.status = TaskStatus.QUEUED
        
        self._notify_listeners("submitted", task)
        return task
    
    def submit_from_error(
        self,
        error_instance: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> LearningTask:
        return self.submit(
            task_type=TaskType.ERROR_ANALYSIS,
            source="error_registry",
            description=f"Learn from error: {getattr(error_instance, 'error_message', 'Unknown')[:100]}",
            input_data=error_instance,
            priority=TaskPriority.HIGH,
            context=context,
            tags=["error", "failure", "learning"],
        )
    
    def get_task(self, task_id: str) -> Optional[LearningTask]:
        return self._tasks.get(task_id)
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[LearningTask]:
        task_ids = self._type_index.get(task_type, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]
    
    def get_tasks_by_source(self, source: str) -> List[LearningTask]:
        task_ids = self._source_index.get(source, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]
    
    def get_pending_count(self) -> int:
        return self._pending_queue.qsize()
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"learning-worker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
    
    def stop(self):
        self._running = False
        
        for _ in range(self.num_workers):
            self._pending_queue.put((99, 0, None))
        
        for worker in self._workers:
            worker.join(timeout=5)
        
        self._workers.clear()
    
    def _worker_loop(self):
        while self._running:
            try:
                _, _, task_id = self._pending_queue.get(timeout=1)
                
                if task_id is None:
                    break
                
                self._process_task(task_id)
                
            except queue.Empty:
                continue
            except Exception:
                continue
    
    def _process_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                return
            
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
        
        self._notify_listeners("started", task)
        
        start_time = datetime.now()
        
        try:
            handler = self._handlers.get(task.task_type)
            
            if handler:
                result = handler(task.input_data, task.context)
            else:
                result = self._default_handler(task)
            
            with self._lock:
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
            
            processing_time = (task.completed_at - start_time).total_seconds() * 1000
            self._processing_times.append(processing_time)
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-500:]
            
            self._notify_listeners("completed", task)
            
        except Exception as e:
            with self._lock:
                task.error = str(e)
                task.retry_count += 1
                
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.QUEUED
                    self._pending_queue.put((
                        task.priority.value,
                        task.created_at.timestamp(),
                        task.task_id
                    ))
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
            
            self._notify_listeners("failed", task)
    
    def _default_handler(self, task: LearningTask) -> Any:
        return {"processed": True, "task_type": task.task_type.value}
    
    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            return True
    
    def get_stats(self) -> QueueStats:
        with self._lock:
            tasks = list(self._tasks.values())
            
            by_type: Dict[str, int] = {}
            by_priority: Dict[str, int] = {}
            
            for task in tasks:
                type_key = task.task_type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1
                
                priority_key = task.priority.name
                by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
            
            avg_time = (
                sum(self._processing_times) / len(self._processing_times)
                if self._processing_times else 0
            )
            
            return QueueStats(
                total_tasks=len(tasks),
                pending_tasks=sum(1 for t in tasks if t.status in [TaskStatus.PENDING, TaskStatus.QUEUED]),
                processing_tasks=sum(1 for t in tasks if t.status == TaskStatus.PROCESSING),
                completed_tasks=sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                failed_tasks=sum(1 for t in tasks if t.status == TaskStatus.FAILED),
                avg_processing_time_ms=avg_time,
                by_type=by_type,
                by_priority=by_priority,
            )
    
    def cleanup_completed(self, max_age_hours: int = 24) -> int:
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                and task.completed_at and task.completed_at < cutoff
            ]
            
            for tid in to_remove:
                task = self._tasks[tid]
                
                if task.task_type in self._type_index:
                    if tid in self._type_index[task.task_type]:
                        self._type_index[task.task_type].remove(tid)
                
                if task.source in self._source_index:
                    if tid in self._source_index[task.source]:
                        self._source_index[task.source].remove(tid)
                
                del self._tasks[tid]
            
            return len(to_remove)
    
    def add_listener(self, callback: Callable):
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: str, task: LearningTask):
        for callback in self._listeners:
            try:
                callback(event, task)
            except Exception:
                pass
