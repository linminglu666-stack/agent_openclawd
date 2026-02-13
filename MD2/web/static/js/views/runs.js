
export default {
    render() {
        return `
            <div class="view-runs">
                <h1>Runs</h1>
                <table id="runs-table">
                    <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Workflow ID</th>
                            <th>Status</th>
                            <th>Started</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="5">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div id="run-details-modal" class="modal" style="display:none;">
                <div class="modal-content" style="max-width: 800px;">
                    <div class="modal-header">
                        <h2>Run Details</h2>
                        <button class="close-modal">×</button>
                    </div>
                    <div id="run-timeline" class="timeline">
                        Loading...
                    </div>
                    <h3>Raw Data</h3>
                    <pre id="run-raw" style="max-height: 200px; overflow:auto;"></pre>
                </div>
            </div>
        `;
    },

    async mount(el) {
        const modal = el.querySelector('#run-details-modal');
        const timeline = el.querySelector('#run-timeline');
        const raw = el.querySelector('#run-raw');
        
        // Close modal logic
        el.querySelector('.close-modal').addEventListener('click', () => {
            modal.style.display = 'none';
        });

        const loadRuns = async () => {
            const res = await window.api.get('/v1/runs?limit=50');
            const tbody = el.querySelector('tbody');
            if (!tbody) return; // Unmounted
            
            tbody.innerHTML = '';
            
            (res.runs || []).forEach(run => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${run.run_id}</td>
                    <td>${run.workflow_id}</td>
                    <td><span class="status-${run.status}">${run.status}</span></td>
                    <td>${new Date(run.started_at * 1000).toLocaleString()}</td>
                    <td>
                        <button class="btn-details" data-id="${run.run_id}">Trace</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Bind buttons
            el.querySelectorAll('.btn-details').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    modal.style.display = 'block';
                    timeline.innerHTML = 'Loading trace...';
                    
                    const details = await window.api.get(`/v1/runs/${id}`);
                    raw.textContent = JSON.stringify(details, null, 2);
                    
                    // Render Timeline
                    timeline.innerHTML = '';
                    if (!details.nodes || details.nodes.length === 0) {
                        timeline.innerHTML = '<div class="timeline-item">No steps recorded yet.</div>';
                    } else {
                        // Sort by start time
                        const nodes = details.nodes.sort((a, b) => a.started_at - b.started_at);
                        nodes.forEach(node => {
                            const item = document.createElement('div');
                            item.className = `timeline-item ${node.status}`;
                            const duration = node.ended_at ? (node.ended_at - node.started_at).toFixed(2) + 's' : 'Running';
                            item.innerHTML = `
                                <strong>${node.node_id}</strong>
                                <span class="status-badge">${node.status}</span>
                                <div class="meta">
                                    Started: ${new Date(node.started_at * 1000).toLocaleTimeString()} (${duration})
                                </div>
                            `;
                            timeline.appendChild(item);
                        });
                    }
                });
            });
        };

        // Initial Load
        loadRuns();

        // Listen for updates
        this.updateHandler = () => {
            console.log('Reloading runs...');
            loadRuns();
        };
        window.addEventListener('update:runs', this.updateHandler);
    },

    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:runs', this.updateHandler);
        }
    }
};
