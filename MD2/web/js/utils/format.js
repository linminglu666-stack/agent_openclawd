// format.js - 格式化工具

export const format = {
    /**
     * 格式化数字
     * @param {number} num 
     * @param {number} digits 小数位数
     */
    number(num, digits = 0) {
        if (num === undefined || num === null) return '-';
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits
        }).format(num);
    },

    /**
     * 格式化日期时间
     * @param {string|number|Date} date 
     * @param {string} style 'short' | 'medium' | 'long' | 'full'
     */
    datetime(date, style = 'medium') {
        if (!date) return '-';
        const d = new Date(date);
        return new Intl.DateTimeFormat('zh-CN', {
            dateStyle: style,
            timeStyle: style === 'short' ? 'short' : 'medium'
        }).format(d);
    },

    /**
     * 格式化相对时间 (如 "5分钟前")
     * @param {string|number|Date} date 
     */
    timeAgo(date) {
        if (!date) return '-';
        const d = new Date(date);
        const now = new Date();
        const diff = (now - d) / 1000; // seconds

        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}天前`;
        
        return this.datetime(date, 'short');
    },

    /**
     * 格式化时长 (如 "1h 30m")
     * @param {number} seconds 
     */
    duration(seconds) {
        if (!seconds) return '0s';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        const parts = [];
        if (h > 0) parts.push(`${h}h`);
        if (m > 0) parts.push(`${m}m`);
        if (s > 0 || parts.length === 0) parts.push(`${s}s`);
        
        return parts.join(' ');
    },

    /**
     * 截断字符串
     * @param {string} str 
     * @param {number} len 
     */
    truncate(str, len = 50) {
        if (!str) return '';
        if (str.length <= len) return str;
        return str.substring(0, len) + '...';
    }
};
