// GrowthLoop.js - 成长循环
import { charts } from '../../utils/charts.js';

export default {
    template: `
        <div class="space-y-6">
            <!-- Header Stats & Radar -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Stats Cards -->
                <div class="lg:col-span-2 space-y-6">
                    <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                        <div class="flex justify-between items-center mb-6">
                            <h2 class="text-xl font-bold text-gray-900 dark:text-white">Skill Acquisition</h2>
                            <button @click="startTraining" :disabled="training" class="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors">
                                {{ training ? 'Training in progress...' : 'Start Idle Training' }}
                            </button>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-800 relative overflow-hidden group">
                                <div class="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                    <span class="text-6xl">🎓</span>
                                </div>
                                <div class="relative z-10">
                                    <div class="text-3xl font-bold text-green-600 dark:text-green-400">12</div>
                                    <div class="text-sm text-green-800 dark:text-green-200 mt-1">New Skills (This Week)</div>
                                </div>
                            </div>
                            <div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800 relative overflow-hidden group">
                                <div class="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                    <span class="text-6xl">📈</span>
                                </div>
                                <div class="relative z-10">
                                    <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">85%</div>
                                    <div class="text-sm text-blue-800 dark:text-blue-200 mt-1">Success Rate Improvement</div>
                                </div>
                            </div>
                            <div class="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-100 dark:border-purple-800 relative overflow-hidden group">
                                <div class="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                    <span class="text-6xl">⏳</span>
                                </div>
                                <div class="relative z-10">
                                    <div class="text-3xl font-bold text-purple-600 dark:text-purple-400">1.5h</div>
                                    <div class="text-sm text-purple-800 dark:text-purple-200 mt-1">Idle Training Time</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Training Progress (Visible when training) -->
                    <transition name="fade">
                        <div v-if="training" class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                            <h3 class="font-bold text-sm text-gray-500 mb-2">TRAINING PROGRESS</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between text-sm">
                                    <span>Simulating scenario: "Database Failover"</span>
                                    <span>{{ progress }}%</span>
                                </div>
                                <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                                    <div class="bg-primary h-2 rounded-full transition-all duration-300" :style="{ width: progress + '%' }"></div>
                                </div>
                                <p class="text-xs text-gray-400">Generating synthetic logs... Validating recovery steps...</p>
                            </div>
                        </div>
                    </transition>
                </div>

                <!-- Radar Chart -->
                <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col">
                    <h3 class="font-bold text-gray-900 dark:text-white mb-4">Capability Radar</h3>
                    <div ref="radarChart" class="flex-1 min-h-[250px]"></div>
                </div>
            </div>

            <!-- Timeline -->
            <div class="bg-white dark:bg-dark-lighter p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <h3 class="font-bold mb-6 text-gray-900 dark:text-white">Learning Timeline</h3>
                <div class="relative pl-8 border-l-2 border-gray-200 dark:border-gray-700 space-y-8">
                    <div v-for="item in logs" :key="item.id" class="relative">
                        <!-- Dot -->
                        <span 
                            class="absolute -left-[39px] w-5 h-5 rounded-full border-4 border-white dark:border-dark-lighter"
                            :class="getDotColor(item.type)">
                        </span>
                        
                        <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between group">
                            <div class="flex-1">
                                <h4 class="text-base font-semibold text-gray-900 dark:text-white group-hover:text-primary transition-colors">
                                    {{ item.title }}
                                </h4>
                                <p class="text-sm text-gray-500 mt-1">{{ item.desc }}</p>
                                <div class="mt-2 flex items-center space-x-2">
                                    <span class="text-xs font-mono text-gray-400">{{ item.time }}</span>
                                    <span v-if="item.xp" class="text-xs font-bold text-green-500">+{{ item.xp }} XP</span>
                                </div>
                            </div>
                            <div class="mt-2 sm:mt-0">
                                <span class="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 uppercase font-bold tracking-wider">
                                    {{ item.type }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            training: false,
            progress: 0,
            chartInstance: null,
            logs: [
                { id: 1, type: 'discovery', title: 'Learned "Kubernetes Debugging"', desc: 'Analyzed 50+ error logs from k8s cluster and synthesized a new troubleshooting protocol.', time: '2 hours ago', xp: 150 },
                { id: 2, type: 'optimization', title: 'Optimized SQL Query Generation', desc: 'Refined prompt strategy for SQL generation based on feedback, reducing syntax errors by 40%.', time: 'Yesterday', xp: 80 },
                { id: 3, type: 'tool', title: 'New Tool: AWS Cost Explorer', desc: 'Successfully integrated and tested new tool definition for AWS cost analysis.', time: '2 days ago', xp: 200 },
                { id: 4, type: 'correction', title: 'Fixed "Loop Condition" Bug', desc: 'Self-corrected infinite loop in pagination logic after 3 failed attempts.', time: '3 days ago', xp: 50 }
            ]
        };
    },
    computed: {
        isDark() {
            return this.$root.isDark;
        }
    },
    watch: {
        isDark() {
            this.updateChart();
        }
    },
    mounted() {
        this.initChart();
    },
    beforeUnmount() {
        if (this.chartInstance) this.chartInstance.dispose();
    },
    methods: {
        initChart() {
            this.chartInstance = charts.init(this.$refs.radarChart, this.isDark);
            this.updateChart();
        },
        updateChart() {
            if (!this.chartInstance) return;
            this.chartInstance.setOption(charts.radar({
                indicators: [
                    { name: 'Coding', max: 100 },
                    { name: 'Reasoning', max: 100 },
                    { name: 'Search', max: 100 },
                    { name: 'Memory', max: 100 },
                    { name: 'Safety', max: 100 }
                ],
                data: [
                    {
                        value: [85, 90, 75, 60, 95],
                        name: 'Current Level'
                    }
                ]
            }, this.isDark));
        },
        getDotColor(type) {
            const map = {
                'discovery': 'bg-blue-500',
                'optimization': 'bg-green-500',
                'tool': 'bg-purple-500',
                'correction': 'bg-red-500'
            };
            return map[type] || 'bg-gray-400';
        },
        startTraining() {
            this.training = true;
            this.progress = 0;
            const interval = setInterval(() => {
                this.progress += 5;
                if (this.progress >= 100) {
                    clearInterval(interval);
                    this.training = false;
                    this.logs.unshift({
                        id: Date.now(),
                        type: 'simulation',
                        title: 'Completed "Database Failover" Sim',
                        desc: 'Successfully recovered from simulated primary DB failure in 45s.',
                        time: 'Just now',
                        xp: 120
                    });
                    this.$store.addNotification('Training session completed!', 'success');
                }
            }, 100);
        }
    }
};
