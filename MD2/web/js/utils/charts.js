// charts.js - ECharts 封装工具
// 依赖 echarts

export const charts = {
    /**
     * 初始化图表
     * @param {HTMLElement} dom 容器元素
     * @param {boolean} isDark 是否暗色模式
     * @returns {Object} ECharts 实例
     */
    init(dom, isDark = false) {
        if (!dom) return null;
        const theme = isDark ? 'dark' : undefined;
        const chart = echarts.init(dom, theme);
        
        // 自动监听 resize
        const resizeHandler = () => chart.resize();
        window.addEventListener('resize', resizeHandler);
        
        // 绑定销毁方法以移除监听
        chart._dispose = chart.dispose;
        chart.dispose = () => {
            window.removeEventListener('resize', resizeHandler);
            chart._dispose();
        };
        
        return chart;
    },

    /**
     * 获取通用基础配置
     * @param {boolean} isDark 
     */
    getBaseOption(isDark) {
        const textColor = isDark ? '#cbd5e1' : '#334155';
        const gridColor = isDark ? '#334155' : '#e2e8f0';
        
        return {
            backgroundColor: 'transparent',
            textStyle: {
                fontFamily: 'Inter, system-ui, sans-serif'
            },
            title: {
                textStyle: { color: textColor }
            },
            legend: {
                textStyle: { color: textColor }
            },
            tooltip: {
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.9)',
                borderColor: gridColor,
                textStyle: { color: textColor },
                padding: [8, 12],
                extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-radius: 0.5rem;'
            },
            grid: {
                top: 40,
                right: 20,
                bottom: 24,
                left: 40,
                containLabel: true,
                borderColor: gridColor
            },
            categoryAxis: {
                axisLine: { lineStyle: { color: gridColor } },
                axisLabel: { color: textColor },
                splitLine: { show: false }
            },
            valueAxis: {
                axisLine: { show: false },
                axisLabel: { color: textColor },
                splitLine: { 
                    show: true, 
                    lineStyle: { color: gridColor, type: 'dashed' } 
                }
            }
        };
    },

    /**
     * 生成折线图配置
     * @param {Object} options 数据与覆盖配置
     * @param {boolean} isDark 
     */
    line(options, isDark) {
        const base = this.getBaseOption(isDark);
        return {
            ...base,
            tooltip: { trigger: 'axis', ...base.tooltip },
            xAxis: { 
                type: 'category', 
                data: options.labels, 
                ...base.categoryAxis 
            },
            yAxis: { 
                type: 'value', 
                ...base.valueAxis 
            },
            series: options.series.map(s => ({
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                itemStyle: { borderWidth: 2 },
                areaStyle: { opacity: 0.1 },
                ...s
            }))
        };
    },

    /**
     * 生成饼图配置
     * @param {Object} options 
     * @param {boolean} isDark 
     */
    pie(options, isDark) {
        const base = this.getBaseOption(isDark);
        return {
            ...base,
            tooltip: { trigger: 'item', ...base.tooltip },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                itemStyle: {
                    borderRadius: 5,
                    borderColor: isDark ? '#0f172a' : '#fff',
                    borderWidth: 2
                },
                label: { show: false },
                data: options.data
            }]
        };
    },

    /**
     * 生成雷达图配置
     * @param {Object} options 
     * @param {boolean} isDark 
     */
    radar(options, isDark) {
        const base = this.getBaseOption(isDark);
        const splitLineColor = isDark ? '#334155' : '#e2e8f0';
        const textColor = isDark ? '#cbd5e1' : '#64748b';

        return {
            ...base,
            tooltip: { ...base.tooltip },
            radar: {
                indicator: options.indicators,
                splitArea: { show: false },
                splitLine: {
                    lineStyle: { color: splitLineColor }
                },
                axisLine: {
                    lineStyle: { color: splitLineColor }
                },
                axisName: {
                    color: textColor,
                    fontWeight: '500'
                }
            },
            series: [{
                type: 'radar',
                data: options.data.map(d => ({
                    value: d.value,
                    name: d.name,
                    symbol: 'none',
                    lineStyle: { width: 2 },
                    areaStyle: { opacity: 0.2 }
                }))
            }]
        };
    }
};
