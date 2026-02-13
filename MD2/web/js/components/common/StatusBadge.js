export default {
    props: ['status'],
    template: `
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" :class="classes">
            <span class="w-2 h-2 rounded-full mr-1.5" :class="dotClasses"></span>
            {{ $t('status.' + status) }}
        </span>
    `,
    computed: {
        classes() {
            const map = {
                running: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                idle: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
                error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
                pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
                stopped: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
            };
            return map[this.status] || map.idle;
        },
        dotClasses() {
            const map = {
                running: 'bg-green-400',
                idle: 'bg-gray-400',
                error: 'bg-red-400',
                pending: 'bg-yellow-400',
                stopped: 'bg-gray-500'
            };
            return map[this.status] || map.idle;
        }
    }
};
