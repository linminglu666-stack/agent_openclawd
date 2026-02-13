// ConsoleConfig.js - 控制台配置与调试中心
import CodeEditor from '../common/CodeEditor.js';

export default {
    components: { CodeEditor },
    template: `
        <div class="h-full flex flex-col bg-gray-50 dark:bg-dark">
            <!-- Tabs -->
            <div class="bg-white dark:bg-dark-lighter border-b border-gray-200 dark:border-gray-700 px-6">
                <nav class="-mb-px flex space-x-8">
                    <button 
                        @click="activeTab = 'config'"
                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
                        :class="activeTab === 'config' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'">
                        ⚙️ System Config
                    </button>
                    <button 
                        @click="activeTab = 'playground'"
                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
                        :class="activeTab === 'playground' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'">
                        🔌 API Playground
                    </button>
                </nav>
            </div>

            <!-- Config Tab -->
            <div v-if="activeTab === 'config'" class="flex-1 overflow-y-auto p-6">
                <div class="max-w-4xl mx-auto space-y-8">
                    <!-- Environment -->
                    <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Environment & Network</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">API Base URL</label>
                                <div class="flex">
                                    <span class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-500 text-sm">https://</span>
                                    <input type="text" value="api.openclaw.io/v1" class="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark focus:ring-primary focus:border-primary sm:text-sm">
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Simulated Latency: <span class="text-primary font-mono">{{ config.mockLatency }}ms</span>
                                </label>
                                <input type="range" v-model.number="config.mockLatency" min="0" max="2000" step="50" class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                                <div class="flex justify-between text-xs text-gray-400 mt-1">
                                    <span>0ms (Instant)</span>
                                    <span>2000ms (Slow)</span>
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Error Rate Injection: <span class="text-red-500 font-mono">{{ config.mockErrorRate }}%</span>
                                </label>
                                <input type="range" v-model.number="config.mockErrorRate" min="0" max="100" step="5" class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            </div>
                        </div>
                    </div>

                    <!-- Business Logic -->
                    <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Business Logic (Hot Reload)</h3>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Active Agents Count</label>
                                <div class="flex items-center space-x-4">
                                    <input type="number" v-model.number="config.agentCount" class="w-24 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-dark focus:ring-primary focus:border-primary">
                                    <span class="text-sm text-gray-500">Updating this will immediately regenerate the agent pool.</span>
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tracing Sampling Rate</label>
                                <select class="w-full md:w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-dark focus:ring-primary focus:border-primary">
                                    <option value="1.0">100% (All Traces)</option>
                                    <option value="0.1">10% (Production)</option>
                                    <option value="0.0">Off</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Playground Tab -->
            <div v-else class="flex-1 flex overflow-hidden">
                <!-- Sidebar -->
                <div class="w-64 bg-white dark:bg-dark-lighter border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
                    <div class="p-4">
                        <input type="text" placeholder="Filter endpoints..." class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm">
                    </div>
                    <div class="px-2 space-y-1">
                        <button 
                            v-for="ep in endpoints" 
                            :key="ep.path"
                            @click="selectEndpoint(ep)"
                            class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center space-x-2"
                            :class="selectedEndpoint === ep ? 'bg-blue-50 dark:bg-blue-900/30 text-primary' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'">
                            <span class="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded text-white w-12 text-center" :class="getMethodColor(ep.method)">{{ ep.method }}</span>
                            <span class="truncate">{{ ep.path }}</span>
                        </button>
                    </div>
                </div>

                <!-- Request/Response -->
                <div class="flex-1 flex flex-col min-w-0 bg-gray-50 dark:bg-dark">
                    <div v-if="selectedEndpoint" class="flex-1 flex flex-col h-full">
                        <!-- Request Panel -->
                        <div class="flex-1 flex flex-col border-b border-gray-200 dark:border-gray-700 p-4 overflow-hidden">
                            <div class="flex justify-between items-center mb-4">
                                <h3 class="font-mono text-lg text-gray-800 dark:text-white">
                                    <span :class="'text-' + getMethodColor(selectedEndpoint.method).split('-')[1]">{{ selectedEndpoint.method }}</span> 
                                    {{ selectedEndpoint.path }}
                                </h3>
                                <button 
                                    @click="executeRequest"
                                    :disabled="executing"
                                    class="px-6 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 shadow-sm flex items-center disabled:opacity-50">
                                    <span v-if="executing" class="animate-spin mr-2">⟳</span>
                                    {{ executing ? 'Running...' : 'Send Request' }}
                                </button>
                            </div>
                            
                            <!-- Params -->
                            <div class="flex-1 flex flex-col space-y-2">
                                <label class="text-xs font-bold text-gray-500 uppercase">Request Body (JSON)</label>
                                <div class="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
                                    <code-editor v-model="requestBody"></code-editor>
                                </div>
                            </div>
                        </div>

                        <!-- Response Panel -->
                        <div class="flex-1 flex flex-col p-4 bg-white dark:bg-dark-lighter overflow-hidden">
                            <div class="flex justify-between items-center mb-2">
                                <label class="text-xs font-bold text-gray-500 uppercase">Response</label>
                                <span v-if="responseStatus" class="text-xs font-mono px-2 py-1 rounded" :class="responseStatus >= 400 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'">
                                    Status: {{ responseStatus }}
                                </span>
                            </div>
                            <div class="flex-1 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900 p-4 overflow-auto font-mono text-xs text-gray-800 dark:text-gray-300 whitespace-pre">
                                {{ responseBody }}
                            </div>
                        </div>
                    </div>
                    <div v-else class="flex-1 flex items-center justify-center text-gray-400">
                        Select an endpoint to start debugging.
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            activeTab: 'config',
            endpoints: [
                { method: 'GET', path: '/agents', body: '{}' },
                { method: 'POST', path: '/agents/scale', body: '{\n  "target": 10,\n  "reason": "load_test"\n}' },
                { method: 'GET', path: '/traces', body: '{}' },
                { method: 'GET', path: '/dashboard/metrics', body: '{}' }
            ],
            selectedEndpoint: null,
            requestBody: '',
            responseBody: '',
            responseStatus: null,
            executing: false
        };
    },
    computed: {
        config() {
            return this.$store.config;
        }
    },
    watch: {
        // Hot Reload Watchers
        'config.mockLatency'(val) { this.$store.updateConfig('mockLatency', val); },
        'config.mockErrorRate'(val) { this.$store.updateConfig('mockErrorRate', val); },
        'config.agentCount'(val) { this.$store.updateConfig('agentCount', val); }
    },
    methods: {
        getMethodColor(method) {
            const map = {
                'GET': 'bg-blue-500',
                'POST': 'bg-green-500',
                'PUT': 'bg-yellow-500',
                'DELETE': 'bg-red-500'
            };
            return map[method] || 'bg-gray-500';
        },
        selectEndpoint(ep) {
            this.selectedEndpoint = ep;
            this.requestBody = ep.body;
            this.responseBody = '';
            this.responseStatus = null;
        },
        async executeRequest() {
            this.executing = true;
            this.responseBody = 'Loading...';
            
            try {
                // Simulate network call using Store logic
                const start = Date.now();
                
                // Wait for configured latency
                await new Promise(r => setTimeout(r, this.config.mockLatency));
                
                // Simulate error
                if (Math.random() * 100 < this.config.mockErrorRate) {
                    throw new Error('Simulated 500 Internal Server Error');
                }

                // Mock Responses based on path
                let data = {};
                if (this.selectedEndpoint.path === '/agents') {
                    data = this.$store.agents;
                } else if (this.selectedEndpoint.path === '/dashboard/metrics') {
                    data = this.$store.metrics;
                } else {
                    data = { success: true, message: 'Operation accepted' };
                }

                this.responseBody = JSON.stringify(data, null, 2);
                this.responseStatus = 200;
                
            } catch (e) {
                this.responseBody = JSON.stringify({ error: e.message }, null, 2);
                this.responseStatus = 500;
            } finally {
                this.executing = false;
            }
        }
    }
};
