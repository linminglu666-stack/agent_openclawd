from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


@dataclass
class SampleResult:
    sample_id: str
    answer: str
    reasoning: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    final_answer: str
    confidence: float
    vote_distribution: Dict[str, int]
    total_samples: int
    agreement_ratio: float
    samples: List[SampleResult] = field(default_factory=list)
    reasoning_trace: List[str] = field(default_factory=list)


@dataclass
class SamplerConfig:
    num_samples: int = 5
    temperature: float = 0.7
    aggregation: str = "majority"
    min_agreement: float = 0.5


class SelfConsistencySampler:
    def __init__(self, config: Optional[SamplerConfig] = None):
        self._config = config or SamplerConfig()
        self._logger = get_logger("reasoning.self_consistency")
        self._sample_counter = 0

    async def sample(
        self,
        query: str,
        generator: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConsensusResult:
        ctx = context or {}
        samples: List[SampleResult] = []

        for i in range(self._config.num_samples):
            sample = await self._generate_sample(query, i, ctx)
            samples.append(sample)

        final_answer, confidence, vote_dist = self._aggregate(samples)

        agreement = max(vote_dist.values()) / len(samples) if samples else 0.0

        reasoning_trace = [
            f"Sample {i+1}: {s.answer[:50]}..." if len(s.answer) > 50 else f"Sample {i+1}: {s.answer}"
            for i, s in enumerate(samples)
        ]
        reasoning_trace.append(f"Consensus: {final_answer} (confidence: {confidence:.2f})")

        self._logger.info(
            "Self-consistency sampling complete",
            total_samples=len(samples),
            agreement_ratio=agreement,
            final_answer=final_answer[:50] if final_answer else None,
        )

        return ConsensusResult(
            final_answer=final_answer,
            confidence=confidence,
            vote_distribution=vote_dist,
            total_samples=len(samples),
            agreement_ratio=agreement,
            samples=samples,
            reasoning_trace=reasoning_trace,
        )

    async def _generate_sample(self, query: str, index: int, context: Dict[str, Any]) -> SampleResult:
        self._sample_counter += 1
        sample_id = f"sample_{self._sample_counter}"

        variations = [
            f"思考角度{index + 1}: {query}",
            f"从不同视角分析{index + 1}: {query}",
            f"方法{index + 1}解决问题: {query}",
        ]

        answer = variations[index % len(variations)]

        if "计算" in query or "calculate" in query.lower():
            base = 10 + index * 2
            answer = f"通过方法{index + 1}计算，结果是 {base}（模拟结果）"
        elif "分析" in query or "analyze" in query.lower():
            answer = f"分析角度{index + 1}: 综合考虑各方面因素，结论是肯定的（模拟分析）"

        confidence = 0.5 + (hash(answer) % 50) / 100.0

        return SampleResult(
            sample_id=sample_id,
            answer=answer,
            reasoning=f"Sample {index + 1} reasoning path",
            confidence=confidence,
            metadata={"temperature": self._config.temperature, "index": index},
        )

    def _aggregate(self, samples: List[SampleResult]) -> Tuple[str, float, Dict[str, int]]:
        if not samples:
            return "", 0.0, {}

        normalized_answers = []
        for s in samples:
            normalized = self._normalize_answer(s.answer)
            normalized_answers.append(normalized)

        vote_counter = Counter(normalized_answers)
        vote_distribution = dict(vote_counter)

        if self._config.aggregation == "majority":
            most_common = vote_counter.most_common(1)
            if most_common:
                winner, votes = most_common[0]
                confidence = votes / len(samples)
                return winner, confidence, vote_distribution

        elif self._config.aggregation == "weighted":
            weighted_votes: Dict[str, float] = {}
            for sample, normalized in zip(samples, normalized_answers):
                weighted_votes[normalized] = weighted_votes.get(normalized, 0.0) + sample.confidence

            winner = max(weighted_votes, key=weighted_votes.get)
            total_weight = sum(weighted_votes.values())
            confidence = weighted_votes[winner] / total_weight if total_weight > 0 else 0.0
            return winner, confidence, vote_distribution

        return samples[0].answer, 0.5, vote_distribution

    def _normalize_answer(self, answer: str) -> str:
        normalized = answer.lower().strip()
        normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())

        words = normalized.split()
        if len(words) > 10:
            normalized = " ".join(words[:10])

        return normalized

    def set_config(self, config: SamplerConfig) -> None:
        self._config = config
        self._logger.info("Sampler config updated", num_samples=config.num_samples)
