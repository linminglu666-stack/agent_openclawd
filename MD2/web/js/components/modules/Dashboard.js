// Dashboard.js - 态势感知
import { charts } from '../../utils/charts.js';

export default {
    template: `
        <div class="space-y-6">
            <!-- Edit Mode Toggle -->
            <div class="flex justify-end">
                <button @click="editMode = !editMode" 
                    class="px-3 py-1 text-xs font-medium rounded-lg transition-colors flex items-center"
                    :class="editMode ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'">
                    <span class="mr-1">{{ editMode ? '✓ Done' : '⚙️ Customize' }}</span>
                </button>
            </div>

            <!-- Key Metrics -->
            <div 
                class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" 
                @dragover.prevent 
                @drop="onDropMetric">
                <div 
                    v-for="(metric, idx) in metrics" 
                    :key="metric.id" 
                    :draggable="editMode"
                    @dragstart="onDragStart($event, idx, 'metric')"
                    class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-all"
                    :class="{'cursor-move ring-2 ring-blue-400 ring-opacity-50 transform hover:scale-105': editMode, 'hover:-translate-y-1': !editMode}">
                    
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ metric.title }}</p>
                            <p class="text-2xl font-bold mt-1 text-gray-900 dark:text-white">{{ metric.value }}</p>
                        </div>
                        <div class="p-3 rounded-full" :class="metric.bgClass">
                            <span class="text-xl">{{ metric.icon }}</span>
                        </div>
                    </div>
                    <div class="mt-4 flex items-center text-sm">
                        <span :class="metric.trend > 0 ? 'text-green-500' : 'text-red-500'" class="font-medium">
                            {{ metric.trend > 0 ? '↑' : '↓' }} {{ Math.abs(metric.trend) }}%
                        </span>
                        <span class="ml-2 text-gray-400">vs yesterday</span>
                    </div>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 relative">
                    <h3 class="text-lg font-semibold mb-4 text-gray-800 dark:text-white">任务吞吐量 (Throughput)</h3>
                    <div ref="chart1" class="h-64 w-full"></div>
                    <div v-if="editMode" class="absolute inset-0 bg-white/50 dark:bg-black/50 flex items-center justify-center rounded-xl cursor-not-allowed">
                        <span class="text-sm font-bold text-gray-800 dark:text-white bg-white dark:bg-dark px-3 py-1 rounded shadow">Fixed Widget</span>
                    </div>
                </div>
                <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 relative">
                    <h3 class="text-lg font-semibold mb-4 text-gray-800 dark:text-white">Agent 资源分布</h3>
                    <div ref="chart2" class="h-64 w-full"></div>
                    <div v-if="editMode" class="absolute inset-0 bg-white/50 dark:bg-black/50 flex items-center justify-center rounded-xl cursor-not-allowed">
                         <span class="text-sm font-bold text-gray-800 dark:text-white bg-white dark:bg-dark px-3 py-1 rounded shadow">Fixed Widget</span>
                    </div>
                </div>
            </div>

            <!-- Recent Alerts -->
            <div class="bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
                    <h3 class="text-lg font-semibold text-gray-800 dark:text-white">最近告警 (Recent Alerts)</h3>
                    <button class="text-sm text-primary hover:underline">View All</button>
                </div>
                <transition-group name="list" tag="ul" class="divide-y divide-gray-100 dark:divide-gray-700">
                    <li v-for="alert in alerts" :key="alert.id" class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-3">
                                <span class="w-2 h-2 rounded-full" :class="alert.severity === 'high' ? 'bg-red-500' : 'bg-yellow-500'"></span>
                                <span class="font-medium text-gray-900 dark:text-gray-200">{{ alert.message }}</span>
                            </div>
                            <span class="text-sm text-gray-400">{{ alert.time }}</span>
                        </div>
                    </li>
                </transition-group>
            </div>
        </div>
    `,
    data() {
        return {
            editMode: false,
            metrics: [
                { id: 1, title: 'CPU Usage', value: '42%', trend: 12, icon: '🖥️', bgClass: 'bg-blue-50 dark:bg-blue-900/30 text-blue-500' },
                { id: 2, title: 'Active Agents', value: '8/12', trend: -5, icon: '🤖', bgClass: 'bg-green-50 dark:bg-green-900/30 text-green-500' },
                { id: 3, title: 'Pending Tasks', value: '24', trend: 8, icon: '⏳', bgClass: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-500' },
                { id: 4, title: 'Health Score', value: '98', trend: 1, icon: '❤️', bgClass: 'bg-purple-50 dark:bg-purple-900/30 text-purple-500' },
            ],
            alerts: [
                { id: 1, severity: 'high', message: 'Agent-007 connection timeout', time: '2 mins ago' },
                { id: 2, severity: 'medium', message: 'High memory usage on Worker-3', time: '15 mins ago' },
                { id: 3, severity: 'medium', message: 'API Gateway latency spike', time: '1 hour ago' },
            ],
            chartInstances: [],
            draggedIdx: null
        };
    },
    computed: {
        isDark() {
            return this.$root.isDark;
        }
    },
    watch: {
        isDark() {
            this.updateCharts();
        }
    },
    mounted() {
        this.initCharts();
    },
    beforeUnmount() {
        this.chartInstances.forEach(c => c.dispose());
    },
    methods: {
        initCharts() {
            const chart1 = charts.init(this.$refs.chart1, this.isDark);
            const chart2 = charts.init(this.$refs.chart2, this.isDark);
            this.chartInstances = [chart1, chart2];
            this.updateCharts();
        },
        updateCharts() {
            if (!this.chartInstances[0]) return;
            
            // Chart 1: Line
            this.chartInstances[0].setOption(charts.line({
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                series: [{ data: [120, 132, 101, 134, 90, 230, 210] }]
            }, this.isDark));

            // Chart 2: Pie
            this.chartInstances[1].setOption(charts.pie({
                data: [
                    { value: 1048, name: 'Search' },
                    { value: 735, name: 'Reasoning' },
                    { value: 580, name: 'Coding' },
                    { value: 484, name: 'Data' }
                ]
            }, this.isDark));
        },
        onDragStart(event, idx, type) {
            this.draggedIdx = idx;
            event.dataTransfer.effectAllowed = 'move';
        },
        onDropMetric(event) {
            if (!this.editMode) return;
            // Simple logic: move dragged item to the end (mock reorder)
            // In real app, calculate drop target index
            const item = this.metrics.splice(this.draggedIdx, 1)[0];
            this.metrics.push(item);
            this.draggedIdx = null;
        }
    }
};
