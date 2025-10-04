"""
LangGraph-style Workflow Graphs

DAG-based execution engine with conditional branching, checkpointing,
and state management.
"""

import asyncio
import logging
import yaml
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json


logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Workflow node types."""
    AGENT = "agent"          # Execute agent
    CONDITION = "condition"  # Conditional branching
    CHECKPOINT = "checkpoint"  # Save state
    PARALLEL = "parallel"    # Parallel execution
    ERROR_HANDLER = "error_handler"  # Error handling
    START = "start"          # Entry point
    END = "end"              # Exit point


class EdgeCondition(Enum):
    """Edge condition types."""
    ALWAYS = "always"        # Always traverse
    ON_SUCCESS = "on_success"  # Only if node succeeds
    ON_FAILURE = "on_failure"  # Only if node fails
    CONDITIONAL = "conditional"  # Custom condition


@dataclass
class WorkflowState:
    """State passed through workflow execution."""
    workflow_id: str
    current_node: str
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_to_history(self, node_id: str, result: Any, metadata: Dict = None):
        """Add node execution to history."""
        self.history.append({
            "node_id": node_id,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    
    def create_checkpoint(self, checkpoint_id: str):
        """Create a checkpoint of current state."""
        self.checkpoints[checkpoint_id] = {
            "variables": self.variables.copy(),
            "history_count": len(self.history),
            "timestamp": datetime.now().isoformat()
        }
    
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from a checkpoint."""
        if checkpoint_id not in self.checkpoints:
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        self.variables = checkpoint["variables"].copy()
        # Truncate history
        self.history = self.history[:checkpoint["history_count"]]
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class WorkflowNode:
    """A node in the workflow graph."""
    node_id: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For AGENT nodes
    agent_id: Optional[str] = None
    
    # For CONDITION nodes
    condition_func: Optional[Callable[[WorkflowState], bool]] = None
    
    # For PARALLEL nodes
    parallel_branches: List[List[str]] = field(default_factory=list)
    
    # For ERROR_HANDLER nodes
    error_handler: Optional[Callable[[WorkflowState, Exception], Any]] = None
    
    # Retry configuration
    max_retries: int = 0
    retry_delay: float = 1.0


