from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import threading

from base_types import (
    utc_now, EntropyCategory, EntropyLevel, AttributionResult, EntropySample
)
from calculator import EntropyCalculator, EntropySample


@dataclass
class SourceProfile:
    source: str
    category: EntropyCategory
    level: EntropyLevel
    sample_count: int = 0
    total_entropy: float = 0.0
    mean_entropy: float = 0.0
    trend_slope: float = 0.0
    last_seen: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    correlated_sources: List[str] = field(default_factory=list)


@dataclass
class RootCauseHypothesis:
    hypothesis_id: str
    source: str
    category: EntropyCategory
    description: str
    evidence: List[str]
    confidence: float
    related_sources: List[str]
    suggested_investigations: List[str]


@dataclass
class CorrelationResult:
    source_a: str
    source_b: str
    correlation_coefficient: float
    sample_count: int
    significance: str


class EntropyAttributor:
    def __init__(
        self,
        calculator: EntropyCalculator,
        correlation_threshold: float = 0.7,
        min_samples_for_correlation: int = 10,
        max_hypotheses: int = 50,
    ):
        self._calculator = calculator
        self._correlation_threshold = correlation_threshold
        self._min_samples_for_correlation = min_samples_for_correlation
        self._max_hypotheses = max_hypotheses
        self._source_profiles: Dict[str, SourceProfile] = {}
        self._correlations: Dict[Tuple[str, str], CorrelationResult] = {}
        self._hypotheses: List[RootCauseHypothesis] = []
        self._lock = threading.RLock()

    def analyze(
        self,
        top_n: int = 10,
        include_correlations: bool = True,
        include_hypotheses: bool = True,
    ) -> List[AttributionResult]:
        with self._lock:
            self._update_source_profiles()
            if include_correlations:
                self._compute_correlations()
            total_entropy = self._calculator.compute_total_entropy()
            attributions: List[AttributionResult] = []
            for source, profile in self._source_profiles.items():
                contribution_ratio = profile.mean_entropy / total_entropy if total_entropy > 0 else 0.0
                correlated = profile.correlated_sources[:5] if include_correlations else []
                hypothesis = ""
                if include_hypotheses:
                    hypothesis = self._generate_hypothesis_description(profile, correlated)
                attributions.append(AttributionResult(
                    source=source,
                    category=profile.category,
                    contribution_ratio=contribution_ratio,
                    absolute_value=profile.mean_entropy,
                    trend_impact=profile.trend_slope,
                    related_sources=correlated,
                    root_cause_hypothesis=hypothesis,
                ))
            attributions.sort(key=lambda x: x.absolute_value, reverse=True)
            return attributions[:top_n]

    def _update_source_profiles(self) -> None:
        now = utc_now()
        since = now - timedelta(hours=24)
        samples_by_source: Dict[str, List[EntropySample]] = defaultdict(list)
        all_samples = self._calculator.get_samples(since=since, limit=10000)
        for sample in all_samples:
            samples_by_source[sample.source].append(sample)
        for source, samples in samples_by_source.items():
            if not samples:
                continue
            values = [s.value for s in samples]
            timestamps = [s.timestamp for s in samples]
            mean_val = sum(values) / len(values)
            slope = self._compute_slope(timestamps, values)
            if source not in self._source_profiles:
                self._source_profiles[source] = SourceProfile(
                    source=source,
                    category=samples[0].category,
                    level=samples[0].level,
                )
            profile = self._source_profiles[source]
            profile.sample_count = len(samples)
            profile.total_entropy = sum(values)
            profile.mean_entropy = mean_val
            profile.trend_slope = slope
            profile.last_seen = max(timestamps)
            profile.first_seen = min(timestamps) if not profile.first_seen else min(profile.first_seen, min(timestamps))

    def _compute_slope(
        self,
        timestamps: List[datetime],
        values: List[float],
    ) -> float:
        if len(values) < 2:
            return 0.0
        ts = [t.timestamp() for t in timestamps]
        n = len(values)
        sum_t = sum(ts)
        sum_v = sum(values)
        sum_tt = sum(t * t for t in ts)
        sum_tv = sum(t * v for t, v in zip(ts, values))
        denom = n * sum_tt - sum_t * sum_t
        if abs(denom) < 1e-10:
            return 0.0
        slope = (n * sum_tv - sum_t * sum_v) / denom
        return slope * 3600

    def _compute_correlations(self) -> None:
        now = utc_now()
        since = now - timedelta(hours=24)
        samples = self._calculator.get_samples(since=since, limit=10000)
        by_source: Dict[str, Dict[datetime, float]] = defaultdict(dict)
        for sample in samples:
            by_source[sample.source][sample.timestamp] = sample.value
        sources = list(by_source.keys())
        self._correlations.clear()
        for i, source_a in enumerate(sources):
            for source_b in sources[i + 1:]:
                corr = self._pearson_correlation(
                    by_source[source_a],
                    by_source[source_b],
                )
                if corr is not None and abs(corr) >= self._correlation_threshold:
                    result = CorrelationResult(
                        source_a=source_a,
                        source_b=source_b,
                        correlation_coefficient=corr,
                        sample_count=min(len(by_source[source_a]), len(by_source[source_b])),
                        significance="strong" if abs(corr) >= 0.9 else "moderate",
                    )
                    key = (source_a, source_b) if source_a < source_b else (source_b, source_a)
                    self._correlations[key] = result
                    if source_b not in self._source_profiles[source_a].correlated_sources:
                        self._source_profiles[source_a].correlated_sources.append(source_b)
                    if source_a not in self._source_profiles[source_b].correlated_sources:
                        self._source_profiles[source_b].correlated_sources.append(source_a)

    def _pearson_correlation(
        self,
        series_a: Dict[datetime, float],
        series_b: Dict[datetime, float],
    ) -> Optional[float]:
        common_times = set(series_a.keys()) & set(series_b.keys())
        if len(common_times) < self._min_samples_for_correlation:
            return None
        a_values = [series_a[t] for t in common_times]
        b_values = [series_b[t] for t in common_times]
        n = len(a_values)
        mean_a = sum(a_values) / n
        mean_b = sum(b_values) / n
        var_a = sum((v - mean_a) ** 2 for v in a_values)
        var_b = sum((v - mean_b) ** 2 for v in b_values)
        if var_a == 0 or var_b == 0:
            return None
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(a_values, b_values))
        return cov / (var_a * var_b) ** 0.5

    def _generate_hypothesis_description(
        self,
        profile: SourceProfile,
        correlated: List[str],
    ) -> str:
        parts: List[str] = []
        if profile.trend_slope > 0.01:
            parts.append(f"Increasing trend detected (slope={profile.trend_slope:.4f}/h)")
        elif profile.trend_slope < -0.01:
            parts.append(f"Decreasing trend (slope={profile.trend_slope:.4f}/h)")
        if profile.mean_entropy > 0.7:
            parts.append("High entropy source")
        if correlated:
            parts.append(f"Correlated with {len(correlated)} other source(s)")
        if not parts:
            return "No significant patterns detected"
        return "; ".join(parts)

    def generate_hypotheses(self) -> List[RootCauseHypothesis]:
        with self._lock:
            self._hypotheses.clear()
            for source, profile in self._source_profiles.items():
                if profile.mean_entropy < 0.3:
                    continue
                evidence: List[str] = []
                suggested: List[str] = []
                if profile.trend_slope > 0.05:
                    evidence.append(f"Rapidly increasing entropy ({profile.trend_slope:.4f}/hour)")
                    suggested.append("Investigate recent changes to this component")
                if profile.mean_entropy > 0.8:
                    evidence.append("Sustained high entropy levels")
                    suggested.append("Consider architectural refactoring")
                if len(profile.correlated_sources) > 2:
                    evidence.append(f"Strong correlation with {len(profile.correlated_sources)} sources")
                    suggested.append("Analyze shared dependencies")
                if not evidence:
                    continue
                hypothesis = RootCauseHypothesis(
                    hypothesis_id=f"hyp-{source}",
                    source=source,
                    category=profile.category,
                    description=f"High entropy source: {source}",
                    evidence=evidence,
                    confidence=min(1.0, profile.mean_entropy * (1 + abs(profile.trend_slope))),
                    related_sources=profile.correlated_sources[:5],
                    suggested_investigations=suggested,
                )
                self._hypotheses.append(hypothesis)
            self._hypotheses.sort(key=lambda h: h.confidence, reverse=True)
            return self._hypotheses[:self._max_hypotheses]

    def get_source_profile(self, source: str) -> Optional[SourceProfile]:
        with self._lock:
            return self._source_profiles.get(source)

    def get_correlations(
        self,
        source: Optional[str] = None,
        min_correlation: float = 0.5,
    ) -> List[CorrelationResult]:
        with self._lock:
            results = list(self._correlations.values())
        if source:
            results = [r for r in results if r.source_a == source or r.source_b == source]
        results = [r for r in results if abs(r.correlation_coefficient) >= min_correlation]
        results.sort(key=lambda r: abs(r.correlation_coefficient), reverse=True)
        return results

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "source_count": len(self._source_profiles),
                "correlation_count": len(self._correlations),
                "hypothesis_count": len(self._hypotheses),
                "high_entropy_sources": sum(
                    1 for p in self._source_profiles.values() if p.mean_entropy > 0.7
                ),
                "increasing_trend_sources": sum(
                    1 for p in self._source_profiles.values() if p.trend_slope > 0.01
                ),
            }
