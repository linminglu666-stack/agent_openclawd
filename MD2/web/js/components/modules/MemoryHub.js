// MemoryHub.js - 记忆中心
export default {
    template: `
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-[500px]">
            <!-- Search & Filter (Top on mobile, full width) -->
            <div class="lg:col-span-12 bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col sm:flex-row gap-4">
                <div class="relative flex-1">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">🔍</span>
                    <input 
                        v-model="searchQuery" 
                        @input="onSearch"
                        type="text" 
                        placeholder="Search knowledge base..." 
                        class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 focus:ring-2 focus:ring-primary outline-none transition-shadow">
                </div>
                <select 
                    v-model="layerFilter"
                    class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 focus:ring-2 focus:ring-primary outline-none cursor-pointer">
                    <option value="all">All Layers</option>
                    <option value="L1">L1 (Short-term)</option>
                    <option value="L2">L2 (Working)</option>
                    <option value="L3">L3 (Long-term)</option>
                    <option value="L4">L4 (Archived)</option>
                </select>
                <button 
                    @click="search(true)"
                    class="px-6 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors shadow-sm"
                    :disabled="searching">
                    {{ searching ? 'Searching...' : 'Search' }}
                </button>
            </div>

            <!-- Stats (Left Column) -->
            <div class="lg:col-span-3 space-y-4">
                <div class="bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <h3 class="font-bold mb-3 text-gray-900 dark:text-white">Memory Stats</h3>
                    <div class="space-y-3 text-sm">
                        <div class="flex justify-between items-center">
                            <span class="text-gray-500">Total Entries</span>
                            <span class="font-medium font-mono">14,203</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-500">Embeddings</span>
                            <span class="font-medium font-mono">1.2 GB</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-500">Daily Drift</span>
                            <span class="text-green-500 font-medium">0.02%</span>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <h3 class="font-bold mb-3 text-gray-900 dark:text-white">Layers</h3>
                    <div class="space-y-2">
                        <div class="h-10 bg-blue-50 dark:bg-blue-900/20 rounded flex items-center px-3 text-xs font-medium text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-800">
                            <span class="w-2 h-2 rounded-full bg-blue-500 mr-2"></span>
                            L1: 5 mins (Active)
                        </div>
                        <div class="h-10 bg-indigo-50 dark:bg-indigo-900/20 rounded flex items-center px-3 text-xs font-medium text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800">
                            <span class="w-2 h-2 rounded-full bg-indigo-500 mr-2"></span>
                            L2: 1 hour (Context)
                        </div>
                        <div class="h-10 bg-purple-50 dark:bg-purple-900/20 rounded flex items-center px-3 text-xs font-medium text-purple-700 dark:text-purple-300 border border-purple-100 dark:border-purple-800">
                            <span class="w-2 h-2 rounded-full bg-purple-500 mr-2"></span>
                            L3: Persistent (Knowledge)
                        </div>
                        <div class="h-10 bg-gray-50 dark:bg-gray-800 rounded flex items-center px-3 text-xs font-medium text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                            <span class="w-2 h-2 rounded-full bg-gray-500 mr-2"></span>
                            L4: Archive (Cold)
                        </div>
                    </div>
                </div>

                <div class="bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                     <h3 class="font-bold mb-3 text-gray-900 dark:text-white">Popular Tags</h3>
                     <div class="flex flex-wrap gap-2">
                        <span v-for="tag in popularTags" :key="tag" 
                            class="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 text-xs rounded-md cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                            @click="addTagFilter(tag)">
                            #{{ tag }}
                        </span>
                     </div>
                </div>
            </div>

            <!-- Content List (Right Column) -->
            <div class="lg:col-span-9 bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col h-[600px]">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="font-bold text-gray-900 dark:text-white">Results</h3>
                    <span class="text-xs text-gray-400">{{ filteredMemories.length }} items</span>
                </div>
                
                <div class="flex-1 overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                    <transition-group name="list">
                        <div 
                            v-for="mem in filteredMemories" 
                            :key="mem.id" 
                            class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary/50 dark:hover:border-primary/50 transition-all cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 group">
                            <div class="flex justify-between items-start mb-2">
                                <span class="px-2 py-0.5 text-xs rounded uppercase font-bold tracking-wider" :class="getLayerBadgeClass(mem.layer)">{{ mem.layer }}</span>
                                <span class="text-xs text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">{{ mem.time }}</span>
                            </div>
                            <p class="text-sm text-gray-800 dark:text-gray-200 line-clamp-2 leading-relaxed mb-3">{{ mem.content }}</p>
                            <div class="flex items-center justify-between">
                                <div class="flex space-x-2">
                                    <span v-for="tag in mem.tags" :key="tag" class="text-xs text-blue-500 hover:text-blue-600 cursor-pointer">#{{ tag }}</span>
                                </div>
                                <div class="flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button class="text-xs text-gray-500 hover:text-primary">Edit</button>
                                    <button class="text-xs text-gray-500 hover:text-red-500">Delete</button>
                                </div>
                            </div>
                        </div>
                    </transition-group>
                    
                    <div v-if="filteredMemories.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400">
                        <span class="text-3xl mb-2">📭</span>
                        <p>No memories found.</p>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            searchQuery: '',
            layerFilter: 'all',
            searching: false,
            debounceTimer: null,
            popularTags: ['performance', 'db', 'protocol', 'deployment', 'audit', 'security', 'api'],
            memories: [
                { id: 1, layer: 'L2', time: '10 mins ago', content: 'Observed high latency in service-A when concurrent requests > 1000. Potential bottleneck in DB connection pool.', tags: ['performance', 'db'] },
                { id: 2, layer: 'L3', time: '2 days ago', content: 'Deployment Protocol v2: Always run smoke tests before traffic switch. Rollback threshold is 1% error rate.', tags: ['protocol', 'deployment'] },
                { id: 3, layer: 'L1', time: 'Just now', content: 'User "admin" initiated manual override for workflow WF-123.', tags: ['audit'] },
                { id: 4, layer: 'L3', time: '3 days ago', content: 'Security Policy Update: All external API calls must include x-request-id header for tracing.', tags: ['security', 'api'] },
                { id: 5, layer: 'L2', time: '1 hour ago', content: 'Cache hit ratio dropped to 45% after deployment of v1.2.0. Investigating cache key generation logic.', tags: ['performance'] }
            ]
        };
    },
    computed: {
        filteredMemories() {
            return this.memories.filter(mem => {
                const matchesSearch = !this.searchQuery || 
                                    mem.content.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                                    mem.tags.some(t => t.toLowerCase().includes(this.searchQuery.toLowerCase()));
                const matchesLayer = this.layerFilter === 'all' || mem.layer === this.layerFilter;
                return matchesSearch && matchesLayer;
            });
        }
    },
    methods: {
        onSearch() {
            if (this.debounceTimer) clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.search();
            }, 300);
        },
        async search(force = false) {
            if (force) {
                this.searching = true;
                // Simulate API latency
                await new Promise(r => setTimeout(r, 600));
                this.searching = false;
            }
        },
        addTagFilter(tag) {
            this.searchQuery = tag;
            this.search(true);
        },
        getLayerBadgeClass(layer) {
            const map = {
                'L1': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
                'L2': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
                'L3': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
                'L4': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
            };
            return map[layer] || 'bg-gray-100 text-gray-800';
        }
    }
};
