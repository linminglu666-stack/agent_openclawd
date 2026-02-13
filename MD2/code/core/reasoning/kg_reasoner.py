from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interfaces import IReasoner


Triple = Tuple[str, str, str]


@dataclass
class KnowledgeGraph:
    triples: Set[Triple] = field(default_factory=set)

    def add(self, s: str, p: str, o: str) -> bool:
        self.triples.add((str(s), str(p), str(o)))
        return True

    def add_many(self, triples: List[Dict[str, Any]]) -> int:
        n = 0
        for t in triples or []:
            if "s" in t and "p" in t and "o" in t:
                self.add(t["s"], t["p"], t["o"])
                n += 1
        return n

    def query(self, s: Optional[str] = None, p: Optional[str] = None, o: Optional[str] = None) -> List[Triple]:
        out: List[Triple] = []
        for ts, tp, to in self.triples:
            if s is not None and ts != s:
                continue
            if p is not None and tp != p:
                continue
            if o is not None and to != o:
                continue
            out.append((ts, tp, to))
        return out

    def closure_is_a(self) -> None:
        changed = True
        while changed:
            changed = False
            edges = list(self.query(p="is_a"))
            for a, _, b in edges:
                for b2, _, c in edges:
                    if b2 != b:
                        continue
                    inferred = (a, "is_a", c)
                    if inferred not in self.triples:
                        self.triples.add(inferred)
                        changed = True


class NeuroSymbolicKGReasoner(IReasoner):
    def __init__(self):
        self._kg = KnowledgeGraph()

    @property
    def strategy(self) -> str:
        return "neuro_symbolic_kg"

    async def reason(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        triples = context.get("triples") or []
        self._kg.add_many(triples)
        if context.get("enable_is_a_closure") is True:
            self._kg.closure_is_a()

        query = context.get("query") or {}
        s = query.get("s") or query.get("subject")
        p = query.get("p") or query.get("predicate")
        o = query.get("o") or query.get("object")
        path = query.get("path")

        if path:
            result = self._path_query(str(s or ""), [str(x) for x in path])
            return {"strategy": self.strategy, "query": query, "result": result, "confidence": 0.65}

        matches = self._kg.query(s=str(s) if s is not None else None, p=str(p) if p is not None else None, o=str(o) if o is not None else None)
        return {
            "strategy": self.strategy,
            "query": query,
            "matches": [{"s": ms, "p": mp, "o": mo} for (ms, mp, mo) in matches],
            "confidence": 0.7 if matches else 0.3,
        }

    async def evaluate(self, result: Dict[str, Any]) -> float:
        try:
            return float(result.get("confidence", 0.5))
        except Exception:
            return 0.5

    def _path_query(self, subject: str, predicates: List[str]) -> List[Dict[str, Any]]:
        if not subject:
            return []
        frontier: Set[str] = {subject}
        steps: List[Dict[str, Any]] = []
        for pred in predicates:
            next_frontier: Set[str] = set()
            for node in frontier:
                for _, _, obj in self._kg.query(s=node, p=pred):
                    next_frontier.add(obj)
            steps.append({"predicate": pred, "nodes": sorted(next_frontier)})
            frontier = next_frontier
            if not frontier:
                break
        return steps

