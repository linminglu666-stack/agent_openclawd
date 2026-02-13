// Tracing.js - 追踪探索主视图
import DecisionTree from './tracing/DecisionTree.js';
import Timeline from './tracing/Timeline.js';
import ReasoningChain from './tracing/ReasoningChain.js';
import ToTExplorer from './tracing/ToTExplorer.js';

export default {
    components: { DecisionTree, Timeline, ReasoningChain, ToTExplorer },
    template: `
        <div class="h-full flex flex-col">
            <!-- Header -->
            <div class="h-14 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-lighter flex items-center justify-between px-4 shrink-0">
                <div class="flex items-center space-x-4">
                    <h2 class="font-bold text-gray-800 dark:text-white">🔍 Trace Explorer</h2>
                    <select v-model="selectedTraceId" class="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-gray-50 dark:bg-gray-800 text-sm">
                        <option v-for="t in traces" :key="t.id" :value="t.id">{{ t.name }} ({{ t.status }})</option>
                    </select>
                    <div v-if="currentTrace" class="flex items-center space-x-2 text-xs text-gray-500">
                        <span>耗时: {{ currentTrace.total_duration_ms || 0 }}ms</span>
                        <span>|</span>
                        <span>Span: {{ currentTrace.span_count || 0 }}</span>
                    </div>
                </div>
                
                <!-- View Switcher -->
                <div class="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                    <button 
                        v-for="view in views" 
                        :key="view.id"
                        @click="currentView = view.id"
                        class="px-3 py-1 text-xs font-medium rounded-md transition-colors flex items-center space-x-1"
                        :class="currentView === view.id ? 'bg-white dark:bg-dark-lighter shadow text-primary' : 'text-gray-500 hover:text-gray-700'">
                        <span>{{ view.icon }}</span>
                        <span>{{ view.label }}</span>
                    </button>
                </div>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-hidden bg-gray-50 dark:bg-dark p-4">
                <div class="h-full bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden relative">
                    <!-- Loading State -->
                    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-dark-lighter/80 z-10">
                        <div class="flex flex-col items-center">
                            <div class="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                            <span class="mt-2 text-sm text-gray-500">加载追踪数据...</span>
                        </div>
                    </div>
                    
                    <!-- Empty State -->
                    <div v-if="!loading && traces.length === 0" class="absolute inset-0 flex items-center justify-center">
                        <div class="text-center">
                            <div class="text-4xl mb-4">📭</div>
                            <h3 class="font-bold text-gray-700 dark:text-gray-300 mb-2">暂无追踪数据</h3>
                            <p class="text-sm text-gray-500">执行任务后将自动生成追踪记录</p>
                        </div>
                    </div>
                    
                    <!-- View Content -->
                    <transition name="fade" mode="out-in">
                        <component 
                            v-if="!loading && traces.length > 0"
                            :is="currentViewComponent" 
                            :data="currentViewData"
                            :trace="currentTrace"
                            @node-select="onNodeSelect"
                            class="h-full w-full">
                        </component>
                    </transition>
                </div>
            </div>
            
            <!-- Footer Status Bar -->
            <div class="h-10 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-lighter flex items-center justify-between px-4 text-xs text-gray-500">
                <div class="flex items-center space-x-4">
                    <span>策略: <strong class="text-primary">{{ currentTrace?.reasoning_strategy || 'N/A' }}</strong></span>
                    <span>模型: <strong>{{ currentTrace?.model || 'N/A' }}</strong></span>
                </div>
                <div class="flex items-center space-x-2">
                    <button @click="refreshTrace" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded" title="刷新">
                        🔄
                    </button>
                    <button @click="exportTrace" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded" title="导出">
                        📥
                    </button>
                    <button @click="openInNewTab" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded" title="新窗口打开">
                        🔗
                    </button>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            selectedTraceId: null,
            currentView: 'timeline',
            loading: false,
            views: [
                { id: 'timeline', label: 'Timeline', icon: '⏱️' },
                { id: 'tree', label: 'Decision Tree', icon: '🎯' },
                { id: 'chain', label: 'Reasoning Chain', icon: '🔗' },
                { id: 'tot', label: 'ToT Explorer', icon: '🌳' }
            ]
        };
    },
    computed: {
        traces() {
            return this.$store?.traces || [];
        },
        currentTrace() {
            if (!this.traces.length) return null;
            return this.traces.find(t => t.id === this.selectedTraceId) || this.traces[0];
        },
        currentViewComponent() {
            const map = {
                'timeline': 'timeline',
                'tree': 'decision-tree',
                'chain': 'reasoning-chain',
                'tot': 'to-t-explorer'
            };
            return map[this.currentView] || 'timeline';
        },
        currentViewData() {
            if (!this.currentTrace) return { nodes: [], edges: [], selected_path: [] };
            
            switch (this.currentView) {
                case 'tree':
                case 'tot':
                    return this.treeData;
                case 'timeline':
                case 'chain':
                default:
                    return this.currentTrace;
            }
        },
        treeData() {
            if (!this.currentTrace) return { nodes: [], edges: [], selected_path: [] };
            
            if (this.currentTrace.decision_tree) {
                return this.currentTrace.decision_tree;
            }
            
            if (this.currentTrace.spans && this.currentTrace.spans.length > 0) {
                const nodes = this.currentTrace.spans.map(span => ({
                    id: span.span_id || span.id,
                    label: span.name,
                    content: span.name,
                    depth: span.depth || 0,
                    confidence: span.confidence || 0,
                    is_selected: span.status === 'completed'
                }));
                
                const edges = this.currentTrace.spans
                    .filter(span => span.parent_id)
                    .map(span => ({
                        from: span.parent_id,
                        to: span.span_id || span.id,
                        selected: span.status === 'completed'
                    }));
                
                return {
                    nodes,
                    edges,
                    selected_path: nodes.filter(n => n.is_selected).map(n => n.id)
                };
            }
            
            return {
                nodes: [
                    { id: 'root', label: '开始', content: '推理起点', depth: 0, confidence: 1.0, is_selected: true },
                    { id: 'n1', label: '问题分析', content: '分析用户问题', depth: 1, confidence: 0.85, is_selected: false },
                    { id: 'n2', label: '策略选择', content: '选择推理策略', depth: 1, confidence: 0.9, is_selected: true },
                    { id: 'n3', label: '知识检索', content: '检索相关知识', depth: 2, confidence: 0.88, is_selected: true },
                    { id: 'n4', label: '答案生成', content: '生成最终答案', depth: 2, confidence: 0.92, is_selected: true }
                ],
                edges: [
                    { from: 'root', to: 'n1', selected: false },
                    { from: 'root', to: 'n2', selected: true },
                    { from: 'n2', to: 'n3', selected: true },
                    { from: 'n2', to: 'n4', selected: true }
                ],
                selected_path: ['root', 'n2', 'n3', 'n4']
            };
        }
    },
    watch: {
        traces: {
            handler(val) {
                if (val.length > 0 && !this.selectedTraceId) {
                    this.selectedTraceId = val[0].id;
                }
            },
            immediate: true
        }
    },
    methods: {
        onNodeSelect(node) {
            console.log('Node selected:', node);
            this.$emit('node-select', node);
        },
        async refreshTrace() {
            if (!this.selectedTraceId) return;
            this.loading = true;
            try {
                await this.$store?.fetchTrace?.(this.selectedTraceId);
            } finally {
                setTimeout(() => { this.loading = false; }, 300);
            }
        },
        exportTrace() {
            if (!this.currentTrace) return;
            const data = JSON.stringify(this.currentTrace, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trace-${this.currentTrace.id || 'export'}.json`;
            a.click();
            URL.revokeObjectURL(url);
        },
        openInNewTab() {
            if (!this.selectedTraceId) return;
            window.open(`/tracing/${this.selectedTraceId}`, '_blank');
        }
    }
};
