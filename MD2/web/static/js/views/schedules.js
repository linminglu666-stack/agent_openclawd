
export default {
    render() {
        return `
            <div class="view-schedules">
                <h1>Schedules</h1>
                <table id="schedules-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Workflow ID</th>
                            <th>Enabled</th>
                            <th>Policy</th>
                            <th>Next Run</th>
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
        const loadSchedules = async () => {
            const res = await window.api.get('/v1/schedules?limit=50');
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            (res.schedules || []).forEach(sch => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${sch.id}</td>
                    <td>${sch.workflow_id}</td>
                    <td>
                        <input type="checkbox" ${sch.enabled ? 'checked' : ''} data-id="${sch.id}" class="toggle-enabled">
                    </td>
                    <td><pre>${JSON.stringify(sch.policy_json, null, 2)}</pre></td>
                    <td>${sch.next_fire_at ? new Date(sch.next_fire_at * 1000).toLocaleString() : '-'}</td>
                `;
                tbody.appendChild(tr);
            });

            el.querySelectorAll('.toggle-enabled').forEach(chk => {
                chk.addEventListener('change', async (e) => {
                    const id = e.target.dataset.id;
                    const enabled = e.target.checked;
                    try {
                        const res = await window.api.patch(`/v1/schedules/${id}`, { enabled });
                        if (!res.ok) {
                            window.App.toast('Failed to update: ' + res.error, 'error');
                            e.target.checked = !enabled;
                        } else {
                            window.App.toast(`Schedule ${enabled ? 'enabled' : 'disabled'}`, 'success');
                        }
                    } catch (err) {
                        console.error(err);
                        window.App.toast('Network error', 'error');
                        e.target.checked = !enabled;
                    }
                });
            });
        };

        loadSchedules();

        this.updateHandler = () => {
            loadSchedules();
        };
        window.addEventListener('update:schedules', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:schedules', this.updateHandler);
        }
    }
};
