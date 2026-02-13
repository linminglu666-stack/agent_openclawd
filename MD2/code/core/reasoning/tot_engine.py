from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


@dataclass
class ToTNode:
    node_id: str
    content: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    score: float = 0.0
    depth: int = 0
    is_terminal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToTResult:
    root_id: str
    nodes: Dict[str, ToTNode] = field(default_factory=dict)
    best_path: List[str] = field(default_factory=list)
    best_answer: Optional[str] = None
    confidence: float = 0.5
    total_nodes: int = 0


class TreeOfThoughtEngine:
    def __init__(
        self,
        max_depth: int = 4,
        branch_factor: int = 3,
        beam_width: int = 2,
        scoring_threshold: float = 0.5,
    ):
        self._max_depth = max_depth
        self._branch_factor = branch_factor
        self._beam_width = beam_width
        self._scoring_threshold = scoring_threshold
        self._logger = get_logger("reasoning.tot_engine")
        self._node_counter = 0

    def expand(self, problem: str, context: Optional[Dict[str, Any]] = None) -> ToTResult:
        self._node_counter = 0
        nodes: Dict[str, ToTNode] = {}

        root = self._create_node(content=problem, depth=0)
        nodes[root.node_id] = root
        result = ToTResult(root_id=root.node_id, nodes=nodes)

        frontier = [root.node_id]
        for depth in range(self._max_depth):
            if not frontier:
                break

            next_frontier = []
            for node_id in frontier:
                node = nodes[node_id]
                if node.is_terminal:
                    continue

                children = self._generate_thoughts(node, context or {})
                scored_children = []

                for child_content in children:
                    child = self._create_node(
                        content=child_content,
                        parent_id=node.node_id,
                        depth=depth + 1,
                    )
                    child.score = self._evaluate_thought(child_content, problem, context or {})
                    child.is_terminal = self._is_terminal(child_content)
                    nodes[child.node_id] = child
                    nodes[node.node_id].children.append(child.node_id)
                    scored_children.append((child.node_id, child.score))

                scored_children.sort(key=lambda x: x[1], reverse=True)
                next_frontier.extend([cid for cid, _ in scored_children[: self._beam_width]])

            frontier = next_frontier

        result.total_nodes = len(nodes)
        result.best_path, result.best_answer, result.confidence = self._find_best_path(nodes, root.node_id)

        self._logger.info("ToT expansion complete", total_nodes=result.total_nodes, best_depth=len(result.best_path))
        return result

    def _create_node(self, content: str, parent_id: Optional[str] = None, depth: int = 0) -> ToTNode:
        self._node_counter += 1
        return ToTNode(
            node_id=f"tot_{self._node_counter}",
            content=content,
            parent_id=parent_id,
            depth=depth,
        )

    def _generate_thoughts(self, node: ToTNode, context: Dict[str, Any]) -> List[str]:
        thoughts = []
        base = node.content

        if "分析" in base or "analyze" in base.lower():
            thoughts = [
                f"思路A: 从正面角度分析 - {base}",
                f"思路B: 从反面角度分析 - {base}",
                f"思路C: 从中立角度分析 - {base}",
            ]
        elif "计算" in base or "calculate" in base.lower():
            thoughts = [
                f"方法1: 直接计算 - {base}",
                f"方法2: 分步计算 - {base}",
                f"方法3: 估算验证 - {base}",
            ]
        else:
            thoughts = [
                f"思考方向1: {base} -> 分析关键因素",
                f"思考方向2: {base} -> 考虑替代方案",
                f"思考方向3: {base} -> 评估可行性",
            ]

        return thoughts[: self._branch_factor]

    def _evaluate_thought(self, thought: str, problem: str, context: Dict[str, Any]) -> float:
        score = 0.5

        positive_indicators = ["正确", "合理", "可行", "有效", "correct", "valid", "reasonable"]
        for ind in positive_indicators:
            if ind in thought.lower():
                score += 0.1

        if len(thought) > 50:
            score += 0.1
        if len(thought) > 100:
            score += 0.05

        return min(score, 1.0)

    def _is_terminal(self, content: str) -> bool:
        terminal_indicators = ["答案", "结论", "最终", "answer", "conclusion", "final"]
        return any(ind in content.lower() for ind in terminal_indicators)

    def _find_best_path(self, nodes: Dict[str, ToTNode], root_id: str) -> Tuple[List[str], Optional[str], float]:
        best_leaf: Optional[ToTNode] = None
        best_score = -1.0

        for node in nodes.values():
            if node.is_terminal or node.depth == self._max_depth:
                if node.score > best_score:
                    best_score = node.score
                    best_leaf = node

        if not best_leaf:
            for node in nodes.values():
                if node.score > best_score:
                    best_score = node.score
                    best_leaf = node

        if not best_leaf:
            return [root_id], None, 0.0

        path = []
        current = best_leaf
        while current:
            path.append(current.node_id)
            if current.parent_id:
                current = nodes.get(current.parent_id)
            else:
                break

        path.reverse()
        return path, best_leaf.content, best_score

    def get_node(self, result: ToTResult, node_id: str) -> Optional[ToTNode]:
        return result.nodes.get(node_id)

    def get_children(self, result: ToTResult, node_id: str) -> List[ToTNode]:
        node = result.nodes.get(node_id)
        if not node:
            return []
        return [result.nodes[cid] for cid in node.children if cid in result.nodes]
