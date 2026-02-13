// LoadingBar.js - 全局加载进度条
export default {
    props: ['loading'],
    template: `
        <div class="fixed top-0 left-0 right-0 z-[100] h-1 bg-transparent pointer-events-none" v-if="loading">
            <div class="h-full bg-primary animate-progress"></div>
        </div>
    `,
    styles: `
        @keyframes progress {
            0% { width: 0%; margin-left: 0%; }
            50% { width: 50%; margin-left: 25%; }
            100% { width: 100%; margin-left: 100%; }
        }
        .animate-progress {
            animation: progress 1.5s infinite linear;
        }
    `
};