@dataclass
class WorkflowEdge:
    """An edge connecting workflow nodes."""
    from_node: str
    to_node: str
    condition: EdgeCondition = EdgeCondition.ALWAYS
    condition_func: Optional[Callable[[WorkflowState], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowGraph:
    """
    DAG-based workflow execution engine.
    
    Inspired by LangGraph's stateful workflow patterns.
    """
    
    def __init__(self, name: str, coordinator=None):
        """
        Initialize workflow graph.
        
        Args:
            name: Workflow name
            coordinator: Central coordinator instance
        """
        self.name = name
        self.coordinator = coordinator
        self._nodes: Dict[str, WorkflowNode] = {}
        self._edges: List[WorkflowEdge] = []
        self._entry_node: Optional[str] = None
        self._execution_history: List[Dict[str, Any]] = []
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        agent_id: str = None,
        config: Dict[str, Any] = None,
        **kwargs
    ) -> "WorkflowGraph":
        """
        Add a node to the workflow.
        
        Args:
            node_id: Unique node identifier
            node_type: Type of node
            agent_id: Agent ID for AGENT nodes
            config: Node configuration
            **kwargs: Additional node parameters
            
        Returns:
            Self for method chaining
        """
        node = WorkflowNode(
            node_id=node_id,
            node_type=node_type,
            agent_id=agent_id,
            config=config or {},
            **kwargs
        )
        
        self._nodes[node_id] = node
        
        # Set entry node if START type
        if node_type == NodeType.START:
            self._entry_node = node_id
        
        logger.info(f"Added node to workflow {self.name}: {node_id} ({node_type.value})")
        return self
    
    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: EdgeCondition = EdgeCondition.ALWAYS,
        condition_func: Callable[[WorkflowState], bool] = None
    ) -> "WorkflowGraph":
        """
        Add an edge between nodes.
        
        Args:
            from_node: Source node ID
            to_node: Target node ID
            condition: Edge condition
            condition_func: Custom condition function
            
        Returns:
            Self for method chaining
        """
        if from_node not in self._nodes:
            raise ValueError(f"Source node not found: {from_node}")
        if to_node not in self._nodes:
            raise ValueError(f"Target node not found: {to_node}")
        
        edge = WorkflowEdge(
            from_node=from_node,
            to_node=to_node,
            condition=condition,
            condition_func=condition_func
        )
        
        self._edges.append(edge)
        logger.debug(f"Added edge: {from_node} -> {to_node}")
        return self
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges originating from a node."""
        return [e for e in self._edges if e.from_node == node_id]
    
    async def execute(
        self,
        input: str,
        initial_state: Dict[str, Any] = None,
        max_steps: int = 100
    ) -> WorkflowState:
        """
        Execute the workflow.
        
        Args:
            input: Workflow input
            initial_state: Initial state variables
            max_steps: Maximum execution steps
            
        Returns:
            Final workflow state
        """
        if not self._entry_node:
            raise ValueError("No entry node defined")
        
        # Initialize state
        workflow_id = f"workflow_{self.name}_{int(datetime.now().timestamp())}"
        state = WorkflowState(
            workflow_id=workflow_id,
            current_node=self._entry_node,
            variables=initial_state or {}
        )
        state.variables["input"] = input
        
        logger.info(f"Starting workflow execution: {self.name}")
        start_time = datetime.now()
        
        steps = 0
        try:
            while state.current_node and steps < max_steps:
                node = self._nodes.get(state.current_node)
                if not node:
                    raise ValueError(f"Node not found: {state.current_node}")
                
                # Check if END node
                if node.node_type == NodeType.END:
                    logger.info(f"Reached END node: {node.node_id}")
                    break
                
                # Execute node
                result = await self._execute_node(node, state)
                state.add_to_history(node.node_id, result)
                
                # Find next node
                next_node = await self._find_next_node(node.node_id, state, result)
                state.current_node = next_node
                
                steps += 1
            
            if steps >= max_steps:
                logger.warning(f"Workflow reached max steps: {max_steps}")
                state.error = "Maximum steps exceeded"
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            state.error = str(e)
            
            # Try to find error handler
            error_handler = self._find_error_handler(state.current_node)
            if error_handler:
                try:
                    await self._execute_node(error_handler, state)
                except Exception as handler_error:
                    logger.error(f"Error handler failed: {handler_error}")
        
        end_time = datetime.now()
        
        # Record execution
        execution_record = {
            "workflow_id": workflow_id,
            "workflow_name": self.name,
            "steps": steps,
            "status": "success" if not state.error else "failed",
            "error": state.error,
            "duration": (end_time - start_time).total_seconds(),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        self._execution_history.append(execution_record)
        
        logger.info(f"Workflow {self.name} completed in {steps} steps")
        return state
    
    async def _execute_node(self, node: WorkflowNode, state: WorkflowState) -> Any:
        """Execute a single node."""
        logger.info(f"Executing node: {node.node_id} ({node.node_type.value})")
        
        if node.node_type == NodeType.START:
            return {"status": "started"}
        
        elif node.node_type == NodeType.AGENT:
            return await self._execute_agent_node(node, state)
        
        elif node.node_type == NodeType.CONDITION:
            return await self._execute_condition_node(node, state)
        
        elif node.node_type == NodeType.CHECKPOINT:
            state.create_checkpoint(node.node_id)
            return {"checkpoint_created": node.node_id}
        
        elif node.node_type == NodeType.PARALLEL:
            return await self._execute_parallel_node(node, state)
        
        elif node.node_type == NodeType.ERROR_HANDLER:
            if node.error_handler:
                return node.error_handler(state, Exception(state.error or "Unknown error"))
            return {"handled": True}
        
        return None
    
    async def _execute_agent_node(self, node: WorkflowNode, state: WorkflowState) -> Any:
        """Execute an agent node with retry logic."""
        if not node.agent_id:
            raise ValueError(f"No agent_id for AGENT node: {node.node_id}")
        
        # Get agent from coordinator
        if self.coordinator:
            agent = self.coordinator.get_agent(node.agent_id)
        else:
            raise ValueError("No coordinator available")
        
        if not agent:
            raise ValueError(f"Agent not found: {node.agent_id}")
        
        # Prepare input from state
        input_data = node.config.get("input_template", "{input}")
        for key, value in state.variables.items():
            input_data = input_data.replace(f"{{{key}}}", str(value))
        
        # Retry logic
        last_error = None
        for attempt in range(node.max_retries + 1):
            try:
                from agentosx.agents.base import ExecutionContext
                context = ExecutionContext(
                    input=input_data,
                    session_id=state.workflow_id,
                    metadata={
                        "workflow": self.name,
                        "node": node.node_id,
                        "state": state.variables.copy(),
                        "attempt": attempt
                    }
                )
                
                result = await agent.process(input_data, context)
                
                # Store result in state variables if output_key specified
                if "output_key" in node.config:
                    state.variables[node.config["output_key"]] = result
                
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(f"Node {node.node_id} attempt {attempt + 1} failed: {e}")
                if attempt < node.max_retries:
                    await asyncio.sleep(node.retry_delay * (attempt + 1))
        
        # All retries failed
        raise last_error or Exception("Unknown error")
    
    async def _execute_condition_node(self, node: WorkflowNode, state: WorkflowState) -> Any:
        """Execute a condition node."""
        if node.condition_func:
            result = node.condition_func(state)
            return {"condition_result": result}
        return {"condition_result": False}
    
    async def _execute_parallel_node(self, node: WorkflowNode, state: WorkflowState) -> Any:
        """Execute parallel branches."""
        results = []
        
        for branch in node.parallel_branches:
            # Execute each branch
            branch_tasks = []
            for node_id in branch:
                branch_node = self._nodes.get(node_id)
                if branch_node:
                    branch_tasks.append(self._execute_node(branch_node, state))
            
            # Execute branch in parallel
            if branch_tasks:
                branch_results = await asyncio.gather(*branch_tasks, return_exceptions=True)
                results.append(branch_results)
        
        return {"parallel_results": results}
    
    async def _find_next_node(
        self,
        current_node_id: str,
        state: WorkflowState,
        result: Any
    ) -> Optional[str]:
        """Find the next node to execute based on edges and conditions."""
        outgoing_edges = self.get_outgoing_edges(current_node_id)
        
        if not outgoing_edges:
            return None  # No more nodes
        
        for edge in outgoing_edges:
            should_traverse = False
            
            if edge.condition == EdgeCondition.ALWAYS:
                should_traverse = True
            
            elif edge.condition == EdgeCondition.ON_SUCCESS:
                should_traverse = result is not None and not state.error
            
            elif edge.condition == EdgeCondition.ON_FAILURE:
                should_traverse = state.error is not None
            
            elif edge.condition == EdgeCondition.CONDITIONAL:
                if edge.condition_func:
                    should_traverse = edge.condition_func(state)
            
            if should_traverse:
                logger.debug(f"Traversing edge: {current_node_id} -> {edge.to_node}")
                return edge.to_node
        
        return None  # No edge condition met
    
    def _find_error_handler(self, current_node_id: str) -> Optional[WorkflowNode]:
        """Find error handler node connected to current node."""
        for edge in self._edges:
            if edge.from_node == current_node_id and edge.condition == EdgeCondition.ON_FAILURE:
                target_node = self._nodes.get(edge.to_node)
                if target_node and target_node.node_type == NodeType.ERROR_HANDLER:
                    return target_node
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Export workflow to dictionary."""
        return {
            "name": self.name,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "agent_id": node.agent_id,
                    "config": node.config,
                    "metadata": node.metadata
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "from_node": edge.from_node,
                    "to_node": edge.to_node,
                    "condition": edge.condition.value
                }
                for edge in self._edges
            ],
            "entry_node": self._entry_node
        }
    
    @classmethod
    def from_yaml(cls, yaml_file: str, coordinator=None) -> "WorkflowGraph":
        """
        Load workflow from YAML file.
        
        Args:
            yaml_file: Path to YAML file
            coordinator: Central coordinator
            
        Returns:
            WorkflowGraph instance
        """
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data, coordinator)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], coordinator=None) -> "WorkflowGraph":
        """Create workflow from dictionary."""
        name = data.get("name", "unnamed_workflow")
        workflow = cls(name, coordinator)
        
        # Add nodes
        for node_data in data.get("nodes", []):
            workflow.add_node(
                node_id=node_data["node_id"],
                node_type=NodeType(node_data["node_type"]),
                agent_id=node_data.get("agent_id"),
                config=node_data.get("config", {})
            )
        
        # Add edges
        for edge_data in data.get("edges", []):
            workflow.add_edge(
                from_node=edge_data["from_node"],
                to_node=edge_data["to_node"],
                condition=EdgeCondition(edge_data.get("condition", "always"))
            )
        
        return workflow
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get workflow execution history."""
        return self._execution_history.copy()
