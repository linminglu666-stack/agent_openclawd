// api.js - BFF API Client
import { store } from './store.js';

const BASE_URL = '/v1';

// --- Mock Reasoning Engine ---
// This simulates the backend LLM logic to make the demo interactive
const mockReasoning = async (messages, context, onChunk) => {
    const lastMsg = messages[messages.length - 1].content.toLowerCase();
    let response = "";
    
    // 1. Analyze Intent
    if (context.view === 'agent_pool') {
        if (lastMsg.includes('scale') || lastMsg.includes('扩容')) {
            response = "检测到 Agent 池当前负载为 **42%**。建议扩容到 15 个节点以应对即将到来的流量高峰。\n\n<action>{\"type\":\"approve\",\"title\":\"申请扩容至 15 节点\",\"reason\":\"负载预测 > 80%\"}</action>";
        } else if (lastMsg.includes('stop') || lastMsg.includes('停')) {
            response = "正在停止指定的 Agent... \n\n已生成审计日志: `Action: StopAgent`. 请在 Governance 页面查看详情。";
        } else if (lastMsg.includes('log') || lastMsg.includes('日志')) {
            response = "正在检索最近 1 小时的日志...\n\n发现 3 个异常堆栈：\n- `ConnectionTimeout` at 10:05\n- `OOMKilled` at 10:12\n\n建议检查内存限制配置。";
        } else {
            response = "我是 Agent 资源管理员。您可以让我扩容集群、重启节点或查询日志。";
        }
    } 
    else if (context.view === 'governance') {
        if (lastMsg.includes('approve') || lastMsg.includes('批')) {
            response = "已批准该请求。系统将自动执行后续部署流程。\n\n<action>{\"type\":\"view_logs\",\"title\":\"查看部署进度\"}</action>";
        } else if (lastMsg.includes('risk') || lastMsg.includes('风险')) {
            response = "当前系统整体风险评分为 **Low (0.2)**。但在过去 24 小时内拦截了 5 次高危操作尝试。\n\n<chart>{\"radar\":{\"indicator\":[{\"name\":\"Auth\",\"max\":100},{\"name\":\"Data\",\"max\":100},{\"name\":\"Network\",\"max\":100}]},\"series\":[{\"type\":\"radar\",\"data\":[{\"value\":[90,80,95],\"name\":\"Risk Score\"}]}]}</chart>";
        } else {
            response = "这里是审计中心。我可以帮您快速审批请求或查询历史操作记录。";
        }
    }
    else {
        // Default / Dashboard
        if (lastMsg.includes('status') || lastMsg.includes('状态')) {
            response = `系统当前运行正常。\n- CPU: **${store.metrics.cpu}%**\n- Active Agents: **${store.metrics.activeAgents}**\n\n所有核心服务均在线。`;
        } else if (lastMsg.includes('chart') || lastMsg.includes('图')) {
            response = "这是最近的系统负载趋势图：\n\n<chart>{\"xAxis\":{\"type\":\"category\",\"data\":[\"10:00\",\"10:05\",\"10:10\",\"10:15\"]},\"yAxis\":{\"type\":\"value\"},\"series\":[{\"data\":[30,45,60,55],\"type\":\"line\",\"smooth\":true}]}</chart>";
        } else {
            response = "你好！我是 OpenClaw-X 智能助手。请问有什么可以帮您？我可以协助管理集群、审批请求或诊断故障。";
        }
    }

    // Simulate Streaming
    const chunks = response.split(/(.{1,5})/g).filter(Boolean); // Split into small chunks
    for (const chunk of chunks) {
        await new Promise(r => setTimeout(r, 30 + Math.random() * 50)); // Random typing delay
        onChunk(chunk);
    }
};

export const api = {
    // REST API Wrapper
    async get(endpoint, params = {}) {
        try {
            const url = new URL(BASE_URL + endpoint, window.location.origin);
            Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
            const res = await fetch(url);
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            return await res.json();
        } catch (e) {
            console.warn(`GET ${endpoint} failed, falling back to mock if available`, e);
            return {};
        }
    },

    async post(endpoint, data = {}) {
        try {
            const res = await fetch(BASE_URL + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            return await res.json();
        } catch (e) {
            console.error(`POST ${endpoint} failed`, e);
            return {};
        }
    },

    // Entropy Governance API
    async getEntropyMetrics() {
        return this.get('/governance/entropy/metrics');
    },

    async getEntropyHistory() {
        return this.get('/governance/entropy/history');
    },

    async getEntropyConfig() {
        return this.get('/governance/entropy/config');
    },

    async updateEntropyConfig(config) {
        return this.post('/governance/entropy/config', config);
    },

    // SSE Stream
    initSSE() {
        // Mock SSE
        return {
            addEventListener: () => {},
            close: () => {}
        };
    },

    // Chat Stream (Using Mock Engine)
    async chatStream(messages, context, onChunk, onDone) {
        try {
            // In real app: fetch from backend
            // Here: use mock engine
            await mockReasoning(messages, context, onChunk);
            if (onDone) onDone();
        } catch (err) {
            console.error("Chat Error:", err);
            if (onChunk) onChunk(`\n\n[System Error: ${err.message}]`);
            if (onDone) onDone();
        }
    }
};
