
export default {
    render() {
        return `
            <div class="view-queue">
                <h1>Queue Inspection</h1>
                <div class="filters">
                    <select id="filter-status">
                        <option value="">All Statuses</option>
                        <option value="created">Created</option>
                        <option value="claimed">Claimed</option>
                        <option value="running">Running</option>
                        <option value="acked">Acked</option>
                        <option value="failed">Failed</option>
                    </select>
                    <button id="btn-refresh-queue">Refresh</button>
                </div>
                <table id="queue-table">
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Agent</th>
                            <th>Created</th>
                            <th>Payload</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
    },

    async mount(el) {
        const loadQueue = async () => {
            const status = el.querySelector('#filter-status').value;
            const url = status ? `/v1/work-items?status=${status}&limit=100` : '/v1/work-items?limit=100';
            const res = await window.api.get(url);
            const tbody = el.querySelector('tbody');
            tbody.innerHTML = '';
            
            if (!res.work_items || res.work_items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No items found</td></tr>';
                return;
            }

            res.work_items.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.task_id}</td>
                    <td><span class="status-badge ${item.status}">${item.status}</span></td>
                    <td>${item.priority}</td>
                    <td>${item.agent_id || '-'}</td>
                    <td>${new Date(item.created_at * 1000).toLocaleString()}</td>
                    <td><pre>${JSON.stringify(item.payload, null, 2)}</pre></td>
                `;
                tbody.appendChild(tr);
            });
        };

        el.querySelector('#btn-refresh-queue').addEventListener('click', loadQueue);
        el.querySelector('#filter-status').addEventListener('change', loadQueue);
        
        loadQueue();

        this.updateHandler = () => {
            loadQueue();
        };
        window.addEventListener('update:queue', this.updateHandler);
    },

    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:queue', this.updateHandler);
        }
    }
};
