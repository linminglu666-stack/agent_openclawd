
import { charts } from '../../utils/charts.js';

export default {
    template: `
        <div class="space-y-6">
            <!-- Header -->
            <div class="flex justify-between items-center">
                <div>
                    <h2 class="text-lg font-bold text-gray-900 dark:text-white">Entropy Governance V2</h2>
                    <p class="text-sm text-gray-500">Monitor system entropy across 6 dimensions</p>
                </div>
                <div class="flex space-x-2">
                    <button @click="refresh" class="px-3 py-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-sm">
                        Refresh
                    </button>
                    <button @click="showConfig = !showConfig" class="px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded text-sm">
                        Configure
                    </button>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Radar Chart -->
                <div class="bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <h3 class="font-medium text-gray-700 dark:text-gray-200 mb-4">Entropy Distribution</h3>
                    <div ref="radarChart" class="h-64 w-full"></div>
                </div>

                <!-- Trend Chart -->
                <div class="bg-white dark:bg-dark-lighter p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <h3 class="font-medium text-gray-700 dark:text-gray-200 mb-4">Entropy Trend (24h)</h3>
                    <div ref="trendChart" class="h-64 w-full"></div>
                </div>
            </div>

            <!-- Metrics Detail Grid -->
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div v-for="(metric, key) in metricsList" :key="key" 
                    class="bg-white dark:bg-dark-lighter p-3 rounded-lg border border-gray-100 dark:border-gray-700 flex flex-col items-center justify-center">
                    <span class="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">{{ key }}</span>
                    <span class="text-xl font-bold" :class="getScoreColor(metric.score)">{{ (metric.score * 100).toFixed(0) }}</span>
                    <span class="text-xs text-gray-400 mt-1">Threshold: {{ config[key + '_threshold'] || 0.7 }}</span>
                </div>
            </div>

            <!-- Config Panel -->
            <div v-if="showConfig" class="bg-gray-50 dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700">
                <h3 class="font-bold mb-4">Threshold Configuration</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div v-for="(val, key) in config" :key="key" class="flex items-center justify-between">
                        <label class="text-sm font-medium">{{ key.replace('_threshold', '').toUpperCase() }}</label>
                        <input type="range" min="0" max="1" step="0.1" v-model.number="config[key]" class="w-1/2">
                        <span class="text-sm w-8">{{ val }}</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            showConfig: false,
            radarInstance: null,
            trendInstance: null,
            pollInterval: null
        }
    },
    computed: {
        metrics() {
            return this.$store.entropy.metrics || {};
        },
        history() {
            return this.$store.entropy.history || [];
        },
        config() {
            return this.$store.entropy.config;
        },
        metricsList() {
            const list = {};
            ['input', 'evolution', 'observability', 'structure', 'behavior', 'data'].forEach(k => {
                if (this.metrics[k]) list[k] = this.metrics[k];
            });
            return list;
        }
    },
    watch: {
        metrics: {
            handler() {
                this.updateCharts();
            },
            deep: true
        }
    },
    mounted() {
        this.refresh();
        this.initCharts();
        this.pollInterval = setInterval(() => {
            this.refresh();
        }, 5000);
    },
    beforeUnmount() {
        if (this.pollInterval) clearInterval(this.pollInterval);
        if (this.radarInstance) this.radarInstance.dispose();
        if (this.trendInstance) this.trendInstance.dispose();
    },
    methods: {
        async refresh() {
            try {
                // Try to fetch real data
                if (this.$api) {
                    const metrics = await this.$api.getEntropyMetrics();
                    if (metrics && metrics.by_category) {
                        this.$store.setEntropyMetrics(metrics);
                        // Convert API format to history if needed, or fetch history
                        const history = await this.$api.getEntropyHistory();
                        if (history && history.entries) {
                            this.$store.setEntropyHistory(history.entries);
                        }
                        return;
                    }
                }
                // Fallback to mock
                this.$store.refreshEntropyData();
            } catch (e) {
                console.warn("API unavailable, using mock", e);
                this.$store.refreshEntropyData();
            }
        },
        getScoreColor(score) {
            if (score > 0.8) return 'text-red-500';
            if (score > 0.5) return 'text-yellow-500';
            return 'text-green-500';
        },
        initCharts() {
            // Init Radar
            if (this.$refs.radarChart) {
                this.radarInstance = charts.init(this.$refs.radarChart);
            }
            // Init Trend
            if (this.$refs.trendChart) {
                this.trendInstance = charts.init(this.$refs.trendChart);
            }
            this.updateCharts();
        },
        updateCharts() {
            if (!this.radarInstance || !this.trendInstance) return;

            // Update Radar
            const indicators = Object.keys(this.metricsList).map(k => ({
                name: k.toUpperCase(),
                max: 1
            }));
            const dataValues = Object.keys(this.metricsList).map(k => this.metricsList[k].score);
            
            this.radarInstance.setOption(charts.radar({
                indicators,
                data: [{ value: dataValues, name: 'Current Entropy' }]
            }));

            // Update Trend
            const timestamps = this.history.map(h => {
                const d = new Date(h.timestamp);
                return `${d.getHours()}:${d.getMinutes()}:${d.getSeconds()}`;
            });
            const seriesData = this.history.map(h => h.metrics.total_score);

            this.trendInstance.setOption(charts.line({
                labels: timestamps,
                series: [{
                    name: 'Total Entropy',
                    data: seriesData,
                    areaStyle: { opacity: 0.2 }
                }]
            }));
        }
    }
}
