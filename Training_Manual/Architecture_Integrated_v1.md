# OpenClawd 统一架构思路文档（整体框架 v7）

## 1. 范围
- 覆盖 `Plan0~Plan620`。
- 目标：用“先文档后编码、先验收后推进”的方式降低实现 Bug 风险。

## 2. Soul 优先级
- 上位计划：`Plan0`。
- 所有开发执行必须先满足 Soul 对齐。

## 3. 开发搬运体系（新增）
- 开发索引：`Training_Manual/DEV_PLAN_INDEX.md`
- 代码搬运说明书：`Training_Manual/OpenClawd_Development_Handbook.md`
- 开发计划集：`Training_Manual/Dev_Plans/Plan595~Plan620.md`

## 4. 新开发层（Plan595~Plan620）
1. Plan595~599：规范、脚手架、配置、模型、存储
2. Plan600~607：核心服务（调度、编排、worker、记忆、图谱、搜索、插件）
3. Plan608~612：BFF、安全审计、SSE、可观测、测试门禁
4. Plan613~617：部署恢复、备份回滚、CI、一键启动
5. Plan618~620：缺陷治理、发布检查、运维手册

## 5. 训练体系
- Plan94~Plan593：500条不重复训练计划（含持久化内容）。
- Plan594：边界与成长闭环统筹。

## 6. 分阶段执行顺序（v7）
1. Stage-0：Plan0 Soul
2. Stage-1：Plan4/5 + 合同文档
3. Stage-2：Plan17/18/19/16/20/21
4. Stage-3：Plan22/23/24/26/27/28
5. Stage-4：Plan2/25/30/6/7
6. Stage-5：Plan29/91/92
7. Stage-6：Plan93 + Plan31~90
8. Stage-7：Plan94~593
9. Stage-8：Plan594
10. Stage-9（开发搬运层）：Plan595~620

## 7. 执行入口
- `Training_Manual/OpenClawd_Development_Handbook.md`
- `Training_Manual/Plan_Details/`
- `Training_Manual/Executable_List`
