
export default {
    render() {
        return `
            <div class="view-learning">
                <h1>Growth Loop (Knowledge)</h1>
                <div class="learning-grid" id="reports-container">
                    Loading reports...
                </div>
            </div>
        `;
    },

    async mount(el) {
        const loadReports = async () => {
            const res = await window.api.get('/v1/learning/reports?limit=50');
            const container = el.querySelector('#reports-container');
            if (!container) return;
            container.innerHTML = '';

            if (!res.reports || res.reports.length === 0) {
                container.innerHTML = '<div>No learning reports generated yet.</div>';
                return;
            }

            res.reports.forEach(rep => {
                const card = document.createElement('div');
                card.className = 'card';
                const content = rep.content || {};
                const newSkills = content.new_skills || [];
                const memoryDelta = content.memory_delta || [];
                const validation = content.validation || {};
                const rollback = content.rollback_info || {};

                card.innerHTML = `
                    <div class="card-header">
                        <strong>Report: ${rep.report_id}</strong>
                        <span class="meta">${new Date(rep.created_at * 1000).toLocaleString()}</span>
                    </div>
                    <div class="card-body">
                        <div>Agent: ${rep.agent_id}</div>
                        <div>Summary: ${content.summary || '-'}</div>
                        <details>
                            <summary>New Skills</summary>
                            <pre>${JSON.stringify(newSkills, null, 2)}</pre>
                        </details>
                        <details>
                            <summary>Memory Delta</summary>
                            <pre>${JSON.stringify(memoryDelta, null, 2)}</pre>
                        </details>
                        <details>
                            <summary>Validation</summary>
                            <pre>${JSON.stringify(validation, null, 2)}</pre>
                        </details>
                        <details>
                            <summary>Rollback Info</summary>
                            <pre>${JSON.stringify(rollback, null, 2)}</pre>
                        </details>
                    </div>
                `;
                container.appendChild(card);
            });
        };

        loadReports();

        this.updateHandler = () => {
            loadReports();
        };
        window.addEventListener('update:learning', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:learning', this.updateHandler);
        }
    }
};
