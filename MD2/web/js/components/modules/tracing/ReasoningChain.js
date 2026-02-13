// ReasoningChain.js - 推理链视图
export default {
    props: ['trace'],
    template: `
        <div class="space-y-4 p-4">
            <div v-for="(step, idx) in steps" :key="idx" class="border-l-2 border-gray-200 dark:border-gray-700 pl-4 relative pb-6 last:pb-0">
                <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full border-2 border-white dark:border-dark bg-gray-300 dark:bg-gray-600"></div>
                
                <div class="bg-white dark:bg-dark-lighter p-4 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm">
                    <div class="flex justify-between items-start mb-2">
                        <span class="px-2 py-0.5 rounded text-xs font-bold uppercase" :class="getBadgeClass(step.type)">
                            {{ step.type }}
                        </span>
                        <span class="text-xs text-gray-400 font-mono">{{ step.duration }}ms</span>
                    </div>
                    <h4 class="font-bold text-gray-900 dark:text-white text-sm mb-1">{{ step.name }}</h4>
                    <div class="text-sm text-gray-600 dark:text-gray-300 font-mono bg-gray-50 dark:bg-gray-800 p-2 rounded overflow-x-auto">
                        {{ step.content || 'No content' }}
                    </div>
                </div>
            </div>
        </div>
    `,
    computed: {
        steps() {
            if (!this.trace || !this.trace.root) return [];
            // Flatten trace for linear view
            const result = [];
            const traverse = (node) => {
                result.push({
                    type: node.type,
                    name: node.name,
                    duration: node.duration,
                    content: `Executed ${node.name} with params...` // Mock content
                });
                if (node.children) node.children.forEach(traverse);
            };
            traverse(this.trace.root);
            return result;
        }
    },
    methods: {
        getBadgeClass(type) {
            const map = {
                'thought': 'bg-blue-100 text-blue-800',
                'action': 'bg-green-100 text-green-800',
                'tool': 'bg-purple-100 text-purple-800',
                'error': 'bg-red-100 text-red-800'
            };
            return map[type] || 'bg-gray-100 text-gray-800';
        }
    }
};
