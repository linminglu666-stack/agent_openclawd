// AgentPool.js - 资源池管理
import { format } from '../../utils/format.js';

export default {
    template: `
        <div class="space-y-6">
            <!-- Controls -->
            <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
                <div class="flex flex-1 space-x-4 w-full sm:w-auto">
                    <div class="relative flex-1 sm:flex-none sm:w-64">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">🔍</span>
                        <input 
                            v-model="searchQuery" 
                            type="text" 
                            placeholder="Search agents..." 
                            class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-dark-lighter focus:ring-2 focus:ring-primary outline-none transition-shadow">
                    </div>
                    <select 
                        v-model="statusFilter"
                        class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-dark-lighter focus:ring-2 focus:ring-primary outline-none cursor-pointer">
                        <option value="all">All Status</option>
                        <option value="running">Running</option>
                        <option value="idle">Idle</option>
                        <option value="error">Error</option>
                    </select>
                </div>
                <button 
                    @click="openScaleModal" 
                    class="w-full sm:w-auto px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 flex items-center justify-center transition-colors shadow-sm hover:shadow">
                    <span class="mr-2 text-lg leading-none">+</span> Scale Up
                </button>
            </div>

            <!-- Loading State -->
            <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div v-for="i in 6" :key="i" class="h-48 bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 skeleton"></div>
            </div>

            <!-- Empty State -->
            <div v-else-if="filteredAgents.length === 0" class="flex flex-col items-center justify-center py-20 text-gray-500 dark:text-gray-400">
                <span class="text-4xl mb-4">🤖</span>
                <p>No agents found matching your criteria.</p>
            </div>

            <!-- Agent Grid -->
            <transition-group 
                tag="div" 
                name="list" 
                class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                v-else>
                <div 
                    v-for="agent in filteredAgents" 
                    :key="agent.id" 
                    class="bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 relative group hover:shadow-md hover:border-primary/30 transition-all duration-300 transform hover:-translate-y-1">
                    
                    <!-- Header -->
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex items-center space-x-3">
                            <div class="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-2xl shadow-inner">
                                {{ agent.icon }}
                            </div>
                            <div>
                                <h3 class="font-bold text-gray-900 dark:text-white leading-tight">{{ agent.name }}</h3>
                                <p class="text-xs text-gray-500 font-mono mt-1">{{ agent.id }}</p>
                            </div>
                        </div>
                        <status-badge :status="agent.status"></status-badge>
                    </div>
                    
                    <!-- Stats -->
                    <div class="space-y-3 mb-4">
                        <div class="flex justify-between text-sm">
                            <span class="text-gray-500">Tasks Completed</span>
                            <span class="font-medium font-mono">{{ formatNumber(agent.tasks) }}</span>
                        </div>
                        <div class="flex justify-between text-sm">
                            <span class="text-gray-500">Uptime</span>
                            <span class="font-medium font-mono">{{ agent.uptime }}</span>
                        </div>
                        <div class="relative pt-1">
                            <div class="flex mb-2 items-center justify-between">
                                <span class="text-xs font-semibold inline-block text-gray-500">
                                    Load
                                </span>
                                <span class="text-xs font-semibold inline-block" :class="getLoadColorText(agent.load)">
                                    {{ agent.load }}%
                                </span>
                            </div>
                            <div class="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-100 dark:bg-gray-700">
                                <div :style="{ width: agent.load + '%' }" 
                                     class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center transition-all duration-500"
                                     :class="getLoadColorBg(agent.load)">
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex space-x-2 pt-4 border-t border-gray-100 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button 
                            @click="viewLogs(agent)"
                            class="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                            Logs
                        </button>
                        <button 
                            @click="stopAgent(agent)"
                            :disabled="agent.status === 'stopped'"
                            class="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-danger rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                            Stop
                        </button>
                    </div>
                </div>
            </transition-group>

            <!-- Scale Up Modal -->
            <modal-component 
                v-if="showScaleModal" 
                title="Scale Up Agent Pool" 
                @close="showScaleModal = false"
                @confirm="confirmScale">
                <div class="space-y-4">
                    <p class="text-sm text-gray-500">Increase the number of active agents to handle higher load.</p>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Target Count</label>
                        <input type="number" v-model.number="scaleTarget" min="1" max="50" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:bg-dark bg-white py-2 px-3">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Reason</label>
                        <textarea v-model="scaleReason" rows="3" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:bg-dark bg-white py-2 px-3" placeholder="e.g., Black Friday traffic"></textarea>
                    </div>
                </div>
            </modal-component>

            <!-- Logs Modal -->
            <modal-component 
                v-if="showLogsModal" 
                :title="'Logs: ' + (selectedAgent ? selectedAgent.name : '')" 
                width="sm:max-w-2xl"
                @close="closeLogsModal">
                
                <div class="bg-gray-900 text-gray-200 font-mono text-xs p-4 rounded-lg h-96 overflow-y-auto" ref="logContainer">
                    <div v-for="(log, idx) in agentLogs" :key="idx" class="mb-1 break-all">
                        <span class="text-gray-500">{{ log.time }}</span>
                        <span :class="getLogColor(log.level)" class="mx-2 font-bold">{{ log.level }}</span>
                        <span>{{ log.msg }}</span>
                    </div>
                    <div v-if="loadingLogs" class="animate-pulse text-gray-500 mt-2">_</div>
                </div>

                <template #footer>
                    <button 
                        type="button" 
                        class="w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none sm:w-auto sm:text-sm"
                        @click="closeLogsModal">
                        Close
                    </button>
                    <button 
                        type="button" 
                        class="mt-3 w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary text-base font-medium text-white hover:bg-blue-700 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                        @click="downloadLogs">
                        Download
                    </button>
                </template>
            </modal-component>
        </div>
    `,
    data() {
        return {
            searchQuery: '',
            statusFilter: 'all',
            showScaleModal: false,
            scaleTarget: 10,
            scaleReason: '',
            
            // Logs
            showLogsModal: false,
            selectedAgent: null,
            agentLogs: [],
            loadingLogs: false,
            logInterval: null
        };
    },
    computed: {
        loading() {
            return this.$store.loading.agents;
        },
        agents() {
            return this.$store.agents;
        },
        filteredAgents() {
            return this.agents.filter(agent => {
                const matchesSearch = agent.name.toLowerCase().includes(this.searchQuery.toLowerCase()) || 
                                    agent.id.toLowerCase().includes(this.searchQuery.toLowerCase());
                const matchesStatus = this.statusFilter === 'all' || agent.status === this.statusFilter;
                return matchesSearch && matchesStatus;
            });
        }
    },
    mounted() {
        this.$store.refreshAgents();
        this.timer = setInterval(() => this.$store.refreshAgents(), 5000);
    },
    beforeUnmount() {
        clearInterval(this.timer);
        this.stopLogStream();
    },
    methods: {
        formatNumber: format.number,
        getLoadColorBg(load) {
            if (load > 90) return 'bg-red-500';
            if (load > 70) return 'bg-yellow-500';
            return 'bg-green-500';
        },
        getLoadColorText(load) {
            if (load > 90) return 'text-red-600 dark:text-red-400';
            if (load > 70) return 'text-yellow-600 dark:text-yellow-400';
            return 'text-green-600 dark:text-green-400';
        },
        openScaleModal() {
            this.scaleTarget = this.agents.length + 1;
            this.showScaleModal = true;
        },
        async confirmScale() {
            this.showScaleModal = false;
            // Use store action to trigger approval
            this.$store.triggerApproval('Scale Up', `Request to scale to ${this.scaleTarget} agents`, this.scaleReason, 0.6);
        },
        viewLogs(agent) {
            this.selectedAgent = agent;
            this.showLogsModal = true;
            this.agentLogs = [];
            this.startLogStream();
        },
        closeLogsModal() {
            this.showLogsModal = false;
            this.stopLogStream();
            this.selectedAgent = null;
        },
        startLogStream() {
            this.loadingLogs = true;
            // Generate initial logs
            for (let i = 0; i < 20; i++) {
                this.addLog();
            }
            // Stream new logs
            this.logInterval = setInterval(() => {
                if (Math.random() > 0.5) this.addLog();
                // Scroll to bottom
                this.$nextTick(() => {
                    if (this.$refs.logContainer) {
                        this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight;
                    }
                });
            }, 800);
        },
        stopLogStream() {
            if (this.logInterval) {
                clearInterval(this.logInterval);
                this.logInterval = null;
            }
            this.loadingLogs = false;
        },
        addLog() {
            const levels = ['INFO', 'INFO', 'INFO', 'WARN', 'DEBUG'];
            const msgs = [
                'Processing task #4213...',
                'Heartbeat sent to master',
                'Memory usage: 450MB',
                'Connecting to DB shard-02...',
                'Garbage collection started',
                'Cache hit for key: user:123'
            ];
            const level = levels[Math.floor(Math.random() * levels.length)];
            const msg = msgs[Math.floor(Math.random() * msgs.length)];
            const time = new Date().toISOString().split('T')[1].slice(0, 12);
            
            this.agentLogs.push({ time, level, msg });
            if (this.agentLogs.length > 200) this.agentLogs.shift();
        },
        getLogColor(level) {
            if (level === 'WARN') return 'text-yellow-400';
            if (level === 'ERROR') return 'text-red-400';
            if (level === 'DEBUG') return 'text-blue-400';
            return 'text-green-400';
        },
        downloadLogs() {
            const content = this.agentLogs.map(l => `[${l.time}] ${l.level}: ${l.msg}`).join('\n');
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.selectedAgent.id}.log`;
            a.click();
        },
        async stopAgent(agent) {
            if (!confirm(`Are you sure you want to stop ${agent.name}?`)) return;
            this.$store.updateAgentStatus(agent.id, 'stopped');
            this.$store.addNotification(`${agent.name} stopped.`, 'warning');
        }
    }
};
