"""
复杂度评估器
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComplexityScore:
    overall: float
    factors: Dict[str, float] = field(default_factory=dict)
    
    level: str = "medium"
    confidence: float = 0.8
    
    def __post_init__(self):
        if self.overall < 0.3:
            self.level = "simple"
        elif self.overall < 0.6:
            self.level = "medium"
        elif self.overall < 0.8:
            self.level = "complex"
        else:
            self.level = "very_complex"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "factors": self.factors,
            "level": self.level,
            "confidence": self.confidence,
        }


class ComplexityEstimator:
    
    REASONING_KEYWORDS = [
        "analyze", "analysis", "reasoning", "logic", "prove", "证明", "分析",
        "推理", "逻辑", "because", "therefore", "hence", "step by step",
        "compare", "contrast", "evaluate", "assess", "为什么", "原因",
    ]
    
    CODING_KEYWORDS = [
        "code", "function", "class", "implement", "debug", "refactor",
        "代码", "函数", "类", "实现", "调试", "重构", "algorithm", "算法",
        "program", "script", "python", "javascript", "java",
    ]
    
    CREATIVE_KEYWORDS = [
        "create", "write", "compose", "design", "imagine", "creative",
        "创作", "写", "设计", "想象", "story", "poem", "小说", "诗歌",
    ]
    
    MATH_KEYWORDS = [
        "calculate", "compute", "math", "equation", "formula", "solve",
        "计算", "数学", "方程", "公式", "求解", "derivative", "integral",
    ]
    
    def __init__(self):
        self.weights = {
            "length": 0.15,
            "structure": 0.15,
            "reasoning": 0.25,
            "domain": 0.20,
            "context": 0.15,
            "technical": 0.10,
        }
    
    def estimate(self, prompt: str, history: Optional[List[Dict]] = None) -> ComplexityScore:
        factors = {}
        
        factors["length"] = self._calc_length_factor(prompt, history or [])
        factors["structure"] = self._calc_structure_factor(prompt)
        factors["reasoning"] = self._calc_reasoning_factor(prompt)
        factors["domain"] = self._calc_domain_factor(prompt)
        factors["context"] = self._calc_context_factor(history or [])
        factors["technical"] = self._calc_technical_factor(prompt)
        
        total = sum(
            factors.get(name, 0) * weight
            for name, weight in self.weights.items()
        )
        
        confidence = self._calculate_confidence(factors)
        
        return ComplexityScore(
            overall=min(max(total, 0.0), 1.0),
            factors=factors,
            confidence=confidence,
        )
    
    def _calc_length_factor(self, prompt: str, history: List[Dict]) -> float:
        prompt_len = len(prompt)
        history_len = sum(len(str(h.get("content", ""))) for h in history)
        total_len = prompt_len + history_len
        
        if total_len < 100:
            return 0.1
        elif total_len < 500:
            return 0.3
        elif total_len < 1500:
            return 0.5
        elif total_len < 3000:
            return 0.7
        else:
            return min(0.9, 0.7 + (total_len - 3000) / 10000)
    
    def _calc_structure_factor(self, prompt: str) -> float:
        score = 0.0
        
        if re.search(r'\d+\.', prompt):
            score += 0.2
        if re.search(r'[一二三四五六七八九十]、', prompt):
            score += 0.2
        if re.search(r'[-•*]\s', prompt):
            score += 0.15
        if re.search(r'if|then|else|when|如果|那么|否则', prompt, re.I):
            score += 0.2
        if re.search(r'first|second|finally|首先|其次|最后', prompt, re.I):
            score += 0.15
        if prompt.count('\n') > 5:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calc_reasoning_factor(self, prompt: str) -> float:
        prompt_lower = prompt.lower()
        
        reasoning_count = sum(1 for kw in self.REASONING_KEYWORDS if kw in prompt_lower)
        math_count = sum(1 for kw in self.MATH_KEYWORDS if kw in prompt_lower)
        
        total_keywords = reasoning_count + math_count * 1.5
        
        if total_keywords == 0:
            return 0.2
        elif total_keywords < 3:
            return 0.4
        elif total_keywords < 6:
            return 0.6
        elif total_keywords < 10:
            return 0.8
        else:
            return 0.95
    
    def _calc_domain_factor(self, prompt: str) -> float:
        prompt_lower = prompt.lower()
        
        coding_count = sum(1 for kw in self.CODING_KEYWORDS if kw in prompt_lower)
        creative_count = sum(1 for kw in self.CREATIVE_KEYWORDS if kw in prompt_lower)
        
        if coding_count > 3:
            return 0.8
        elif creative_count > 3:
            return 0.5
        elif coding_count > 0 or creative_count > 0:
            return 0.6
        else:
            return 0.3
    
    def _calc_context_factor(self, history: List[Dict]) -> float:
        if not history:
            return 0.1
        
        history_len = len(history)
        
        if history_len < 2:
            return 0.2
        elif history_len < 5:
            return 0.4
        elif history_len < 10:
            return 0.6
        else:
            return min(0.9, 0.6 + history_len * 0.02)
    
    def _calc_technical_factor(self, prompt: str) -> float:
        technical_patterns = [
            r'\bapi\b', r'\bjson\b', r'\bxml\b', r'\bsql\b',
            r'\bhttp\b', r'\brest\b', r'\bgrpc\b',
            r'\bfunction\b', r'\bclass\b', r'\bobject\b',
            r'\bvariable\b', r'\bconstant\b', r'\barray\b',
            r'函数', r'类', r'对象', r'变量',
        ]
        
        prompt_lower = prompt.lower()
        count = sum(1 for p in technical_patterns if re.search(p, prompt_lower))
        
        return min(count * 0.15, 0.9)
    
    def _calculate_confidence(self, factors: Dict[str, float]) -> float:
        variance = max(factors.values()) - min(factors.values())
        
        if variance < 0.2:
            return 0.9
        elif variance < 0.4:
            return 0.7
        elif variance < 0.6:
            return 0.5
        else:
            return 0.3
    
    def classify_task(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        coding_score = sum(1 for kw in self.CODING_KEYWORDS if kw in prompt_lower)
        reasoning_score = sum(1 for kw in self.REASONING_KEYWORDS if kw in prompt_lower)
        creative_score = sum(1 for kw in self.CREATIVE_KEYWORDS if kw in prompt_lower)
        math_score = sum(1 for kw in self.MATH_KEYWORDS if kw in prompt_lower)
        
        scores = {
            "coding": coding_score,
            "reasoning": reasoning_score,
            "creative": creative_score,
            "math": math_score,
        }
        
        max_task = max(scores, key=scores.get)
        
        if scores[max_task] >= 2:
            return max_task
        else:
            return "general"
