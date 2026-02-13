
export default {
    render() {
        return `
            <div class="view-dashboard">
                <h1>System Dashboard</h1>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Active Runs</h3>
                        <div class="value" id="dash-active-runs">-</div>
                    </div>
                    <div class="stat-card">
                        <h3>Pending Approvals</h3>
                        <div class="value" id="dash-pending-approvals">-</div>
                    </div>
                    <div class="stat-card">
                        <h3>Active Schedules</h3>
                        <div class="value" id="dash-schedules">-</div>
                    </div>
                </div>
                <div class="health-status">
                    <h3>System Health</h3>
                    <div id="health-metrics">Checking...</div>
                </div>
            </div>
        `;
    },

    async mount(el) {
        const loadDashboard = async () => {
            try {
                const health = await window.api.get('/healthz');
                const healthEl = document.getElementById('health-metrics');
                if (healthEl) {
                    healthEl.innerHTML = `
                        <pre>${JSON.stringify(health, null, 2)}</pre>
                    `;
                }

                const runs = await window.api.get('/v1/runs?limit=100');
                const activeRuns = (runs.runs || []).filter(r => r.status === 'pending' || r.status === 'running').length;
                const activeRunsEl = document.getElementById('dash-active-runs');
                if (activeRunsEl) activeRunsEl.textContent = activeRuns;

                const approvals = await window.api.get('/v1/approvals?status=pending');
                const approvalsEl = document.getElementById('dash-pending-approvals');
                if (approvalsEl) approvalsEl.textContent = (approvals.approvals || []).length;

                const schedules = await window.api.get('/v1/schedules');
                const activeScheds = (schedules.schedules || []).filter(s => s.enabled).length;
                const schedEl = document.getElementById('dash-schedules');
                if (schedEl) schedEl.textContent = activeScheds;
            } catch (e) {
                console.error(e);
            }
        };

        loadDashboard();

        this.updateHandler = () => {
            loadDashboard();
        };
        window.addEventListener('update:dashboard', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:dashboard', this.updateHandler);
        }
    }
};
