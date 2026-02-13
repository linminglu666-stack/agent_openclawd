// Settings.js - 设置弹窗内容
export default {
    template: `
        <div class="space-y-6">
            <!-- Profile Section -->
            <div class="flex items-center space-x-4 pb-6 border-b border-gray-200 dark:border-gray-700">
                <div class="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white flex items-center justify-center text-2xl font-bold shadow-lg">
                    {{ user.name ? user.name[0].toUpperCase() : 'A' }}
                </div>
                <div>
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">{{ user.name }}</h3>
                    <p class="text-sm text-gray-500">{{ user.roles.join(', ') }}</p>
                </div>
            </div>

            <!-- Settings Form -->
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Display Name</label>
                    <input v-model="form.name" type="text" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-dark focus:ring-2 focus:ring-primary outline-none">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">API Key</label>
                    <div class="flex space-x-2">
                        <input type="password" value="sk-xxxxxxxxxxxxxxxx" readonly class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-500 cursor-not-allowed">
                        <button class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">Regenerate</button>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Notifications</label>
                    <div class="space-y-2">
                        <label class="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" v-model="form.notif.email" class="rounded text-primary focus:ring-primary">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Email Alerts</span>
                        </label>
                        <label class="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" v-model="form.notif.slack" class="rounded text-primary focus:ring-primary">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Slack Integration</span>
                        </label>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            form: {
                name: this.$store.user.name,
                notif: {
                    email: true,
                    slack: false
                }
            }
        };
    },
    computed: {
        user() {
            return this.$store.user;
        }
    },
    methods: {
        save() {
            // Update store
            this.$store.user.name = this.form.name;
            this.$store.addNotification('Settings saved successfully', 'success');
            this.$emit('close');
        }
    }
};
