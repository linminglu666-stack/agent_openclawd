from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DagNode:
    node_id: str
    task_type: str
    task_data: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    timeout_sec: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DagEdge:
    from_node: str
    to_node: str
    condition: str = "always"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DagSpec:
    dag_id: str
    nodes: List[DagNode] = field(default_factory=list)
    edges: List[DagEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "task_type": n.task_type,
                    "task_data": n.task_data,
                    "retries": n.retries,
                    "timeout_sec": n.timeout_sec,
                    "metadata": n.metadata,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "from_node": e.from_node,
                    "to_node": e.to_node,
                    "condition": e.condition,
                    "metadata": e.metadata,
                }
                for e in self.edges
            ],
            "metadata": self.metadata,
        }

