// Copilot.js - 智能副驾驶核心组件
import ActionCard from '../CopilotPlugins/ActionCard.js';
import ChartRender from '../CopilotPlugins/ChartRender.js';
import { markdown } from '../../utils/markdown.js';

export default {
    props: ['context'],
    components: { ActionCard, ChartRender },
    template: `
        <div class="flex flex-col h-full overflow-hidden">
            <!-- Header -->
            <div class="h-12 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4 bg-gray-50 dark:bg-dark-lighter shrink-0">
                <div class="flex items-center space-x-2">
                    <span class="text-xl">🤖</span>
                    <span class="font-bold text-sm">OpenClaw Copilot</span>
                </div>
                <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" title="Close (Esc)">✕</button>
            </div>

            <!-- Messages Area -->
            <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="msgContainer">
                <!-- Welcome Message -->
                <div class="flex items-start space-x-2">
                    <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-lg flex-shrink-0">🤖</div>
                    <div class="bg-gray-100 dark:bg-gray-700 rounded-lg rounded-tl-none p-3 text-sm max-w-[85%] text-gray-800 dark:text-gray-200">
                        {{ $t('copilot.welcome') }}
                    </div>
                </div>

                <!-- Chat History -->
                <div v-for="(msg, idx) in messages" :key="idx" class="flex items-start space-x-2" :class="{'flex-row-reverse space-x-reverse': msg.role === 'user'}">
                    <div 
                        class="w-8 h-8 rounded-full flex items-center justify-center text-lg flex-shrink-0"
                        :class="msg.role === 'user' ? 'bg-indigo-100' : 'bg-blue-100'">
                        {{ msg.role === 'user' ? '👤' : '🤖' }}
                    </div>
                    
                    <div 
                        class="rounded-lg p-3 text-sm max-w-[85%] overflow-hidden shadow-sm"
                        :class="msg.role === 'user' ? 'bg-primary text-white rounded-tr-none' : 'bg-gray-100 dark:bg-gray-700 rounded-tl-none'">
                        
                        <!-- Text Content (Markdown) -->
                        <div v-if="msg.content" 
                             class="prose dark:prose-invert prose-sm max-w-none" 
                             :class="{'text-white': msg.role === 'user'}"
                             v-html="renderMarkdown(msg.content)">
                        </div>
                        <div v-if="msg.streaming" class="typing-cursor inline-block w-2 h-4 align-middle"></div>

                        <!-- Plugins -->
                        <div v-if="msg.plugins && msg.plugins.length > 0" class="mt-2 space-y-2">
                            <div v-for="(plugin, pIdx) in msg.plugins" :key="pIdx">
                                <action-card 
                                    v-if="plugin.type === 'action'" 
                                    :action="plugin.data">
                                </action-card>
                                <chart-render 
                                    v-if="plugin.type === 'chart'" 
                                    :config="plugin.data">
                                </chart-render>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Prompts -->
            <div class="px-4 pb-2 bg-white dark:bg-dark-lighter shrink-0" v-if="messages.length < 3">
                <div class="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                    <button 
                        v-for="prompt in quickPrompts" 
                        :key="prompt"
                        @click="usePrompt(prompt)"
                        class="whitespace-nowrap px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-300 transition-colors border border-gray-200 dark:border-gray-700">
                        {{ prompt }}
                    </button>
                </div>
            </div>

            <!-- Input Area -->
            <div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-lighter shrink-0">
                <div class="relative">
                    <textarea 
                        ref="inputArea"
                        v-model="input" 
                        @keydown.enter.prevent="sendMessage"
                        rows="1"
                        class="w-full pl-4 pr-12 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary resize-none text-gray-900 dark:text-gray-100 placeholder-gray-400"
                        :placeholder="$t('copilot.placeholder')">
                    </textarea>
                    <button 
                        @click="sendMessage" 
                        :disabled="!input.trim() || loading"
                        class="absolute right-2 top-2 p-1.5 bg-primary text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                        </svg>
                    </button>
                </div>
                <div class="mt-2 flex space-x-2 overflow-x-auto pb-1 text-xs text-gray-500">
                    <span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded cursor-pointer hover:bg-gray-200 transition-colors">Context: {{ context.view }}</span>
                    <span v-if="context.selected" class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded cursor-pointer hover:bg-gray-200 transition-colors">Agent: {{ context.selected }}</span>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            input: '',
            messages: [],
            loading: false
        };
    },
    computed: {
        quickPrompts() {
            const common = ['Help', 'System Status'];
            const map = {
                'dashboard': ['Analysis', 'Show Alerts', 'Export Report'],
                'agent_pool': ['Scale Up', 'Show Errors', 'Optimize Costs'],
                'governance': ['Audit Log', 'Pending Approvals', 'Risk Report'],
                'orchestrator': ['New Workflow', 'Debug Flow', 'Show Templates']
            };
            return [...(map[this.context.view] || []), ...common];
        }
    },
    mounted() {
        // Auto focus input when opened
        this.$nextTick(() => this.$refs.inputArea?.focus());
    },
    methods: {
        renderMarkdown(text) {
            return markdown.render(text);
        },
        usePrompt(text) {
            this.input = text;
            this.sendMessage();
        },
        async sendMessage() {
            if (!this.input.trim() || this.loading) return;
            
            const userMsg = { role: 'user', content: this.input };
            this.messages.push(userMsg);
            this.input = '';
            this.loading = true;

            this.$nextTick(() => this.scrollToBottom());

            const aiMsg = { role: 'assistant', content: '', streaming: true, plugins: [] };
            this.messages.push(aiMsg);

            await this.$api.chatStream(
                this.messages.slice(0, -1),
                this.context,
                (chunk) => {
                    // Plugin parsing logic
                    if (chunk.includes('<action>')) {
                        try {
                            const match = chunk.match(/<action>(.*?)<\/action>/);
                            if (match) {
                                aiMsg.plugins.push({
                                    type: 'action',
                                    data: JSON.parse(match[1])
                                });
                                chunk = chunk.replace(match[0], '');
                            }
                        } catch (e) { console.error('Plugin parse error', e); }
                    }
                    // Chart parsing logic
                    if (chunk.includes('<chart>')) {
                        try {
                            const match = chunk.match(/<chart>(.*?)<\/chart>/);
                            if (match) {
                                aiMsg.plugins.push({
                                    type: 'chart',
                                    data: JSON.parse(match[1])
                                });
                                chunk = chunk.replace(match[0], '');
                            }
                        } catch (e) { console.error('Chart parse error', e); }
                    }
                    
                    aiMsg.content += chunk;
                    this.scrollToBottom();
                },
                () => {
                    aiMsg.streaming = false;
                    this.loading = false;
                }
            );
        },
        scrollToBottom() {
            const container = this.$refs.msgContainer;
            if (container) container.scrollTop = container.scrollHeight;
        }
    }
};
