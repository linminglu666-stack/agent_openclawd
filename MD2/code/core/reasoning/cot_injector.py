from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger


class CoTTemplate(Enum):
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    AUTO = "auto"


@dataclass
class CoTResult:
    prompt: str
    template: CoTTemplate
    reasoning_steps: List[str] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence: float = 0.5


ZERO_SHOT_TEMPLATE = """请一步步思考并回答以下问题：

问题：{question}

让我们一步步来分析：
1. 首先，理解问题的核心是什么...
2. 然后，分析相关的信息和条件...
3. 接着，推导出结论...
4. 最后，给出答案...

请按照上述步骤详细思考并回答。"""

FEW_SHOT_TEMPLATE = """以下是一些示例问题和解答方式：

示例1：
问题：小明有5个苹果，给了小红2个，又买了3个，现在有几个？
解答：
1. 小明原来有5个苹果
2. 给了小红2个，剩下 5-2=3 个
3. 又买了3个，现在有 3+3=6 个
答案：6个苹果

示例2：
问题：一个长方形的长是8米，宽是5米，求面积和周长。
解答：
1. 长方形的面积 = 长 × 宽 = 8 × 5 = 40 平方米
2. 长方形的周长 = 2 × (长 + 宽) = 2 × (8 + 5) = 26 米
答案：面积40平方米，周长26米

现在请回答以下问题：
问题：{question}

请按照示例的方式，一步步思考并解答："""


class CoTInjector:
    def __init__(self, default_template: CoTTemplate = CoTTemplate.AUTO):
        self._default_template = default_template
        self._logger = get_logger("reasoning.cot_injector")
        self._templates = {
            CoTTemplate.ZERO_SHOT: ZERO_SHOT_TEMPLATE,
            CoTTemplate.FEW_SHOT: FEW_SHOT_TEMPLATE,
        }

    def inject(self, question: str, template: Optional[CoTTemplate] = None, context: Optional[Dict[str, Any]] = None) -> CoTResult:
        selected_template = template or self._default_template

        if selected_template == CoTTemplate.AUTO:
            selected_template = self._auto_select_template(question, context or {})

        template_str = self._templates.get(selected_template, ZERO_SHOT_TEMPLATE)
        prompt = template_str.format(question=question)

        self._logger.debug("Injected CoT", template=selected_template.value, question_len=len(question))

        return CoTResult(
            prompt=prompt,
            template=selected_template,
        )

    def _auto_select_template(self, question: str, context: Dict[str, Any]) -> CoTTemplate:
        if context.get("examples") or len(question) > 200:
            return CoTTemplate.FEW_SHOT

        complexity_keywords = ["计算", "分析", "比较", "推导", "证明", "solve", "calculate", "analyze"]
        question_lower = question.lower()
        if any(kw in question_lower for kw in complexity_keywords):
            return CoTTemplate.FEW_SHOT

        return CoTTemplate.ZERO_SHOT

    def parse_response(self, response: str) -> CoTResult:
        steps = []
        lines = response.strip().split("\n")
        current_step = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line[0].isdigit() and "." in line[:3]:
                if current_step:
                    steps.append(" ".join(current_step))
                current_step = [line]
            elif line.startswith("答案") or line.startswith("Answer") or line.startswith("结论"):
                if current_step:
                    steps.append(" ".join(current_step))
                current_step = []
                break
            else:
                current_step.append(line)

        if current_step:
            steps.append(" ".join(current_step))

        final_answer = None
        for line in lines:
            if "答案" in line or "Answer" in line or "结论" in line:
                parts = line.split("：") if "：" in line else line.split(":")
                if len(parts) > 1:
                    final_answer = parts[1].strip()
                break

        return CoTResult(
            prompt=response,
            template=CoTTemplate.ZERO_SHOT,
            reasoning_steps=steps,
            final_answer=final_answer,
            confidence=0.7 if steps else 0.3,
        )

    def add_template(self, name: str, template: str) -> None:
        self._templates[CoTTemplate(name)] = template
        self._logger.info("Added custom template", name=name)
