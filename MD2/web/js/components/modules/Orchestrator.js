// Orchestrator.js - 编排中心
import CodeEditor from '../common/CodeEditor.js';

export default {
    components: { CodeEditor },
    template: `
        <div class="h-full flex flex-col">
            <!-- Toolbar -->
            <div class="h-14 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-lighter flex items-center justify-between px-4 shrink-0">
                <div class="flex items-center space-x-4">
                    <h2 class="font-bold text-gray-800 dark:text-white">Workflow Editor</h2>
                    <div class="flex space-x-2">
                        <button class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">Load</button>
                        <button class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">Save</button>
                    </div>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="text-xs text-gray-500" v-if="lastSaved">Last saved: {{ lastSaved }}</span>
                    <button 
                        @click="runWorkflow"
                        :disabled="running"
                        class="px-4 py-2 bg-success text-white rounded hover:bg-green-600 flex items-center shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                        <span v-if="!running" class="mr-2">▶</span>
                        <span v-else class="mr-2 animate-spin">⟳</span>
                        {{ running ? 'Running...' : 'Run' }}
                    </button>
                </div>
            </div>

            <!-- Main Area -->
            <div class="flex-1 flex overflow-hidden">
                <!-- Sidebar Tools -->
                <div class="w-56 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-dark p-4 overflow-y-auto shrink-0 hidden md:block">
                    <h3 class="text-xs font-bold text-gray-500 uppercase mb-3">Nodes</h3>
                    <div class="space-y-2">
                        <div 
                            v-for="node in nodeTypes" 
                            :key="node.type" 
                            draggable="true"
                            @dragstart="onDragStart($event, node)"
                            class="p-3 bg-white dark:bg-dark-lighter border border-gray-200 dark:border-gray-600 rounded cursor-move shadow-sm text-sm hover:border-primary hover:shadow transition-all flex items-center">
                            <span class="mr-2">{{ node.icon }}</span>
                            {{ node.label }}
                        </div>
                    </div>
                    
                    <div class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 text-xs text-blue-600 dark:text-blue-300 rounded border border-blue-100 dark:border-blue-800">
                        ℹ️ Drag nodes to editor to insert
                    </div>

                    <h3 class="text-xs font-bold text-gray-500 uppercase mt-6 mb-3">Templates</h3>
                    <div class="space-y-2">
                        <button v-for="tpl in templates" :key="tpl.name" @click="loadTemplate(tpl)" class="w-full text-left p-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors">
                            {{ tpl.name }}
                        </button>
                    </div>
                </div>

                <!-- Editor & Preview Split -->
                <div class="flex-1 flex flex-col md:flex-row min-w-0">
                    <!-- Code Editor (Left/Top) -->
                    <div class="flex-1 flex flex-col border-b md:border-b-0 md:border-r border-gray-200 dark:border-gray-700 min-h-[300px]">
                        <div class="h-8 bg-gray-100 dark:bg-gray-800 flex items-center px-4 border-b border-gray-200 dark:border-gray-700">
                            <span class="text-xs font-mono text-gray-500">definition.mermaid</span>
                        </div>
                        <div class="flex-1 relative">
                            <code-editor 
                                ref="editor"
                                v-model="graphDef" 
                                class="absolute inset-0"
                                @update:modelValue="debouncedRender"
                                @drop="onEditorDrop">
                            </code-editor>
                        </div>
                    </div>

                    <!-- Graph Preview (Right/Bottom) -->
                    <div class="flex-1 bg-gray-50 dark:bg-gray-900 relative flex flex-col min-h-[300px]">
                        <div class="h-8 bg-gray-100 dark:bg-gray-800 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
                            <span class="text-xs font-mono text-gray-500">Preview</span>
                            <div class="flex space-x-2">
                                <button @click="zoomIn" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs">+</button>
                                <button @click="zoomOut" class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xs">-</button>
                            </div>
                        </div>
                        <div class="flex-1 overflow-auto flex items-center justify-center p-4" ref="graphContainer">
                             <div 
                                v-html="mermaidSvg" 
                                class="transform transition-transform duration-200 origin-center"
                                :style="{ transform: 'scale(' + zoomLevel + ')' }">
                             </div>
                             <div v-if="renderError" class="absolute bottom-4 left-4 right-4 bg-red-100 text-red-700 p-3 rounded text-sm border border-red-200">
                                {{ renderError }}
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            nodeTypes: [
                { type: 'start', label: 'Start', icon: '🟢', snippet: 'S[Start]' },
                { type: 'task', label: 'Task Agent', icon: '🤖', snippet: 'T[Task Name]' },
                { type: 'condition', label: 'Condition', icon: '🔷', snippet: 'C{Condition?}' },
                { type: 'human', label: 'Human Approval', icon: '👤', snippet: 'H[Approval]' },
                { type: 'end', label: 'End', icon: '🔴', snippet: 'E[End]' }
            ],
            templates: [
                { name: 'Data ETL', def: 'graph TD\nS[Start] --> E[Extract]\nE --> T[Transform]\nT --> L[Load]\nL --> End[End]' },
                { name: 'Approval Flow', def: 'graph TD\nReq[Request] --> Check{Valid?}\nCheck -->|Yes| App[Approval]\nCheck -->|No| Rej[Reject]\nApp --> Done[Done]' }
            ],
            graphDef: `graph TD
    A[Start] --> B(Data Collection)
    B --> C{Quality Check}
    C -->|Pass| D[Analysis]
    C -->|Fail| E[Alert Human]
    D --> F[Report Gen]
    F --> G[End]`,
            mermaidSvg: '',
            renderError: null,
            running: false,
            lastSaved: null,
            zoomLevel: 1,
            debounceTimer: null
        };
    },
    mounted() {
        this.renderGraph();
    },
    methods: {
        onDragStart(event, node) {
            event.dataTransfer.setData('text/plain', node.snippet);
            event.dataTransfer.effectAllowed = 'copy';
        },
        onEditorDrop(event) {
            const snippet = event.dataTransfer.getData('text/plain');
            if (snippet && this.$refs.editor) {
                // Insert with a newline and arrow if graph not empty
                const prefix = this.graphDef.trim() ? '\n    --> ' : '';
                this.$refs.editor.insertText(prefix + snippet);
            }
        },
        loadTemplate(tpl) {
            if (confirm('Replace current workflow?')) {
                this.graphDef = tpl.def;
                this.renderGraph();
            }
        },
        debouncedRender() {
            if (this.debounceTimer) clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.renderGraph();
            }, 500);
        },
        async renderGraph() {
            try {
                this.renderError = null;
                // Unique ID for mermaid to avoid conflicts
                const id = 'mermaid-' + Date.now();
                mermaid.initialize({ 
                    startOnLoad: false, 
                    theme: this.$root.isDark ? 'dark' : 'default',
                    securityLevel: 'loose'
                });
                
                const { svg } = await mermaid.render(id, this.graphDef);
                this.mermaidSvg = svg;
            } catch (e) {
                console.error(e);
                this.renderError = 'Syntax Error: ' + e.message;
            }
        },
        async runWorkflow() {
            this.running = true;
            this.$store.addNotification('Workflow started...', 'info');
            
            // Simulate execution
            await new Promise(r => setTimeout(r, 2000));
            
            this.running = false;
            this.$store.addNotification('Workflow completed successfully.', 'success');
            this.lastSaved = new Date().toLocaleTimeString();
        },
        zoomIn() {
            this.zoomLevel = Math.min(this.zoomLevel + 0.1, 2);
        },
        zoomOut() {
            this.zoomLevel = Math.max(this.zoomLevel - 0.1, 0.5);
        }
    }
};
