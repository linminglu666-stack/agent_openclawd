# Plan2 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan2
- 主计划标题：整体思路文档（最终版）

## 核心要点索引（来自主计划）
3:目标
119:2.1 MemoryUnit（原子记忆单元）
141:2.2 ContextPacket（上下文包）
159:2.3 S1 输出：DraftPack
177:2.4 S2 输出：ReviewPack
190:目标：在预算内生成可用草稿，同时产出“可被质疑”的结构化对象（Claims + Meta）。
222:目标：用明确规则决定是否升级到“质疑式慢思考”。

## 计划原文摘录
整体思路文档（最终版）

目标
用一套系统服务级别的“记忆 + 检索 + 上下文硬控”**模块，组合工作流来模拟不同厂商模型优势：

类 Claude：更强的“结论化/结构化上下文”

类 Kimi：更强的“长对话持续性 + 低污染记忆”

类 Gemini：更大的“可用上下文窗口”——但你要求**只取其 50%**作为工作窗口上限（避免推理/输出被挤压）

存储结构（公共 + 聊天独立，双模式）
真相源一律 append-only（只追加写），可审计、可回放、可重建索引。

global/（公共存储，可迁移第一性原理/长期原则）

principles/：原则（宪法层）与冲突裁决

stages/：按 scope 的阶段结论（可版本化）

tokenizer/：分词字典与自动词晋升事件

scopes/：固定字典映射（你要求“固定字典映射”，用 .taml）

index/：SQLite 倒排索引（派生物，可重建）

chats/<chat_folder>/（聊天独立存储，冻结聊天名）

memory/deltas.jsonl：每次压缩（delta）输出

memory/cold/*.jsonl：自动分类冷存（facts/decisions/open_threads/todo/conflicts/glossary）

memory/hot_context_versions.jsonl：热区上下文版本

分层记忆（强烈建议）
宪法层（Principles）：稳定原则、项目约束、不可违反项

阶段结论层（Stages）：最近一段时间的决策/结论（scope@vYYYYMMDD-NN，可版本化）

原始材料层（Raw/Evidence）：讨论过程、争论、草案、证据片段（仅必要时检索）

每次注入模型：优先 宪法 + 最近阶段结论 + 少量证据片段，其余通过多轮推理补齐。

上下文预算硬控（要求）
设定 context_budget_chars（默认 18000，可按你模型窗口调整）

分配固定比例：

宪法 10%

阶段结论 50%

热区 + 证据 40%

再配合触发规则（delta/merge/trim）避免无上限膨胀

分类与路由（自动推断）
free_tags：自由标签（可多）

route_tag：7 大顶层标签唯一命中（系统/战斗/关卡/数值/叙事/美术/运营），用固定优先级打破并列

scope：固定字典映射（.taml），scope 决定写入哪个 stage

记忆污染控制（你要求的晋升规则）
原则晋升：

用户显式指定加入（user_forced）→ 立即晋升

否则：同义归一化规则出现 ≥ 3 次才自动晋升

原则分级：

加入后每出现 10 次升一级（L1–L10）

冲突处理（强制打断）：

同级互斥命中 → 直接打断输出冲突簇

同级时让使用者裁决（keep #k），其余默认 suppressed

性能/效率提升但不牺牲准确度
真相源：append-only JSONL（正确性基准）

派生物：

增量快照（只处理新增行）

SQLite 倒排索引（快速检索）

严格 freshness check：索引不新鲜就回退扫快照/真相（准确度优先）
输入 / 输出契约
输入 Input

UserQuery：用户需求/问题

MemoryStore：本地库（分层存储 + 元数据）

Policy：宪法层原则/硬约束（最高优先级）

Budget：

context_token_budget：上下文预算

evidence_token_budget：证据注入预算（仅慢思考时扩大）

输出 Output

默认输出：FinalAnswer

可选输出（仅在必要时外显）：

OpenQuestions：仍需用户补充的最少必要信息

Assumptions：为了不给出无依据断言而做的条件化前提

Alternatives：冲突无法裁决时的分支方案

2) 数据结构
2.1 MemoryUnit（原子记忆单元）

建议字段（可按你的库简化）：

id

type：constitution | decision | semantic | episodic | snippet

content：原子陈述（尽量“一条规则/一个事实/一个结论”）

scope：适用范围（模块/系统/关卡/版本/对象）

version：版本号或生效区间（可空，但推荐）

priority：hard | soft | ref

confidence：0~1

provenance：来源（文档/会议/用户明确指令/日期）

tags：关键词/结构化标签

2.2 ContextPacket（上下文包）

固定结构（建议保持稳定）：

Task：任务目标（把 UserQuery 改写成可执行交付）

HardConstraints：宪法层 + 强约束决策

SoftConstraints：偏好/风格/口径

RelevantFacts：相关设定/事实（semantic）

RecentDecisions：近期决策（decision）

EvidenceSnippets（可选）：证据片段（snippet，慢思考时注入）

Risks：风险点/不确定点（由 S1 产出）

2.3 S1 输出：DraftPack

Draft：草稿正文

Claims[]：可核验主张列表（每条一句话）

DraftMeta：

confidence：0~1

conflict_count：0+

missing_critical_info：布尔 + 列表

risk_level：low | mid | high

complexity：simple | mid | complex

2.4 S2 输出：ReviewPack

Questions[]：质疑清单（先产出）

