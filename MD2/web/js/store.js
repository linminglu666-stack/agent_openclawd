// store.js - Global State & Mock Database
import { reactive } from 'vue';
import { format } from './utils/format.js';

// Mock Data Generators
const mockAgents = (count = 5) => {
    const agents = [
        { id: 'agent-001', name: 'Search Worker', status: 'running', icon: '🔍', tasks: 1240, uptime: '3d 4h', load: 45 },
        { id: 'agent-002', name: 'Reasoning Core', status: 'running', icon: '🧠', tasks: 85, uptime: '12h', load: 82 },
        { id: 'agent-003', name: 'Code Executor', status: 'idle', icon: '💻', tasks: 320, uptime: '1d 2h', load: 0 },
        { id: 'agent-004', name: 'Data Ingest', status: 'error', icon: '📥', tasks: 12, uptime: '4h', load: 0 },
        { id: 'agent-005', name: 'Report Gen', status: 'running', icon: '📊', tasks: 56, uptime: '5h', load: 23 },
    ];
    // Generate extra mock agents if count > 5
    for (let i = 5; i < count; i++) {
        agents.push({
            id: `agent-${String(i+1).padStart(3, '0')}`,
            name: `Worker Node ${i+1}`,
            status: Math.random() > 0.8 ? 'idle' : 'running',
            icon: '🤖',
            tasks: Math.floor(Math.random() * 500),
            uptime: '1h',
            load: Math.floor(Math.random() * 80)
        });
    }
    return agents;
};

const mockApprovals = () => [
    { id: 1, type: 'Scale Up', title: 'Request to scale Agent Pool to 20', description: 'Handling traffic spike detected in region us-east-1.', requester: 'AutoScaler', time: '10 mins ago', riskScore: 0.8 },
    { id: 2, type: 'Access', title: 'Grant admin access to user "bob"', description: 'Temporary access for debugging.', requester: 'Bob', time: '1 hour ago', riskScore: 0.9 },
    { id: 3, type: 'Deployment', title: 'Deploy Workflow v2.1', description: 'Critical bug fix for payment gateway.', requester: 'CI/CD', time: '2 hours ago', riskScore: 0.4 }
];

const mockAuditLogs = () => [
    { id: 1, time: '2023-10-27 10:00:01', user: 'admin', action: 'Login', resource: 'System' },
    { id: 2, time: '2023-10-27 10:05:23', user: 'AutoScaler', action: 'Scale', resource: 'AgentPool' },
    { id: 3, time: '2023-10-27 10:12:45', user: 'admin', action: 'Update', resource: 'Policy:Network' },
];

// Mock Trace Generator
const generateMockTrace = () => {
    const traceId = `tr-${Math.random().toString(36).substr(2, 8)}`;
    const startTime = Date.now() - Math.floor(Math.random() * 100000);
    const duration = Math.floor(Math.random() * 5000) + 500;
    
    // Construct a simple tree
    const rootSpan = {
        id: `sp-${Math.random().toString(36).substr(2, 6)}`,
        name: 'Root Task',
        type: 'thought',
        start: 0,
        duration: duration,
        children: []
    };
    
    // Add some children
    let currentOffset = 100;
    for (let i = 0; i < 3; i++) {
        const childDuration = Math.floor(duration / 4);
        rootSpan.children.push({
            id: `sp-${Math.random().toString(36).substr(2, 6)}`,
            name: ['Data Retrieval', 'Analysis', 'Generation'][i],
            type: ['tool', 'thought', 'action'][i],
            start: currentOffset,
            duration: childDuration,
            children: []
        });
        currentOffset += childDuration + 50;
    }

    return {
        id: traceId,
        name: `Trace ${traceId}`,
        startTime: startTime,
        duration: duration,
        status: Math.random() > 0.1 ? 'completed' : 'failed',
        root: rootSpan
    };
};

