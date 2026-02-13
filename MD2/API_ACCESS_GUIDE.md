# OpenClaw-X API 接入指南

本文档详细描述了 Web 前端如何与 OpenClaw-X BFF 服务进行交互，包括认证、智能对话流、管理接口及事件订阅。

## 1. 基础约定

*   **Base URL**: `/v1`
*   **Content-Type**: `application/json`
*   **Authentication**: Bearer Token
    ```http
    Authorization: Bearer <token>
    ```

## 2. 智能对话接口 (Copilot)

OpenClaw-X 兼容 OpenAI Chat Completion API 格式，并扩展了 `metadata` 用于上下文感知。

### 发起对话 (Stream Mode)

**Endpoint**: `POST /v1/chat/completions`

**Request**:
```json
{
  "model": "md2-reasoner-v1",
  "messages": [
    {"role": "user", "content": "Agent-001 为什么报错了？"}
  ],
  "stream": true,
  "metadata": {
    "view": "agent_pool",
    "selected": "agent-001"
  }
}
```

**Response (SSE Stream)**:
```text
data: {"id":"chat-123","choices":[{"delta":{"content":"根据日志分析，"}}]}

data: {"id":"chat-123","choices":[{"delta":{"content":"内存溢出导致。建议扩容。"}}]}

data: [DONE]
```

### Copilot 插件协议

AI 可能会在回复中嵌入 XML 标记来触发前端组件：

*   **操作卡片**: `<action>{"type":"approve","title":"批准"}</action>`
*   **图表渲染**: `<chart>{"xAxis":...}</chart>`

---

## 3. 实时事件流 (SSE)

前端应保持一个长连接以接收系统状态更新。

**Endpoint**: `GET /v1/events/stream`

**Events**:
*   `heartbeat`: 系统存活心跳 (每 30s)
*   `update:agents`: Agent 状态变更 (需刷新 Agent 列表)
*   `update:approvals`: 新增审批任务 (需刷新 Governance 页面)
*   `alert:system`: 系统级告警 (需弹出 Toast)

---

## 4. 管理接口 (Management API)

### 4.1 仪表盘
*   `GET /v1/dashboard/metrics`: 获取 CPU/Memory/Tasks 指标。
*   `GET /v1/dashboard/alerts`: 获取最近告警。

### 4.2 Agent 资源池
*   `GET /v1/agents`: 获取 Agent 列表。
    *   Query: `?status=running&limit=20`
*   `POST /v1/agents/scale`: 扩缩容操作。
    ```json
    { "target": 20, "reason": "Traffic spike" }
    ```

### 4.3 编排器
*   `GET /v1/workflows`: 获取工作流列表。
*   `POST /v1/workflows`: 创建/更新工作流 DAG。

### 4.4 治理与审批
*   `GET /v1/approvals`: 获取待审批列表。
*   `POST /v1/approvals/{id}/decide`: 审批决策。
    ```json
    { "decision": "approve", "comment": "Looks good" }
    ```

### 4.5 记忆中心
*   `GET /v1/memory/search`: 语义检索知识库。
    *   Query: `?q=deployment+protocol&layer=L3`

---

## 5. 错误处理

所有非 200 响应均包含标准错误体：

```json
{
  "ok": false,
  "error": "permission_denied",
  "message": "User 'guest' does not have permission to scale agents.",
  "trace_id": "tr-abc-123"
}
```

前端应根据 `error` 代码在 `i18n` 中查找对应的中文提示。
