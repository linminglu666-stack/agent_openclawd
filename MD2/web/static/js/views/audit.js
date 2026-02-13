
export default {
    render() {
        return `
            <div class="view-audit">
                <h1>Audit Logs</h1>
                <div class="filters">
                    <input type="text" id="audit-trace-id" placeholder="Filter by Trace ID">
                    <button id="btn-audit-search">Search</button>
                </div>
                <table id="audit-table">
                    <thead>
                        <tr>
                            <th>Trace ID</th>
                            <th>Actor</th>
                            <th>Action</th>
                            <th>Resource</th>
                            <th>Result</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6">Enter Trace ID to search</td></tr>
                    </tbody>
                </table>
            </div>
        `;
    },

    async mount(el) {
        const loadLogs = async (traceId = '') => {
            const url = traceId ? `/v1/audit?trace_id=${traceId}` : '/v1/audit';
            const res = await window.api.get(url);
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (!res.audit || res.audit.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No logs found</td></tr>';
                return;
            }

            res.audit.forEach(log => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.trace_id}</td>
                    <td>${log.actor}</td>
                    <td>${log.action}</td>
                    <td>${log.resource}</td>
                    <td><pre>${JSON.stringify(log.result)}</pre></td>
                    <td>${new Date(log.timestamp * 1000).toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });
        };

        el.querySelector('#btn-audit-search').addEventListener('click', () => {
            const traceId = el.querySelector('#audit-trace-id').value;
            this.lastTraceId = traceId;
            loadLogs(traceId);
        });

        loadLogs();

        this.updateHandler = () => {
            loadLogs(this.lastTraceId || '');
        };
        window.addEventListener('update:audit', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:audit', this.updateHandler);
        }
    }
};
