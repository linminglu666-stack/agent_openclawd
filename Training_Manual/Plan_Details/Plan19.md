# Plan19 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan19
- 主计划标题：1) 任务拆解与任务分发方案（Process + Data Model）

## 核心要点索引（来自主计划）
1:1) 任务拆解与任务分发方案（Process + Data Model）
2:1.1 核心目标
10:1.2 关键对象（建议最少字段）
55:1.3 拆解规则（可执行的 heuristic）
57:目标：让拆解稳定、可复用、可验收，而不是“想当然”。
79:1.4 分发策略（Routing Policy）
108:目标：给你一个“能跑起来”的最小系统：DAG 任务、队列、worker、证据、验收。
111:2.1 目录结构（强目录骨架）

## 计划原文摘录
1) 任务拆解与任务分发方案（Process + Data Model）
1.1 核心目标

把宿主指令（用户/系统）变成可执行的任务 DAG（有依赖、有验收标准）。

分发到不同 worker（工具/子 agent/服务），并能重试、降级、回滚。

全流程可审计（为什么这么拆、为什么这么派、为什么这么判定完成）。

1.2 关键对象（建议最少字段）
Goal（顶层目标）

goal_id

statement：宿主原始目标

constraints：硬约束（时间/格式/安全/成本/禁止项）

definition_of_done：完成判据（DoD）

Task（最小可执行单元）

task_id

type：plan | research | compute | write | code | verify | review | publish

input_contract：输入契约（字段、类型、来源）

output_contract：输出契约（字段、类型、质量门槛）

acceptance_tests：验收测试（断言/检查项/示例）

dependencies：依赖 task_id 列表

tool_requirements：需要工具/权限

risk_level：low|med|high

fallbacks：失败降级策略

WorkItem（调度执行载体）

task_id

attempt

assigned_to：worker 名称

lease_until：租约（避免重复执行）

status：queued|running|blocked|failed|done

artifacts：产物引用（文件/表/日志/证据）

1.3 拆解规则（可执行的 heuristic）

目标：让拆解稳定、可复用、可验收，而不是“想当然”。

先写 DoD，再拆任务

DoD 必须可测：输出结构、数量、质量阈值、引用证据、边界条件。

任务拆到“单一主工具/单一主技能”

一个 task 尽量只依赖 1 个主要工具（或 1 个子 agent 能力），否则后续排查困难。

每个 task 都要自带验收测试

验收不靠“感觉”。至少：结构校验 + 关键断言 + 失败示例。

先拆依赖，再拆并行

先确定关键路径（critical path），再把可并行的 research/verify 分出去。

对不确定性拆“探测任务”

不确定：先做 research/probe，产出清晰输入契约，再进入后续 code/write.

1.4 分发策略（Routing Policy）
Worker 分类

planner：只产出 DAG 与契约

researcher：检索/资料整理（带引用）

implementer：写代码/配置

tester：写测试、跑用例、做覆盖率

reviewer：审查（安全、风格、架构、边界）

publisher：产物汇总、格式化输出

路由规则（简单可落地）

type=plan -> planner

type=research -> researcher

type=code -> implementer + 依赖 tester

risk=high -> 强制 reviewer + 双重验证

verify/review 永远不与 implement 同 worker（避免自证）

2) 一套代码实现（可落地骨架，Python + FastAPI + Redis 可选）

目标：给你一个“能跑起来”的最小系统：DAG 任务、队列、worker、证据、验收。
不写花哨框架，保证清晰可扩展。

2.1 目录结构（强目录骨架）
agent_orchestrator/
  README.md
  pyproject.toml
  src/
    orchestrator/
      __init__.py
      api.py
      models.py
      planner.py
      router.py
      executor.py
      validators.py
      store.py
      workers/
        __init__.py
        base.py
        planner_worker.py
        implementer_worker.py
        tester_worker.py
        reviewer_worker.py
      tools/
        __init__.py
        tool_registry.py
        shell_tool.py
      runtime/
        __init__.py
        queue.py
        scheduler.py
        locks.py
  tests/
    test_planner.py
    test_dag.py
    test_acceptance.py

2.2 关键模块代码（最小可用实现）

下面代码是完整骨架（可复制）。依赖：fastapi, pydantic, uvicorn。
队列先用内存实现；后续可替换 Redis/RQ/Celery。

# src/orchestrator/models.py
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

TaskType = Literal["plan", "research", "compute", "write", "code", "verify", "review", "publish"]
Status = Literal["queued", "running", "blocked", "failed", "done"]

class AcceptanceTest(BaseModel):
    name: str
    kind: Literal["schema", "assert", "example"]
    rule: Dict[str, Any]  # e.g. {"must_contain": ["foo"], "min_items": 5}

class Task(BaseModel):
    task_id: str
    type: TaskType
    title: str
    input_contract: Dict[str, Any] = Field(default_factory=dict)
    output_contract: Dict[str, Any] = Field(default_factory=dict)
    acceptance_tests: List[AcceptanceTest] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    tool_requirements: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "med", "high"] = "low"
    fallbacks: List[Dict[str, Any]] = Field(default_factory=list)

class Goal(BaseModel):
    goal_id: str
    statement: str
    constraints: Dict[str, Any] = Field(default_factory=dict)
    definition_of_done: Dict[str, Any] = Field(default_factory=dict)
