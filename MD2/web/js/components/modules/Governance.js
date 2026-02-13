// Governance.js - 治理与审计
import EntropyMonitor from './EntropyMonitor.js';

export default {
    components: { EntropyMonitor },
    template: `
        <div class="space-y-6">
            <!-- Tabs -->
            <div class="border-b border-gray-200 dark:border-gray-700">
                <nav class="-mb-px flex space-x-8" aria-label="Tabs">
                    <button 
                        v-for="tab in tabs" 
                        :key="tab.id"
                        @click="currentTab = tab.id"
                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors relative"
                        :class="currentTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300'">
                        {{ tab.label }}
                        <span 
                            v-if="tab.count" 
                            class="ml-2 py-0.5 px-2.5 rounded-full text-xs font-medium"
                            :class="currentTab === tab.id ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-200'">
                            {{ tab.count }}
                        </span>
                    </button>
                </nav>
            </div>

            <!-- Content Area -->
            <transition name="fade" mode="out-in">
                <!-- Entropy Monitor Tab -->
                <div v-if="currentTab === 'entropy'" key="entropy">
                    <entropy-monitor></entropy-monitor>
                </div>

                <!-- Approvals Tab -->
                <div v-else-if="currentTab === 'approvals'" key="approvals" class="space-y-4">
                    <div v-if="loading" class="space-y-4">
                         <div v-for="i in 3" :key="i" class="h-32 bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 skeleton"></div>
                    </div>
                    
                    <div v-else-if="approvals.length === 0" class="text-center py-12 text-gray-500">
                        <span class="text-4xl block mb-2">✅</span>
                        No pending approvals.
                    </div>

                    <div v-else v-for="item in approvals" :key="item.id" class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow">
                        <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
                            <div class="flex-1">
                                <div class="flex items-center space-x-3 mb-2">
                                    <span class="px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wide" :class="getTypeColor(item.type)">
                                        {{ item.type }}
                                    </span>
                                    <h3 class="font-bold text-gray-900 dark:text-white text-lg">{{ item.title }}</h3>
                                </div>
                                <p class="text-sm text-gray-600 dark:text-gray-300 mb-4">{{ item.description }}</p>
                                <div class="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-gray-500 font-mono">
                                    <span class="flex items-center">
                                        <span class="mr-1">👤</span> {{ item.requester }}
                                    </span>
                                    <span class="flex items-center">
                                        <span class="mr-1">🕒</span> {{ item.time }}
                                    </span>
                                    <span class="flex items-center" :class="getRiskColor(item.riskScore)">
                                        <span class="mr-1">⚠️</span> Risk: {{ item.riskScore }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex space-x-3 w-full sm:w-auto">
                                <button 
                                    @click="reject(item)"
                                    class="flex-1 sm:flex-none px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                    Reject
                                </button>
                                <button 
                                    @click="approve(item)"
                                    class="flex-1 sm:flex-none px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 shadow-sm transition-colors">
                                    Approve
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Audit Tab -->
                <div v-else-if="currentTab === 'audit'" key="audit" class="bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead class="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resource</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white dark:bg-dark-lighter divide-y divide-gray-200 dark:divide-gray-700">
                                <tr v-for="log in auditLogs" :key="log.id" class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">{{ log.time }}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">{{ log.user }}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                            {{ log.action }}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ log.resource }}</td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Success</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Policies Tab (Placeholder) -->
                <div v-else key="policies" class="text-center py-20 text-gray-400">
                    <span class="text-4xl block mb-4">📜</span>
                    <p>Policy management coming soon.</p>
                </div>
            </transition>
        </div>
    `,
    data() {
        return {
            currentTab: 'entropy',
            tabs: [
                { id: 'entropy', label: 'Entropy V2' },
                { id: 'approvals', label: 'Pending Approvals', count: 0 }, // Count updated from store
                { id: 'audit', label: 'Audit Log' },
                { id: 'policies', label: 'Policy Rules' }
            ],
            auditLogs: [
                { id: 1, time: '2023-10-27 10:00:01', user: 'admin', action: 'Login', resource: 'System' },
                { id: 2, time: '2023-10-27 10:05:23', user: 'AutoScaler', action: 'Scale', resource: 'AgentPool' },
                { id: 3, time: '2023-10-27 10:12:45', user: 'admin', action: 'Update', resource: 'Policy:Network' },
                { id: 4, time: '2023-10-27 10:15:00', user: 'CI/CD', action: 'Deploy', resource: 'Workflow:Payment' },
                { id: 5, time: '2023-10-27 10:20:11', user: 'Bob', action: 'Access', resource: 'DebugTool' },
            ]
        };
    },
    computed: {
        approvals() {
            return this.$store.approvals;
        },
        loading() {
            return this.$store.loading.approvals;
        }
    },
    watch: {
        approvals: {
            handler(newVal) {
                const tab = this.tabs.find(t => t.id === 'approvals');
                if (tab) tab.count = newVal.length;
            },
            immediate: true
        }
    },
    mounted() {
        this.$store.refreshApprovals();
    },
    methods: {
        getTypeColor(type) {
            const colors = {
                'Scale Up': 'bg-purple-100 text-purple-800',
                'Access': 'bg-blue-100 text-blue-800',
                'Deployment': 'bg-yellow-100 text-yellow-800'
            };
            return colors[type] || 'bg-gray-100 text-gray-800';
        },
        getRiskColor(score) {
            if (score > 0.8) return 'text-red-600 font-bold';
            if (score > 0.5) return 'text-yellow-600';
            return 'text-green-600';
        },
        async approve(item) {
            if (!confirm(`Approve request: ${item.title}?`)) return;
            this.$store.addNotification(`Approved request #${item.id}`, 'success');
            // Optimistic remove
            const idx = this.$store.approvals.findIndex(a => a.id === item.id);
            if (idx !== -1) this.$store.approvals.splice(idx, 1);
        },
        async reject(item) {
            if (!confirm(`Reject request: ${item.title}?`)) return;
            this.$store.addNotification(`Rejected request #${item.id}`, 'info');
            const idx = this.$store.approvals.findIndex(a => a.id === item.id);
            if (idx !== -1) this.$store.approvals.splice(idx, 1);
        }
    }
};
