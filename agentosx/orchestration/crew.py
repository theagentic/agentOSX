"""
CrewAI-style Team Coordination

Role-based agent teams with manager pattern, task queue, and shared memory.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque


logger = logging.getLogger(__name__)


class CrewRole(Enum):
    """Agent roles in a crew."""
    MANAGER = "manager"      # Coordinates and delegates
    WORKER = "worker"        # Executes tasks
    REVIEWER = "reviewer"    # Reviews work
    SPECIALIST = "specialist"  # Domain expert


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    """Crew execution modes."""
    SEQUENTIAL = "sequential"  # Tasks run one after another
    PARALLEL = "parallel"      # Tasks run concurrently
    HIERARCHICAL = "hierarchical"  # Manager delegates to workers


@dataclass
class Task:
    """A task to be executed by a crew member."""
    task_id: str
    description: str
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def mark_started(self):
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def mark_completed(self, result: Any):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()


class TaskQueue:
    """Thread-safe task queue with priority support."""
    
    def __init__(self):
        """Initialize task queue."""
        self._queue: deque = deque()
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
    
    async def add_task(self, task: Task, priority: int = 0):
        """
        Add a task to the queue.
        
        Args:
            task: Task to add
            priority: Task priority (higher = more important)
        """
        async with self._lock:
            self._tasks[task.task_id] = task
            
            # Insert based on priority
            inserted = False
            for i, (p, t) in enumerate(self._queue):
                if priority > p:
                    self._queue.insert(i, (priority, task))
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append((priority, task))
            
            logger.debug(f"Added task to queue: {task.task_id} (priority: {priority})")
    
    async def get_next_task(self) -> Optional[Task]:
        """Get next available task (respecting dependencies)."""
        async with self._lock:
            for i, (priority, task) in enumerate(self._queue):
                # Check if dependencies are met
                if task.status == TaskStatus.PENDING:
                    deps_met = all(
                        self._tasks.get(dep_id, Task(dep_id, "")).status == TaskStatus.COMPLETED
                        for dep_id in task.dependencies
                    )
                    if deps_met:
                        self._queue.remove((priority, task))
                        task.status = TaskStatus.ASSIGNED
                        return task
        return None
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        return self._tasks.get(task_id)
    
    async def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return [task for task in self._tasks.values() if task.status == TaskStatus.PENDING]
    
    async def is_empty(self) -> bool:
        """Check if queue is empty."""
        async with self._lock:
            return len(self._queue) == 0


@dataclass
class CrewMember:
    """A member of a crew with specific role and capabilities."""
    agent_id: str
    agent: Any  # BaseAgent instance
    role: CrewRole
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    active_tasks: int = 0


class Crew:
    """
    Role-based agent team with manager pattern.
    
    Inspired by CrewAI's approach to multi-agent collaboration.
    """
    
    def __init__(self, name: str, manager_id: str = None):
        """
        Initialize a crew.
        
        Args:
            name: Crew name
            manager_id: Optional manager agent ID
        """
        self.name = name
        self.manager_id = manager_id
        self._members: Dict[str, CrewMember] = {}
        self._task_queue = TaskQueue()
        self._shared_memory: Dict[str, Any] = {}
        self._memory_lock = asyncio.Lock()
        self._execution_history: List[Dict[str, Any]] = []
    
    async def add_member(
        self,
        agent_id: str,
        agent: Any,
        role: CrewRole,
        capabilities: List[str] = None,
        max_concurrent_tasks: int = 1
    ):
        """
        Add a member to the crew.
        
        Args:
            agent_id: Agent identifier
            agent: Agent instance
            role: Agent role in crew
            capabilities: Agent capabilities
            max_concurrent_tasks: Maximum concurrent tasks
        """
        if role == CrewRole.MANAGER and self.manager_id and self.manager_id != agent_id:
            raise ValueError("Crew already has a manager")
        
        member = CrewMember(
            agent_id=agent_id,
            agent=agent,
            role=role,
            capabilities=capabilities or [],
            max_concurrent_tasks=max_concurrent_tasks
        )
        
        self._members[agent_id] = member
        
        if role == CrewRole.MANAGER:
            self.manager_id = agent_id
        
        logger.info(f"Added {role.value} to crew {self.name}: {agent_id}")
    
    async def add_task(
        self,
        description: str,
        task_id: str = None,
        dependencies: List[str] = None,
        metadata: Dict[str, Any] = None,
        priority: int = 0
    ) -> str:
        """
        Add a task to the crew's queue.
        
        Args:
            description: Task description
            task_id: Optional task ID (auto-generated if not provided)
            dependencies: Task IDs this depends on
            metadata: Task metadata
            priority: Task priority
            
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = f"task_{len(self._execution_history)}_{int(datetime.now().timestamp())}"
        
        task = Task(
            task_id=task_id,
            description=description,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        await self._task_queue.add_task(task, priority)
        logger.info(f"Added task to crew {self.name}: {task_id}")
        
        return task_id
    
    async def execute(self, mode: ExecutionMode = ExecutionMode.SEQUENTIAL) -> Dict[str, Any]:
        """
        Execute all tasks in the queue.
        
        Args:
            mode: Execution mode (sequential, parallel, hierarchical)
            
        Returns:
            Execution results
        """
        logger.info(f"Starting crew {self.name} execution (mode: {mode.value})")
        start_time = datetime.now()
        
        results = {
            "crew": self.name,
            "mode": mode.value,
            "tasks": [],
            "status": "success",
            "start_time": start_time.isoformat()
        }
        
        try:
            if mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential()
            elif mode == ExecutionMode.PARALLEL:
                await self._execute_parallel()
            elif mode == ExecutionMode.HIERARCHICAL:
                await self._execute_hierarchical()
            
            # Collect results
            all_tasks = await self._task_queue.get_pending_tasks()
            for task_id, task in self._task_queue._tasks.items():
                results["tasks"].append({
                    "task_id": task_id,
                    "description": task.description,
                    "status": task.status.value,
                    "result": task.result,
                    "error": task.error,
                    "assigned_to": task.assigned_to
                })
            
            # Check if any task failed
            if any(t.status == TaskStatus.FAILED for t in self._task_queue._tasks.values()):
                results["status"] = "partial_failure"
        
        except Exception as e:
            logger.error(f"Crew execution error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        end_time = datetime.now()
        results["end_time"] = end_time.isoformat()
        results["duration"] = (end_time - start_time).total_seconds()
        
        self._execution_history.append(results)
        return results
    
    async def _execute_sequential(self):
        """Execute tasks sequentially."""
        while not await self._task_queue.is_empty():
            task = await self._task_queue.get_next_task()
            if task:
                await self._execute_task(task)
            else:
                # No task available (dependencies not met)
                await asyncio.sleep(0.1)
    
    async def _execute_parallel(self):
        """Execute tasks in parallel where possible."""
        workers = []
        
        while not await self._task_queue.is_empty() or workers:
            # Start new tasks
            while len(workers) < len(self._members):
                task = await self._task_queue.get_next_task()
                if task:
                    workers.append(asyncio.create_task(self._execute_task(task)))
                else:
                    break
            
            if workers:
                # Wait for at least one to complete
                done, pending = await asyncio.wait(workers, return_when=asyncio.FIRST_COMPLETED)
                workers = list(pending)
    
    async def _execute_hierarchical(self):
        """Execute with manager delegating to workers."""
        if not self.manager_id:
            logger.warning("No manager assigned, falling back to sequential")
            await self._execute_sequential()
            return
        
        manager = self._members.get(self.manager_id)
        if not manager:
            raise ValueError(f"Manager not found: {self.manager_id}")
        
        # Manager assigns tasks to workers
        while not await self._task_queue.is_empty():
            task = await self._task_queue.get_next_task()
            if task:
                # Find best worker for task
                worker = await self._find_best_worker(task)
                if worker:
                    task.assigned_to = worker.agent_id
                    await self._execute_task(task, worker)
                else:
                    logger.warning(f"No available worker for task: {task.task_id}")
                    await asyncio.sleep(0.5)
    
    async def _execute_task(self, task: Task, member: CrewMember = None):
        """Execute a single task."""
        if member is None:
            # Find available member
            member = await self._find_best_worker(task)
            if not member:
                task.mark_failed("No available agent")
                return
        
        task.mark_started()
        task.assigned_to = member.agent_id
        member.active_tasks += 1
        
        logger.info(f"Executing task {task.task_id} with {member.agent_id}")
        
        try:
            # Execute with agent
            from agentosx.agents.base import ExecutionContext
            context = ExecutionContext(
                input=task.description,
                session_id=task.task_id,
                metadata={
                    "crew": self.name,
                    "task": task.task_id,
                    "shared_memory": await self.get_shared_memory()
                }
            )
            
            result = await member.agent.process(task.description, context)
            task.mark_completed(result)
            
            # Update shared memory with result
            await self.set_shared_memory(f"task_{task.task_id}_result", result)
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.mark_failed(str(e))
        
        finally:
            member.active_tasks -= 1
    
    async def _find_best_worker(self, task: Task) -> Optional[CrewMember]:
        """Find best available worker for a task."""
        # Prioritize specialists, then workers
        candidates = [
            m for m in self._members.values()
            if m.role in [CrewRole.SPECIALIST, CrewRole.WORKER]
            and m.active_tasks < m.max_concurrent_tasks
        ]
        
        if not candidates:
            return None
        
        # Simple selection: first available
        # Could be enhanced with capability matching
        return candidates[0]
    
    async def get_shared_memory(self, key: str = None) -> Any:
        """
        Get value from shared memory.
        
        Args:
            key: Memory key, or None to get all memory
            
        Returns:
            Memory value or all memory dict
        """
        async with self._memory_lock:
            if key:
                return self._shared_memory.get(key)
            return self._shared_memory.copy()
    
    async def set_shared_memory(self, key: str, value: Any):
        """
        Set value in shared memory.
        
        Args:
            key: Memory key
            value: Value to store
        """
        async with self._memory_lock:
            self._shared_memory[key] = value
            logger.debug(f"Updated shared memory: {key}")
    
    def get_members(self) -> List[CrewMember]:
        """Get all crew members."""
        return list(self._members.values())
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self._execution_history.copy()
