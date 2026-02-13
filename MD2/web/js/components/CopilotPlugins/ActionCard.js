// ActionCard.js - 聊天中的可操作卡片
export default {
    props: ['action'],
    template: `
        <div class="mt-2 p-3 bg-white dark:bg-dark border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <span class="text-xl" v-if="action.type === 'approve'">✅</span>
                    <span class="text-xl" v-if="action.type === 'reject'">❌</span>
                    <span class="text-xl" v-if="action.type === 'retry'">🔄</span>
                    <span class="font-medium text-sm">{{ action.title }}</span>
                </div>
                <button 
                    @click="execute" 
                    :disabled="loading || executed"
                    class="px-3 py-1 text-xs font-medium rounded transition-colors"
                    :class="btnClass">
                    {{ executed ? '已执行' : (loading ? '执行中...' : '立即执行') }}
                </button>
            </div>
            <div class="mt-1 text-xs text-gray-500" v-if="action.reason">
                理由: {{ action.reason }}
            </div>
        </div>
    `,
    data() {
        return {
            loading: false,
            executed: false
        };
    },
    computed: {
        btnClass() {
            if (this.executed) return 'bg-gray-100 text-gray-400 cursor-not-allowed';
            if (this.action.type === 'approve') return 'bg-green-100 text-green-700 hover:bg-green-200';
            if (this.action.type === 'reject') return 'bg-red-100 text-red-700 hover:bg-red-200';
            return 'bg-blue-100 text-blue-700 hover:bg-blue-200';
        }
    },
    methods: {
        async execute() {
            this.loading = true;
            try {
                // Call API based on action
                // await this.$api.post('/actions', this.action.payload);
                await new Promise(r => setTimeout(r, 1000)); // Mock
                this.executed = true;
                this.$emit('executed', this.action);
            } catch (err) {
                console.error(err);
            } finally {
                this.loading = false;
            }
        }
    }
};
