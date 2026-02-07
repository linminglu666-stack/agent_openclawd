# Plan99 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan94_593_GameDesign_Training_Pack.md
- 同步策略：逐条抽取，不使用通用模板。

## 计划正文
## Plan99
- 类型：进化型
- 主题域：核心循环
- 能力维度：反例检验
- 目标：在“核心循环”场景下完成“反例检验”能力建设，输出可复用方法与稳定结果。
- 评判指标：关键反例发现率>=80%，线上回退<=3%
- 要做什么：生成反例集并执行冲突/边界压力测试
- 做到什么程度：能提前发现脆弱点并阻断上线风险
- 持久化内容：
  - 学习产物：
    - memory_castle/workshop/plan_99_summary.md
    - memory_castle/workshop/plan_99_lessons.json
  - 证据数据：
    - evidence/plan_99/cases.jsonl
    - evidence/plan_99/metrics.json
  - 结构索引：
    - kg/plan_99_nodes_edges.json
    - index/plan_99_keywords.json
  - 审计与复盘：
    - audit/plan_99_run.log
    - review/plan_99_retro.md
