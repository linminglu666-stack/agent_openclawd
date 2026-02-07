# Plan21 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan21
- 主计划标题：Plan21 核心-指令型：OpenClawd 联网搜索能力（免费方案）

## 核心要点索引（来自主计划）
3:1. 目标
6:2. 免费优先方案

## 计划原文摘录
Plan21 核心-指令型：OpenClawd 联网搜索能力（免费方案）

1. 目标
- 为 OpenClawd 提供稳定、低成本、可降级的联网搜索能力。

2. 免费优先方案
- 主方案：SearXNG（自建/公共实例）+ 站点白名单抓取。
- 备选方案：Wikipedia API、DuckDuckGo Instant Answer API、公开 RSS/站点搜索。
- 降级方案：仅返回缓存结果与本地知识库答案，并显式声明联网失败。

3. 架构
- Search Adapter 统一接口：`search(query, recency, domains)`。
- 抓取与摘要分离：先检索链接，再抽取正文，再证据归档。
- 去重与可信度评分：域名信誉 + 时间新鲜度 + 多源交叉验证。

4. 持久化
- `search_cache`：query/hash/result/ttl/source_count。
- `search_evidence`：url/snapshot_hash/extracted_claims。
- 缓存 TTL：热点 1h，普通 24h。

5. 合规与安全
- 遵守 robots 与站点条款。
- 限流、超时、重试、熔断。

6. 验收
- 免费链路可用率达标。
- 查询结果带来源与时间戳。
