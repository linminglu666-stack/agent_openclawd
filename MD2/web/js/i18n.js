// i18n.js - 中文本地化资源包
export const messages = {
    'zh-CN': {
        views: {
            dashboard: '态势感知',
            agent_pool: '资源池管理',
            orchestrator: '编排中心',
            governance: '治理与审计',
            memory_hub: '记忆中心',
            growth_loop: '成长循环',
            eval_gate: '评估门禁',
            tracing: '追踪探索',
            console_config: '控制台设置'
        },
        status: {
            running: '运行中',
            idle: '空闲',
            error: '异常',
            pending: '等待中',
            stopped: '已停止'
        },
        copilot: {
            placeholder: '输入指令，如“扩容 Agent 池”...',
            welcome: '你好！我是 OpenClaw-X 智能副驾驶。我可以帮你管理集群、诊断问题或编排工作流。',
            thinking: '思考中...',
            actions: {
                approve: '批准',
                reject: '拒绝',
                retry: '重试',
                view_logs: '查看日志'
            }
        },
        dashboard: {
            cpu_usage: 'CPU 使用率',
            memory_usage: '内存使用率',
            active_agents: '活跃 Agent',
            pending_tasks: '堆积任务',
            health_score: '健康评分'
        },
        governance: {
            pending_approvals: '待审批事项',
            audit_logs: '审计日志',
            approver: '审批人',
            risk_score: '风险分',
            reason: '申请理由'
        }
    }
};

export const i18n = {
    locale: 'zh-CN',
    t(key) {
        const keys = key.split('.');
        let value = messages[this.locale];
        for (const k of keys) {
            value = value?.[k];
        }
        return value || key;
    }
};
