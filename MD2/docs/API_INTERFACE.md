# OpenClaw-X API Reference

## 1. 基础约定 (Conventions)

*   **Base URL**: `/api/v1` (Default) - Configurable in Console
*   **Authentication**: Bearer Token
*   **Content-Type**: `application/json`

## 2. 核心接口 (Core APIs)

### 2.1 Agents
*   `GET /agents`: List all agents with status and load.
*   `POST /agents/scale`: Request scaling of agent pool.
    ```json
    { "target": 10, "reason": "load_spike" }
    ```

### 2.2 Tracing (Visualization)
*   `GET /traces`: List recent traces.
*   `GET /traces/{id}`: Get full trace details including Decision Tree and Waterfall data.
    *   **Response**:
        ```json
        {
          "trace_id": "tr-123",
          "waterfall": { ... },
          "decision_tree": { "nodes": [...], "edges": [...] }
        }
        ```

### 2.3 Dashboard
*   `GET /dashboard/metrics`: Real-time system metrics (CPU, Memory, Active Agents).

## 3. Mock Configuration (Console Config)

The following parameters can be adjusted in real-time via the Console Config panel:

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `mockLatency` | int | 0-5000ms | Simulates network delay globally. |
| `mockErrorRate` | int | 0-100% | Simulates random API failures (500 Internal Error). |
| `agentCount` | int | 1-100 | Controls the size of the simulated agent cluster. |

## 4. Web Architecture

### 4.1 Tech Stack
*   **Framework**: Vue 3 (ES Modules)
*   **State Management**: Reactive Store (`store.js`)
*   **Visualization**: ECharts + D3.js
*   **Styling**: Tailwind CSS

### 4.2 Key Modules
*   **ConsoleConfig**: The control center for the console itself.
*   **TracingViewer**: D3-based visualization of complex reasoning chains.
*   **Copilot**: Context-aware AI assistant with plugin support.
