// main.js - App Entry
import { store } from './store.js';
import { api } from './api.js';
import { i18n } from './i18n.js';

// Import Components
import SidebarComponent from './components/layout/Sidebar.js';
import CopilotComponent from './components/layout/Copilot.js';
import StatusBadge from './components/common/StatusBadge.js';
import ModalComponent from './components/common/Modal.js';
import SettingsComponent from './components/common/Settings.js';

// Import Views (Modules)
import DashboardView from './components/modules/Dashboard.js';
import AgentPoolView from './components/modules/AgentPool.js';
import OrchestratorView from './components/modules/Orchestrator.js';
import GovernanceView from './components/modules/Governance.js';
import MemoryHubView from './components/modules/MemoryHub.js';
import GrowthLoopView from './components/modules/GrowthLoop.js';
import EvalGateView from './components/modules/EvalGate.js';
import ConsoleConfigView from './components/modules/ConsoleConfig.js';
import TracingView from './components/modules/Tracing.js';
import LoadingBar from './components/common/LoadingBar.js';

const app = Vue.createApp({
    data() {
        return {
            currentView: 'dashboard',
            showCopilot: false,
            sidebarOpen: false, // For mobile
            isDark: false,
            modal: { show: false, props: {}, component: null }
        };
    },
    computed: {
        user() { return store.user; },
        systemStatus() { return store.systemStatus; },
        notifications() { return store.notifications; },
        loading() { 
            // Aggregate loading state
            return Object.values(store.loading).some(v => v); 
        },
        currentViewComponent() {
            const map = {
                'dashboard': 'dashboard-view',
                'agent_pool': 'agent-pool-view',
                'orchestrator': 'orchestrator-view',
                'governance': 'governance-view',
                'memory_hub': 'memory-hub-view',
                'growth_loop': 'growth-loop-view',
                'eval_gate': 'eval-gate-view',
                'tracing': 'tracing-view',
                'console_config': 'console-config-view'
            };
            return map[this.currentView] || 'dashboard-view';
        }
    },
    watch: {
        currentView() {
            // Close sidebar on mobile when view changes
            if (window.innerWidth < 1024) {
                this.sidebarOpen = false;
            }
        }
    },
    created() {
        // Init SSE
        api.initSSE();
        
        // Check Dark Mode
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.isDark = true;
            document.documentElement.classList.add('dark');
        }
        
        // Global Keyboard Shortcuts
        window.addEventListener('keydown', this.handleKeydown);

        // Listen for system errors to show toast
        window.addEventListener('unhandledrejection', (event) => {
            store.addNotification(event.reason.message || 'Unknown Error', 'error');
        });
    },
    beforeUnmount() {
        window.removeEventListener('keydown', this.handleKeydown);
    },
    methods: {
        handleKeydown(e) {
            // Ctrl/Cmd + K: Toggle Copilot
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.toggleCopilot();
            }
            // Esc: Close Copilot or Modal
            if (e.key === 'Escape') {
                if (this.modal.show) {
                    this.closeModal();
                } else if (this.showCopilot) {
                    this.showCopilot = false;
                }
            }
        },
        changeView(view) {
            this.currentView = view;
        },
        toggleCopilot() {
            this.showCopilot = !this.showCopilot;
        },
        toggleTheme() {
            this.isDark = !this.isDark;
            if (this.isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        },
        openModal(props) {
            this.modal = { show: true, props, component: null };
        },
        openSettings() {
            this.modal = { 
                show: true, 
                props: { title: 'User Settings' }, 
                component: 'settings-component' 
            };
        },
        closeModal() {
            this.modal.show = false;
            this.modal.component = null;
        },
        handleModalConfirm() {
            // If component has save method, call it
            if (this.$refs.modalContent && this.$refs.modalContent.save) {
                this.$refs.modalContent.save();
            }
            this.closeModal();
        }
    }
});

// Global Mixins/Properties
app.config.globalProperties.$t = (key) => i18n.t(key);
app.config.globalProperties.$api = api;
app.config.globalProperties.$store = store;

// Register Components
app.component('sidebar-component', SidebarComponent);
app.component('copilot-component', CopilotComponent);
app.component('status-badge', StatusBadge);
app.component('modal-component', ModalComponent);
app.component('settings-component', SettingsComponent);
app.component('loading-bar', LoadingBar);

// Register Views
app.component('dashboard-view', DashboardView);
app.component('agent-pool-view', AgentPoolView);
app.component('orchestrator-view', OrchestratorView);
app.component('governance-view', GovernanceView);
app.component('memory-hub-view', MemoryHubView);
app.component('growth-loop-view', GrowthLoopView);
app.component('eval-gate-view', EvalGateView);
app.component('console-config-view', ConsoleConfigView);
app.component('tracing-view', TracingView);

app.mount('#app');
