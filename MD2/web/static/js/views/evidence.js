
export default {
    render() {
        return `
            <div class="view-evidence">
                <h1>Evidence Explorer</h1>
                <div class="filters">
                    <input type="text" id="evidence-trace-id" placeholder="Filter by Trace ID">
                    <button id="btn-evidence-search">Search</button>
                </div>
                <table id="evidence-table">
                    <thead>
                        <tr>
                            <th>Evidence ID</th>
                            <th>Trace ID</th>
                            <th>Type</th>
                            <th>Hash (SHA256)</th>
                            <th>Content</th>
                            <th>Created</th>
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
        const loadEvidence = async (traceId = '') => {
            if (!traceId) return;
            const res = await window.api.get(`/v1/evidence?trace_id=${traceId}`);
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (!res.evidence || res.evidence.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No evidence found</td></tr>';
                return;
            }

            res.evidence.forEach(ev => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><small>${ev.evidence_id}</small></td>
                    <td>${ev.trace_id}</td>
                    <td>${ev.type}</td>
                    <td><small>${ev.hash.substring(0, 16)}...</small></td>
                    <td><pre style="max-height:100px;">${JSON.stringify(ev.content, null, 2)}</pre></td>
                    <td>${new Date(ev.created_at * 1000).toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });
        };

        el.querySelector('#btn-evidence-search').addEventListener('click', () => {
            const val = el.querySelector('#evidence-trace-id').value;
            this.lastTraceId = val;
            loadEvidence(val);
        });

        this.updateHandler = () => {
            if (this.lastTraceId) {
                loadEvidence(this.lastTraceId);
            }
        };
        window.addEventListener('update:evidence', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:evidence', this.updateHandler);
        }
    }
};