export const store = reactive({
    user: {
        id: 'admin',
        name: 'Administrator',
        roles: ['admin', 'operator']
    },
    token: 'mock-token-123',
    
    // Configuration State (Hot Reloadable)
    config: {
        mockLatency: 500, // ms
        mockErrorRate: 0, // 0-100%
        agentCount: 5,
        themeColor: '#3B82F6'
    },

    systemStatus: 'running',
    
    // Data State
    agents: mockAgents(5),
    approvals: mockApprovals(),
    auditLogs: mockAuditLogs(),
    traces: Array.from({ length: 10 }, generateMockTrace),
    workflows: [],
    metrics: {
        cpu: 42,
        activeAgents: 8,
        pendingTasks: 24,
        health: 98
    },
    
    // Entropy Governance
    entropy: {
        metrics: null, // { input: { score: 0.8, details: [...] }, evolution: ... }
        history: [], // [{ timestamp: ..., metrics: ... }]
        config: {
            input_threshold: 0.7,
            evolution_threshold: 0.7,
            observability_threshold: 0.7,
            structure_threshold: 0.7,
            behavior_threshold: 0.7,
            data_threshold: 0.7
        },
        alerts: []
    },

    // UI State
    notifications: [],
    loading: {
        agents: false,
        approvals: false,
        traces: false
    },

    // --- Actions ---

    // Config Actions
    updateConfig(key, value) {
        this.config[key] = value;
        // Hot reload logic
        if (key === 'agentCount') {
            this.agents = mockAgents(value);
            this.addNotification(`Agent count updated to ${value}`, 'success');
        }
        if (key === 'themeColor') {
            // Apply theme color (mock)
            document.documentElement.style.setProperty('--color-primary', value);
        }
    },

    setSystemStatus(status) {
        this.systemStatus = status;
    },
    
    addNotification(msg, type = 'info') {
        const id = Date.now();
        this.notifications.push({ id, msg, type });
        setTimeout(() => {
            const idx = this.notifications.findIndex(n => n.id === id);
            if (idx !== -1) this.notifications.splice(idx, 1);
        }, 3000);
    },

    // Core Logic: Interconnectivity
    
    logAudit(action, resource, user = 'admin') {
        const log = {
            id: Date.now(),
            time: format.datetime(new Date(), 'long'),
            user,
            action,
            resource
        };
        this.auditLogs.unshift(log);
        if (this.auditLogs.length > 50) this.auditLogs.pop();
    },

    triggerApproval(type, title, description, riskScore = 0.5) {
        const approval = {
            id: Date.now(),
            type,
            title,
            description,
            requester: this.user.name,
            time: 'Just now',
            riskScore
        };
        this.approvals.unshift(approval);
        this.addNotification(`New approval request: ${title}`, 'warning');
    },

    updateAgentStatus(agentId, status) {
        const agent = this.agents.find(a => a.id === agentId);
        if (agent) {
            const oldStatus = agent.status;
            agent.status = status;
            this.logAudit('UpdateStatus', `Agent:${agentId} (${oldStatus} -> ${status})`);
            this.metrics.activeAgents = this.agents.filter(a => a.status === 'running').length;
        }
    },

    setEntropyMetrics(metrics) {
        this.entropy.metrics = metrics;
        // Also update history if not present?
        // History should come from history API or be accumulated.
        // If we use real API, we might fetch history separately.
    },
    
    setEntropyHistory(history) {
        this.entropy.history = history;
    },

    async refreshEntropyData() {
        // Fallback or Mock
        this.generateMockEntropyData();
    },

    generateMockEntropyData() {
        const categories = ['input', 'evolution', 'observability', 'structure', 'behavior', 'data'];
        const metrics = {};
        let totalScore = 0;
        
        categories.forEach(cat => {
            const score = Math.random() * 0.5 + 0.3; // 0.3 - 0.8
            metrics[cat] = {
                score: parseFloat(score.toFixed(2)),
                details: []
            };
            totalScore += score;
        });
        
        this.entropy.metrics = {
            ...metrics,
            total_score: parseFloat((totalScore / 6).toFixed(2)),
            timestamp: new Date().toISOString()
        };
        
        // Add to history
        this.entropy.history.push({
            timestamp: new Date().toISOString(),
            metrics: this.entropy.metrics
        });
        
        if (this.entropy.history.length > 20) {
            this.entropy.history.shift();
        }
    },

    // Data Refreshers
    async refreshAgents() {
        this.loading.agents = true;
        try {
            // Simulate latency from config
            await new Promise(r => setTimeout(r, this.config.mockLatency));
            
            // Simulate random error
            if (Math.random() * 100 < this.config.mockErrorRate) {
                throw new Error('Random simulated network error');
            }

            // Simulate load fluctuation
            this.agents.forEach(a => {
                if (a.status === 'running') {
                    a.load = Math.min(100, Math.max(0, a.load + Math.floor(Math.random() * 20 - 10)));
                } else {
                    a.load = 0;
                }
            });
            this.metrics.activeAgents = this.agents.filter(a => a.status === 'running').length;
            this.metrics.cpu = Math.min(100, Math.max(10, this.metrics.cpu + Math.floor(Math.random() * 10 - 5)));
        } catch (e) {
            console.warn('Failed to fetch agents:', e);
            // Don't show toast for background refresh errors to avoid spamming
        } finally {
            this.loading.agents = false;
        }
    },
    
    async refreshApprovals() {
        this.loading.approvals = false;
    }
});
