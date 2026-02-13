
export default {
    render() {
        return `
            <div class="view-agents">
                <h1>Infrastructure (Agents)</h1>
                <div class="stats-summary" id="agents-stats">
                    Loading stats...
                </div>
                <table id="agents-table">
                    <thead>
                        <tr>
                            <th>Agent ID</th>
                            <th>Status</th>
                            <th>Health (CPU/Mem)</th>
                            <th>Queue</th>
                            <th>Last Seen</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="5">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
    },

    async mount(el) {
        const loadAgents = async () => {
            const res = await window.api.get('/v1/agents?limit=50');
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (!res.agents || res.agents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No agents found</td></tr>';
                el.querySelector('#agents-stats').textContent = '0 Active Agents';
                return;
            }

            const now = Date.now() / 1000;
            let activeCount = 0;

            res.agents.forEach(agent => {
                const isAlive = (now - agent.last_seen) < 30; // 30s threshold
                if (isAlive) activeCount++;
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="status-dot ${isAlive ? 'online' : 'offline'}"></span>
                            ${agent.agent_id}
                        </div>
                    </td>
                    <td>${agent.status}</td>
                    <td>
                        <div class="resource-bar">
                            <div class="bar-fill" style="width:${agent.cpu}%"></div>
                            <span class="bar-text">CPU: ${agent.cpu}%</span>
                        </div>
                        <div class="resource-bar">
                            <div class="bar-fill" style="width:${agent.mem}%"></div>
                            <span class="bar-text">Mem: ${agent.mem}%</span>
                        </div>
                    </td>
                    <td>${agent.queue_depth}</td>
                    <td>${new Date(agent.last_seen * 1000).toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });

            el.querySelector('#agents-stats').textContent = `${activeCount} Online / ${res.agents.length} Total`;
        };

        loadAgents();

        this.updateHandler = () => {
            loadAgents();
        };
        window.addEventListener('update:agents', this.updateHandler);
    },

    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:agents', this.updateHandler);
        }
    }
};
