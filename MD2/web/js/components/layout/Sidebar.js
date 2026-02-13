// Sidebar.js - 侧边导航
export default {
    props: ['currentView'],
    template: `
        <div class="flex flex-col h-full">
            <!-- Logo -->
            <div class="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-lighter shrink-0">
                <span class="text-2xl mr-2">🦀</span>
                <h1 class="text-xl font-bold bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent truncate">
                    OpenClaw-X
                </h1>
            </div>

            <!-- Navigation -->
            <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-1">
                <a 
                    v-for="item in menuItems" 
                    :key="item.id"
                    @click="$emit('change-view', item.id)"
                    class="group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg cursor-pointer transition-all duration-200"
                    :class="currentView === item.id 
                        ? 'bg-primary text-white shadow-md shadow-blue-500/20' 
                        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'">
                    <span class="mr-3 text-lg opacity-80 group-hover:opacity-100 transition-opacity">{{ item.icon }}</span>
                    <span class="flex-1">{{ $t('views.' + item.id) }}</span>
                    
                    <!-- Badges -->
                    <span 
                        v-if="getBadge(item.id)" 
                        class="ml-auto py-0.5 px-2 rounded-full text-xs font-bold transition-transform transform group-hover:scale-110"
                        :class="getBadgeClass(item.id)">
                        {{ getBadge(item.id) }}
                    </span>
                </a>
            </nav>

            <!-- Footer -->
            <div class="p-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
                <div class="flex items-center space-x-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                    <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span class="text-xs text-gray-500 font-mono">System Online</span>
                </div>
                <div class="mt-2 text-[10px] text-gray-400 text-center">v2.0.0 (X-Arch)</div>
            </div>
        </div>
    `,
    data() {
        return {
            menuItems: [
                { id: 'dashboard', icon: '📊' },
                { id: 'agent_pool', icon: '🤖' },
                { id: 'orchestrator', icon: '🎼' },
                { id: 'governance', icon: '⚖️' },
                { id: 'memory_hub', icon: '🧠' },
                { id: 'growth_loop', icon: '🌱' },
                { id: 'eval_gate', icon: '🛡️' },
                { id: 'tracing', icon: '🔍' },
                { id: 'console_config', icon: '⚙️' }
            ]
        };
    },
    methods: {
        getBadge(viewId) {
            if (viewId === 'governance') {
                return this.$store.approvals.length || null;
            }
            if (viewId === 'agent_pool') {
                const errorCount = this.$store.agents.filter(a => a.status === 'error').length;
                return errorCount > 0 ? errorCount : null;
            }
            return null;
        },
        getBadgeClass(viewId) {
            if (viewId === 'governance') {
                return 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-200';
            }
            if (viewId === 'agent_pool') {
                return 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-200';
            }
            return '';
        }
    }
};
