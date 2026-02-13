// Timeline.js - 瀑布流时间线
export default {
    props: ['trace'],
    template: `
        <div class="w-full h-full overflow-y-auto bg-white dark:bg-dark-lighter p-4 rounded-lg">
            <div class="relative min-h-[300px]">
                <!-- Time Axis -->
                <div class="flex border-b border-gray-200 dark:border-gray-700 pb-2 mb-2 sticky top-0 bg-white dark:bg-dark-lighter z-10">
                    <div class="w-1/4 text-xs text-gray-500 font-mono">Span Name</div>
                    <div class="w-3/4 relative h-4">
                        <div class="absolute left-0 text-xs text-gray-400">0ms</div>
                        <div class="absolute right-0 text-xs text-gray-400">{{ totalDuration }}ms</div>
                    </div>
                </div>
                
                <!-- Spans -->
                <div v-for="span in flattenedSpans" :key="span.id" class="flex items-center hover:bg-gray-50 dark:hover:bg-gray-800 py-1 group rounded">
                    <div class="w-1/4 text-xs truncate px-2" :style="{ paddingLeft: (span.depth * 12 + 8) + 'px' }">
                        <span class="mr-1">{{ getIcon(span.type) }}</span>
                        {{ span.name }}
                    </div>
                    <div class="w-3/4 relative h-6">
                        <div 
                            class="absolute h-4 rounded text-[10px] text-white flex items-center justify-center overflow-hidden whitespace-nowrap transition-all hover:h-5 hover:-top-0.5 shadow-sm"
                            :class="getColor(span.type)"
                            :style="{ 
                                left: getLeft(span.start) + '%', 
                                width: Math.max(0.5, getWidth(span.duration)) + '%' 
                            }"
                            :title="span.duration + 'ms'">
                            <span v-if="getWidth(span.duration) > 5">{{ span.duration }}ms</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    computed: {
        totalDuration() {
            return this.trace ? this.trace.duration : 1000;
        },
        flattenedSpans() {
            if (!this.trace || !this.trace.root) return [];
            const result = [];
            const traverse = (node, depth) => {
                result.push({ ...node, depth });
                if (node.children) {
                    node.children.forEach(c => traverse(c, depth + 1));
                }
            };
            traverse(this.trace.root, 0);
            return result;
        }
    },
    methods: {
        getLeft(start) {
            return (start / this.totalDuration) * 100;
        },
        getWidth(duration) {
            return (duration / this.totalDuration) * 100;
        },
        getColor(type) {
            const map = {
                'thought': 'bg-blue-400',
                'action': 'bg-green-500',
                'tool': 'bg-purple-500',
                'observation': 'bg-gray-400'
            };
            return map[type] || 'bg-blue-400';
        },
        getIcon(type) {
            const map = {
                'thought': '💭',
                'action': '⚡',
                'tool': '🛠️',
                'observation': '👁️'
            };
            return map[type] || '•';
        }
    }
};
