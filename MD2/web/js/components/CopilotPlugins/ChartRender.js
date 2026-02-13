// ChartRender.js - 聊天中的图表渲染
export default {
    props: ['config'],
    template: `
        <div class="mt-2 w-full h-48 bg-white dark:bg-dark border border-gray-200 dark:border-gray-700 rounded-lg p-2" ref="chartRef"></div>
    `,
    mounted() {
        this.initChart();
    },
    methods: {
        initChart() {
            if (!this.$refs.chartRef) return;
            const chart = echarts.init(this.$refs.chartRef);
            chart.setOption(this.config);
            window.addEventListener('resize', () => chart.resize());
        }
    }
};
