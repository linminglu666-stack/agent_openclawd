export default {
    props: ['modelValue', 'language'],
    emits: ['update:modelValue', 'drop'],
    template: `
        <div class="w-full h-full border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden font-mono text-sm bg-gray-50 dark:bg-gray-900"
             @dragover.prevent
             @drop.prevent="onDrop">
            <textarea
                ref="textarea"
                :value="modelValue"
                @input="$emit('update:modelValue', $event.target.value)"
                class="w-full h-full p-4 bg-transparent outline-none resize-none text-gray-800 dark:text-gray-200"
                spellcheck="false">
            </textarea>
        </div>
    `,
    methods: {
        onDrop(event) {
            this.$emit('drop', event);
        },
        insertText(text) {
            const textarea = this.$refs.textarea;
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const value = textarea.value;
            
            const newValue = value.substring(0, start) + text + value.substring(end);
            this.$emit('update:modelValue', newValue);
            
            // Restore cursor position
            this.$nextTick(() => {
                textarea.selectionStart = textarea.selectionEnd = start + text.length;
                textarea.focus();
            });
        }
    }
};
