// EvalGate.js - 评估门
export default {
    template: `
        <div class="space-y-6">
            <!-- Header Status -->
            <div class="flex items-center justify-between p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl">
                <div class="flex items-center space-x-4">
                    <div class="p-3 bg-yellow-100 dark:bg-yellow-800 rounded-full">
                        <span class="text-2xl">🛡️</span>
                    </div>
                    <div>
                        <h3 class="font-bold text-yellow-800 dark:text-yellow-200 text-lg">Truth Gate Active</h3>
                        <p class="text-sm text-yellow-700 dark:text-yellow-300">Validating high-impact actions against Ground Truth database.</p>
                    </div>
                </div>
                <div class="text-right hidden sm:block">
                    <div class="text-2xl font-bold text-yellow-800 dark:text-yellow-200">98.5%</div>
                    <div class="text-xs text-yellow-700 dark:text-yellow-300 uppercase font-bold tracking-wider">Pass Rate</div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="border-b border-gray-200 dark:border-gray-700">
                <nav class="-mb-px flex space-x-8">
                    <button 
                        @click="currentTab = 'live'"
                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
                        :class="currentTab === 'live' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300'">
                        Live Events
                    </button>
                    <button 
                        @click="currentTab = 'rules'"
                        class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
                        :class="currentTab === 'rules' ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:hover:text-gray-300'">
                        Rules Config
                    </button>
                </nav>
            </div>

            <!-- Live Events Tab -->
            <transition name="fade" mode="out-in">
                <div v-if="currentTab === 'live'" key="live" class="bg-white dark:bg-dark-lighter rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead class="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Request ID</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Eval Score</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Result</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                                <transition-group name="list">
                                    <tr v-for="eval in evals" :key="eval.id" class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                        <td class="px-6 py-4 text-sm font-mono text-gray-500">{{ eval.id }}</td>
                                        <td class="px-6 py-4 text-sm font-medium">{{ eval.action }}</td>
                                        <td class="px-6 py-4 text-sm">
                                            <div class="flex items-center space-x-2">
                                                <div class="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                                    <div class="h-1.5 rounded-full transition-all duration-500" 
                                                        :class="getScoreColor(eval.score)"
                                                        :style="{ width: (eval.score * 100) + '%' }">
                                                    </div>
                                                </div>
                                                <span class="text-xs font-mono">{{ eval.score }}</span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4">
                                            <span class="px-2 py-0.5 text-xs rounded-full font-bold uppercase" 
                                                :class="eval.pass ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'">
                                                {{ eval.pass ? 'PASS' : 'BLOCK' }}
                                            </span>
                                        </td>
                                        <td class="px-6 py-4 text-sm text-gray-500">{{ eval.reason }}</td>
                                    </tr>
                                </transition-group>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Rules Config Tab -->
                <div v-else key="rules" class="space-y-4">
                    <div class="flex justify-end">
                        <button @click="addRule" class="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                            + Add Rule
                        </button>
                    </div>
                    <div class="grid gap-4">
                        <div v-for="(rule, idx) in rules" :key="idx" class="bg-white dark:bg-dark-lighter p-4 rounded-xl border border-gray-200 dark:border-gray-700 flex items-start space-x-4">
                            <div class="flex-1 space-y-2">
                                <div class="flex items-center space-x-2">
                                    <span class="px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 text-xs rounded font-mono">REGEX</span>
                                    <input v-model="rule.pattern" class="flex-1 bg-transparent border-b border-gray-200 dark:border-gray-700 focus:border-primary outline-none font-mono text-sm py-1" placeholder="Pattern...">
                                </div>
                                <div class="flex items-center space-x-2">
                                    <span class="px-2 py-0.5 bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 text-xs rounded font-mono">ACTION</span>
                                    <select v-model="rule.action" class="bg-transparent border-b border-gray-200 dark:border-gray-700 focus:border-primary outline-none text-sm py-1">
                                        <option value="block">Block</option>
                                        <option value="flag">Flag</option>
                                        <option value="require_approval">Require Approval</option>
                                    </select>
                                </div>
                            </div>
                            <button @click="removeRule(idx)" class="text-gray-400 hover:text-red-500">🗑️</button>
                        </div>
                    </div>
                </div>
            </transition>
        </div>
    `,
    data() {
        return {
            currentTab: 'live',
            evals: [
                { id: 'req-abc-123', action: 'Delete Database', score: 0.1, pass: false, reason: 'High Risk / Low Confidence' },
                { id: 'req-def-456', action: 'Restart Service', score: 0.95, pass: true, reason: 'Safe / Routine' },
                { id: 'req-ghi-789', action: 'Update Config', score: 0.88, pass: true, reason: 'Validated against schema' },
            ],
            rules: [
                { pattern: '^DROP TABLE.*', action: 'block' },
                { pattern: '.*password.*', action: 'flag' },
                { pattern: '^sudo rm -rf.*', action: 'require_approval' }
            ]
        };
    },
    mounted() {
        // Simulate live events
        this.timer = setInterval(() => {
            if (Math.random() > 0.7) this.addMockEvent();
        }, 3000);
    },
    beforeUnmount() {
        clearInterval(this.timer);
    },
    methods: {
        getScoreColor(score) {
            if (score < 0.5) return 'bg-red-500';
            if (score < 0.8) return 'bg-yellow-500';
            return 'bg-green-500';
        },
        addMockEvent() {
            const actions = ['Read Log', 'Write File', 'Delete Pod', 'Update Schema', 'Scale Cluster'];
            const action = actions[Math.floor(Math.random() * actions.length)];
            const score = parseFloat(Math.random().toFixed(2));
            const pass = score > 0.4;
            
            this.evals.unshift({
                id: `req-${Math.random().toString(36).substr(2, 6)}`,
                action: action,
                score: score,
                pass: pass,
                reason: pass ? 'Within safety bounds' : 'Policy violation detected'
            });
            
            if (this.evals.length > 10) this.evals.pop();
        },
        addRule() {
            this.rules.push({ pattern: '', action: 'flag' });
        },
        removeRule(idx) {
            this.rules.splice(idx, 1);
        }
    }
};
