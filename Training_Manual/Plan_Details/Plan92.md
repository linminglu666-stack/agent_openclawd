# Plan92 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan92_Skills_Architecture_Stack.md
- 主计划标题：# Plan92 技能型方案：架构导向 Skill 体系（36个，含布设上限）

## 计划原文摘录
# Plan92 技能型方案：架构导向 Skill 体系（36个，含布设上限）

## 1. 目标
- 基于现有架构构建标准化技能体系，提升可复用性与执行质量。

## 2. 布设上限（强约束）
- Skill 总数上限：`36`。
- 同时激活上限：`12`。
- 高成本 Skill（深度推理/大检索）同时激活上限：`4`。
- 实验 Skill 上限：`6`（必须可一键回滚）。

## 3. Skill 清单（36）
1. Skill-01 指令解析与任务卡生成
2. Skill-02 DAG 任务拆解
3. Skill-03 依赖拓扑与并行规划
4. Skill-04 Run 策略选择
5. Skill-05 NodeRun 失败恢复
6. Skill-06 进度汇报生成
7. Skill-07 完成总结生成
8. Skill-08 证据编号与引用绑定
9. Skill-09 覆盖率闸门校验
10. Skill-10 证据闸门校验
11. Skill-11 可复现闸门校验
12. Skill-12 Delta 变更记录
13. Skill-13 记忆城堡写入
14. Skill-14 记忆冲突聚类
15. Skill-15 记忆检索预算分配
16. Skill-16 知识图谱路径召回
17. Skill-17 语义缓存命中
18. Skill-18 缓存失效策略
19. Skill-19 模型路由决策
20. Skill-20 成本预算守门
21. Skill-21 风险识别与分级
22. Skill-22 Prompt Injection 防护
23. Skill-23 RBAC 审计增强
24. Skill-24 插件权限校验
25. Skill-25 插件健康巡检
26. Skill-26 联网搜索多源聚合
27. Skill-27 来源可信度评估
28. Skill-28 网页证据抽取
29. Skill-29 游戏策划需求澄清
30. Skill-30 机制循环设计
31. Skill-31 数值平衡草案
32. Skill-32 关卡节奏分析
33. Skill-33 用户行为假设建模
34. Skill-34 经济系统风控
35. Skill-35 复盘与策略学习
36. Skill-36 自动优化建议生成

## 4. 生命周期
- Draft -> Trial -> Stable -> Deprecated。
- Trial 超过 14 天未达标自动下线。

## 5. 验收
- 每个 Skill 绑定输入/输出契约、质量门、成本上限。
