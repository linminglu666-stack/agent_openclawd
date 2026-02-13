
export default {
    render() {
        return `
            <div class="view-system">
                <h1>Server Control</h1>
                
                <div class="control-panel card">
                    <div class="status-row">
                        <span>Status: </span>
                        <span id="sys-status" class="status-badge unknown">Checking...</span>
                    </div>
                    <div class="actions-row">
                        <button id="btn-start" class="btn-success">Start Server</button>
                        <button id="btn-restart" class="btn-warning">Restart Server</button>
                        <button id="btn-stop" class="btn-danger">Stop Server</button>
                    </div>
                </div>

                <div class="logs-panel card">
                    <h3>Server Logs</h3>
                    <div class="logs-container">
                        <pre id="sys-logs">Loading logs...</pre>
                    </div>
                    <div class="logs-actions">
                        <label><input type="checkbox" id="chk-autoscroll" checked> Auto-scroll</label>
                        <button id="btn-refresh-logs" class="small">Refresh Now</button>
                    </div>
                </div>
            </div>
        `;
    },

    async mount(el) {
        this.el = el;
        this.statusEl = el.querySelector('#sys-status');
        this.logsEl = el.querySelector('#sys-logs');
        this.autoScroll = true;
        this.logInterval = null;

        // Bind Controls
        el.querySelector('#btn-start').addEventListener('click', () => this.control('start'));
        el.querySelector('#btn-restart').addEventListener('click', () => this.control('restart'));
        el.querySelector('#btn-stop').addEventListener('click', () => this.control('stop'));
        el.querySelector('#btn-refresh-logs').addEventListener('click', () => this.fetchLogs());
        
        el.querySelector('#chk-autoscroll').addEventListener('change', (e) => {
            this.autoScroll = e.target.checked;
        });

        // Initial Load
        await this.refreshStatus();
        await this.fetchLogs();

        // Polling for logs
        // Now using SSE event update:system to trigger fetchLogs
        this.updateHandler = () => {
            if (this.el && document.body.contains(this.el)) {
                this.fetchLogs();
                this.refreshStatus();
            }
        };
        window.addEventListener('update:system', this.updateHandler);
    },
    
    unmount() {
        if (this.logInterval) clearInterval(this.logInterval);
        if (this.updateHandler) window.removeEventListener('update:system', this.updateHandler);
    },

    async control(action) {
        if (!confirm(`Are you sure you want to ${action} the server?`)) return;
        
        try {
            const res = await window.api.post('/v1/system/control', { action });
            if (res.ok) {
                this.updateStatus(res.status);
                window.App.toast(`Server ${action} initiated`, 'success');
            } else {
                window.App.toast('Error: ' + res.error, 'error');
            }
        } catch (e) {
            console.error(e);
            window.App.toast('Request failed', 'error');
        }
    },

    async refreshStatus() {
        try {
            const res = await window.api.get('/v1/system/status');
            if (res.ok) {
                this.updateStatus(res.status);
            }
        } catch (e) {
            this.updateStatus('error');
        }
    },

    updateStatus(status) {
        this.statusEl.textContent = status.toUpperCase();
        this.statusEl.className = `status-badge ${status}`;
        
        // Update button states
        const running = status === 'running';
        this.el.querySelector('#btn-start').disabled = running;
        this.el.querySelector('#btn-stop').disabled = !running;
    },

    async fetchLogs() {
        try {
            const res = await window.api.get('/v1/system/logs');
            if (res.ok) {
                const text = res.logs.join('');
                this.logsEl.textContent = text;
                if (this.autoScroll) {
                    const container = this.el.querySelector('.logs-container');
                    container.scrollTop = container.scrollHeight;
                }
            }
        } catch (e) {
            // ignore
        }
    }
};
