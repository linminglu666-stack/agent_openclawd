
export default {
    render() {
        return `
            <div class="view-workflows">
                <h1>Workflows</h1>
                <div class="actions">
                    <button id="btn-create-workflow">Create Workflow</button>
                </div>
                <table id="workflows-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Version</th>
                            <th>Created At</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="4">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div id="create-workflow-modal" class="modal" style="display:none;">
                <div class="modal-content">
                    <h2>Create Workflow</h2>
                    <textarea id="workflow-json" rows="10" cols="50" placeholder='{"workflow_id": "my-wf", "dag": {...}}'></textarea>
                    <div class="modal-actions">
                        <button id="btn-save-workflow">Save</button>
                        <button id="btn-cancel-workflow" class="secondary">Cancel</button>
                    </div>
                </div>
            </div>
        `;
    },

    async mount(el) {
        const loadWorkflows = async () => {
            const res = await window.api.get('/v1/workflows?limit=50');
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            (res.workflows || []).forEach(wf => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${wf.workflow_id}</td>
                    <td>${wf.version}</td>
                    <td>${new Date(wf.created_at * 1000).toLocaleString()}</td>
                    <td>
                        <button class="btn-view" data-id="${wf.workflow_id}">View</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        };

        loadWorkflows();

        el.querySelector('#btn-create-workflow').addEventListener('click', () => {
            el.querySelector('#create-workflow-modal').style.display = 'block';
        });

        el.querySelector('#btn-cancel-workflow').addEventListener('click', () => {
            el.querySelector('#create-workflow-modal').style.display = 'none';
        });

        el.querySelector('#btn-save-workflow').addEventListener('click', async () => {
            const jsonStr = el.querySelector('#workflow-json').value;
            try {
                const data = JSON.parse(jsonStr);
                const res = await window.api.post('/v1/workflows', data);
                if (res.ok) {
                    window.App.toast('Workflow created successfully!', 'success');
                    el.querySelector('#create-workflow-modal').style.display = 'none';
                    loadWorkflows(); 
                } else {
                    window.App.toast('Error: ' + res.error, 'error');
                }
            } catch (e) {
                window.App.toast('Invalid JSON: ' + e.message, 'error');
            }
        });

        this.updateHandler = () => {
            loadWorkflows();
        };
        window.addEventListener('update:workflows', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:workflows', this.updateHandler);
        }
    }
};
