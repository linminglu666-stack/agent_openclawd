
export default {
    render() {
        return `
            <div class="view-approvals">
                <h1>Approvals</h1>
                <table id="approvals-table">
                    <thead>
                        <tr>
                            <th>Approval ID</th>
                            <th>Task</th>
                            <th>Requester</th>
                            <th>Risk Score</th>
                            <th>Factors</th>
                            <th>Actions</th>
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
        const loadApprovals = async () => {
            const res = await window.api.get('/v1/approvals?status=pending');
            const tbody = el.querySelector('tbody');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (!res.approvals || res.approvals.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No pending approvals</td></tr>';
                return;
            }

            res.approvals.forEach(appr => {
                const tr = document.createElement('tr');
                
                const factors = appr.risk_factors || [];
                const factorsHtml = factors.map(f => {
                    const factor = f.factor ?? f.type ?? '';
                    const score = f.score ?? f.value ?? '';
                    const weight = f.weight ?? '';
                    if (factor || score || weight) {
                        return `
                            <div title="Weight: ${weight}">
                                • ${factor}: <strong>${score}</strong>
                            </div>
                        `;
                    }
                    return `<div><small>${JSON.stringify(f)}</small></div>`;
                }).join('');

                const riskClass = appr.risk_score > 80 ? 'risk-high' : (appr.risk_score > 50 ? 'risk-med' : 'risk-low');
                const requester = appr.requester || {};
                const requesterText = requester.user_id || requester.workflow_id || requester.run_id || '-';

                tr.innerHTML = `
                    <td><small>${appr.approval_id}</small></td>
                    <td>${appr.task_id}</td>
                    <td>${requesterText}</td>
                    <td class="${riskClass}"><strong>${appr.risk_score}</strong></td>
                    <td><small>${factorsHtml}</small></td>
                    <td>
                        <button class="btn-approve" data-id="${appr.approval_id}">Approve</button>
                        <button class="btn-reject" data-id="${appr.approval_id}" class="secondary">Reject</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Actions
            el.querySelectorAll('.btn-approve').forEach(btn => {
                btn.addEventListener('click', () => this.decide(btn.dataset.id, 'approved'));
            });
            el.querySelectorAll('.btn-reject').forEach(btn => {
                btn.addEventListener('click', () => this.decide(btn.dataset.id, 'rejected'));
            });
        };

        loadApprovals();

        this.updateHandler = () => {
            console.log('Reloading approvals...');
            loadApprovals();
        };
        window.addEventListener('update:approvals', this.updateHandler);
    },

    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:approvals', this.updateHandler);
        }
    },

    async decide(id, decision) {
        const reason = prompt(`Reason for ${decision}?`, "Manual review");
        if (!reason) return;
        
        try {
            const res = await window.api.post(`/v1/approvals/${id}/decision`, {
                decision,
                reason,
                approver: document.getElementById('user-info').textContent
            });
            if (res.ok) {
                window.App.toast(`Approval ${decision} successfully`, 'success');
                this.mount(document.getElementById('main-content')); // Reload
            } else {
                window.App.toast('Error: ' + res.error, 'error');
            }
        } catch (e) {
            console.error(e);
            window.App.toast('Error submitting decision', 'error');
        }
    }
};
