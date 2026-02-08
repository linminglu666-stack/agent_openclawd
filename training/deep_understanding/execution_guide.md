# 深度理解训练执行指南 v5.0

## 系统特性

- **防造假**: 每个任务必须使用真实模型推理
- **最高思考**: 启用 `thinking=high` 模式
- **深度理解**: 50轮渐进式理解深化
- **记忆整合**: 结果存入记忆系统

## 执行方式

### 方法1: 使用 sessions_spawn (推荐)

对每个训练任务，使用以下命令创建子代理：

```bash
# 示例：执行 Plan002 第1轮训练
openclaw sessions spawn --task "# 深度理解训练 - Plan002: 记忆与上下文

**训练轮次**: 1/50
**主题**: human-like memory architecture with episodic/semantic/working memory layers

## 当前深度问题
What are the fundamental differences between human memory types?

## 训练要求

1. **深度分析**: 使用最高级别的推理能力，深入分析这个问题
2. **多角度思考**: 从技术、认知、哲学、实践等多个角度思考
3. **批判性思维**: 质疑假设，考虑反例，识别局限性
4. **联系整合**: 将理解与已有知识联系，形成网络

## 输出格式

请以结构化方式输出你的深度理解：

```
## 核心洞察
[1-2句话概括最核心的理解]

## 深度分析
[详细分析，包含推理过程]

## 关键概念
- 概念1: 解释
- 概念2: 解释
...

## 实践启示
[如何在实际系统中应用这个理解]

## 待探索问题
[这个理解引出的新问题]
```

**重要**: 这是一个真实的训练过程，不是模拟。请进行真正的深度思考。" --thinking=high
```

### 方法2: 批量执行脚本

```python
import asyncio
from openclaw import sessions_spawn

async def execute_training_task(task):
    result = await sessions_spawn(
        task=task['prompt'],
        thinking='high',
        label=task['task_id']
    )
    # 保存结果到记忆系统
    save_to_memory(task, result)
```

## 任务清单

总任务数: 300
预计总时间: 15.0 小时

### Plan列表

- **Plan002**: 记忆与上下文 (50轮)
- **Plan006**: 任务管理 (50轮)
- **Plan007**: 自主学习 (50轮)
- **Plan022**: 错误模式进化 (50轮)
- **Plan025**: 知识图谱 (50轮)
- **Plan030**: 记忆城堡 (50轮)

## 防造假验证

每个训练结果必须包含：
1. 真实的推理token消耗
2. 思考过程的时间戳
3. 独特的见解（非模板化）
4. 与主题的深度关联

## 记忆整合

训练完成后，将理解整合到：
- `memory/deep_understanding_P{plan_id}.md`
- `MEMORY.md` 的长期记忆区
- SOUL.md 的认知模型更新

---
*深度理解训练系统 v5.0*
