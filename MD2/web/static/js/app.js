
import DashboardView from './views/dashboard.js';
import WorkflowsView from './views/workflows.js';
import SchedulesView from './views/schedules.js';
import RunsView from './views/runs.js';
import ApprovalsView from './views/approvals.js';
import AgentsView from './views/agents.js';
import SkillsView from './views/skills.js';
import AuditView from './views/audit.js';
import SystemView from './views/system.js';
import QueueView from './views/queue.js';
import LearningView from './views/learning.js';
import EvidenceView from './views/evidence.js';

const App = {
    state: {
        token: localStorage.getItem('openclaw_token') || '',
        user: null,
        currentView: 'dashboard',
        sse: null
    },

    routes: {
        '': DashboardView,
        'dashboard': DashboardView,
        'workflows': WorkflowsView,
        'schedules': SchedulesView,
        'runs': RunsView,
        'approvals': ApprovalsView,
        'agents': AgentsView,
        'skills': SkillsView,
        'audit': AuditView,
        'system': SystemView,
        'queue': QueueView,
        'learning': LearningView,
        'evidence': EvidenceView
    },

    init() {
        this.bindEvents();
        this.handleRoute();
        this.connectSSE();
        
        // Auto-login if token exists (simple check)
        if (!this.state.token) {
            this.login();
        } else {
            document.getElementById('user-info').textContent = 'Admin'; // Mock
        }
    },

    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">${message}</div>
        `;
        
        container.appendChild(toast);

        // Auto remove
        setTimeout(() => {
            toast.classList.add('hiding');
            toast.addEventListener('animationend', () => {
                if (toast.parentElement) toast.remove();
            });
        }, 3000);
    },
    
    connectSSE() {
        if (this.state.sse) return;
        
        this.state.sse = new EventSource('/v1/events/stream');
        
        this.state.sse.addEventListener('heartbeat', (e) => {
            // console.log('Heartbeat', e.data);
            // Could update a "Live" indicator
        });
        
        this.state.sse.addEventListener('stats', (e) => {
            try {
                const data = JSON.parse(e.data);
                // Broadcast to active view or update global counters?
                // For now, just update global counters if they exist in DOM (Dashboard)
                const pendingEl = document.getElementById('dash-pending-approvals');
                if (pendingEl) pendingEl.textContent = data.pending_approvals;
            } catch (err) {
                console.warn('SSE Parse Error', err);
            }
        });

        // Generic Event Dispatcher
        const dispatch = (event) => {
            // If current view has a 'refresh' method, call it
            // Ideally we check if the event matches the view context
            // But for now, we just let the View decide or re-mount if it's the right view.
            
            // Actually, re-mounting is heavy (destroys DOM).
            // Views should have a `refresh()` method.
            // If not, we do nothing or re-mount.
            
            // Better: Dispatch custom DOM event
            window.dispatchEvent(new CustomEvent(event.type, { detail: event.data }));
        };

        ['update:runs', 'update:agents', 'update:approvals', 'update:queue', 'update:system', 'update:dashboard', 'update:schedules', 'update:workflows', 'update:skills', 'update:learning', 'update:evidence', 'update:audit'].forEach(evt => {
            this.state.sse.addEventListener(evt, dispatch);
        });
    },

    bindEvents() {
        window.addEventListener('hashchange', () => this.handleRoute());
        document.getElementById('login-btn').addEventListener('click', () => this.login());
    },

    handleRoute() {
        const hash = window.location.hash.slice(2) || 'dashboard'; // Remove #/
        const baseRoute = hash.split('/')[0];
        
        // Update nav
        document.querySelectorAll('.nav-link').forEach(el => {
            el.classList.remove('active');
            if (el.getAttribute('data-view') === baseRoute) {
                el.classList.add('active');
            }
        });

        const View = this.routes[baseRoute] || DashboardView;
        const main = document.getElementById('main-content');
        
        // Clear content
        main.innerHTML = '';
        
        // Render view
        if (View && View.render) {
            // Unmount previous if exists
            if (this.currentViewInstance && this.currentViewInstance.unmount) {
                this.currentViewInstance.unmount();
            }
            this.currentViewInstance = View; // Track current view object

            main.innerHTML = View.render();
            if (View.mount) {
                View.mount(main);
            }
        } else {
            main.innerHTML = '<h1>404 Not Found</h1>';
        }
    },

    async login() {
        // Mock login for now, or real one
        const userId = prompt("Enter User ID (e.g. admin):", "admin");
        if (!userId) return;
        
        try {
            const res = await fetch('/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, roles: ['admin'] })
            });
            const data = await res.json();
            if (data.ok) {
                this.state.token = data.token;
                localStorage.setItem('openclaw_token', data.token);
                document.getElementById('user-info').textContent = userId;
                this.toast(`Welcome back, ${userId}!`, 'success');
                // Reload current view
                this.handleRoute();
            } else {
                this.toast('Login failed: ' + data.error, 'error');
            }
        } catch (e) {
            console.error(e);
            this.toast('Login error', 'error');
        }
    }
};

// Global API helper
window.api = {
    async get(url) {
        const headers = {};
        if (App.state.token) {
            headers['Authorization'] = 'Bearer ' + App.state.token;
        }
        const res = await fetch(url, { headers });
        return res.json();
    },
    
    async post(url, body) {
        const headers = { 'Content-Type': 'application/json' };
        if (App.state.token) {
            headers['Authorization'] = 'Bearer ' + App.state.token;
        }
        const res = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(body)
        });
        return res.json();
    },

    async patch(url, body) {
        const headers = { 'Content-Type': 'application/json' };
        if (App.state.token) {
            headers['Authorization'] = 'Bearer ' + App.state.token;
        }
        const res = await fetch(url, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(body)
        });
        return res.json();
    }
};

window.App = App;
App.init();
