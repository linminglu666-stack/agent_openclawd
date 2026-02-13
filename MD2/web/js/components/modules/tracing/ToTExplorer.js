// ToTExplorer.js - Tree of Thought 思维树探索视图
export default {
    props: ['data'],
    template: `
        <div class="w-full h-full flex flex-col bg-white dark:bg-dark-lighter rounded-lg">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div>
                    <h3 class="font-bold text-gray-900 dark:text-white">🌳 Tree of Thought</h3>
                    <p class="text-xs text-gray-500">探索多路径推理过程</p>
                </div>
                <div class="flex space-x-2">
                    <button @click="expandAll" class="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
                        展开全部
                    </button>
                    <button @click="collapseAll" class="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
                        收起全部
                    </button>
                    <button @click="showOnlySelected" class="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
                        仅显示选中
                    </button>
                </div>
            </div>
            
            <!-- Tree Canvas -->
            <div ref="canvas" class="flex-1 overflow-auto p-4">
                <div v-if="treeData.nodes.length === 0" class="flex items-center justify-center h-full text-gray-400">
                    暂无思维树数据
                </div>
                <div v-else class="relative min-w-max">
                    <!-- Levels -->
                    <div v-for="(level, levelIdx) in levels" :key="levelIdx" class="flex items-start mb-8">
                        <div class="w-32 shrink-0 text-right pr-4">
                            <div class="text-xs font-bold text-gray-400">Level {{ levelIdx }}</div>
                            <div class="text-xs text-gray-500">{{ level.label }}</div>
                        </div>
                        <div class="flex-1 flex flex-wrap gap-4">
                            <div 
                                v-for="node in level.nodes" 
                                :key="node.id"
                                @click="selectNode(node)"
                                class="relative group cursor-pointer"
                            >
                                <!-- Node Card -->
                                <div 
                                    class="w-48 p-3 rounded-lg border-2 transition-all duration-200"
                                    :class="getNodeClass(node)">
                                    <div class="flex items-center justify-between mb-2">
                                        <span class="text-xs font-bold" :class="node.is_selected ? 'text-blue-600' : 'text-gray-500'">
                                            {{ node.is_selected ? '✓ SELECTED' : 'OPTION' }}
                                        </span>
                                        <span class="text-xs px-1.5 py-0.5 rounded"
                                            :class="getScoreClass(node.confidence)">
                                            {{ (node.confidence * 10).toFixed(1) }}
                                        </span>
                                    </div>
                                    <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">
                                        {{ node.label }}
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                                        {{ node.content }}
                                    </div>
                                </div>
                                
                                <!-- Connector Line -->
                                <div v-if="levelIdx > 0" class="absolute -left-4 top-1/2 w-4 h-0.5 bg-gray-300 dark:bg-gray-600"></div>
                                
                                <!-- Selected Path Indicator -->
                                <div v-if="node.is_selected" class="absolute -left-6 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-blue-500"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Footer Stats -->
            <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <div class="flex space-x-4 text-xs">
                    <span class="text-gray-500">总节点: <strong class="text-gray-900 dark:text-white">{{ treeData.nodes.length }}</strong></span>
                    <span class="text-gray-500">选中路径: <strong class="text-blue-600">{{ treeData.selected_path?.length || 0 }}</strong></span>
                </div>
                <div class="flex space-x-2">
                    <button class="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600">
                        导出决策报告
                    </button>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            expandedNodes: new Set(),
            showOnlySelectedMode: false
        };
    },
    computed: {
        treeData() {
            return this.data || { nodes: [], edges: [], selected_path: [] };
        },
        levels() {
            const result = [];
            const nodesByDepth = {};
            
            this.treeData.nodes.forEach(node => {
                if (!nodesByDepth[node.depth]) {
                    nodesByDepth[node.depth] = [];
                }
                if (!this.showOnlySelectedMode || node.is_selected) {
                    nodesByDepth[node.depth].push(node);
                }
            });
            
            const depthLabels = ['问题', '策略', '方案', '执行', '结果'];
            
            Object.keys(nodesByDepth).sort((a, b) => a - b).forEach((depth, idx) => {
                result.push({
                    depth: parseInt(depth),
                    label: depthLabels[depth] || `阶段${depth}`,
                    nodes: nodesByDepth[depth]
                });
            });
            
            return result;
        }
    },
    methods: {
        getNodeClass(node) {
            if (node.is_selected) {
                return 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-lg shadow-blue-500/20';
            }
            return 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600';
        },
        getScoreClass(score) {
            if (score >= 0.8) return 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300';
            if (score >= 0.6) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300';
            return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
        },
        selectNode(node) {
            this.$emit('node-select', node);
        },
        expandAll() {
            this.expandedNodes = new Set(this.treeData.nodes.map(n => n.id));
        },
        collapseAll() {
            this.expandedNodes.clear();
        },
        showOnlySelected() {
            this.showOnlySelectedMode = !this.showOnlySelectedMode;
        }
    }
};
