// markdown.js - Markdown 渲染工具
// 依赖 marked.js

// 配置 marked
marked.setOptions({
    renderer: new marked.Renderer(),
    highlight: function(code, lang) {
        // 这里可以集成 highlight.js 或 prism.js
        // 目前返回原始内容，后续可扩展
        return code;
    },
    pedantic: false,
    gfm: true,
    breaks: true,
    sanitize: false,
    smartLists: true,
    smartypants: false,
    xhtml: false
});

export const markdown = {
    /**
     * 渲染 Markdown 文本为 HTML
     * @param {string} text Markdown 文本
     * @returns {string} HTML 字符串
     */
    render(text) {
        if (!text) return '';
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown parse error:', e);
            return text;
        }
    },

    /**
     * 渲染简单的单行 Markdown (去除段落标签)
     * @param {string} text 
     */
    renderInline(text) {
        if (!text) return '';
        const html = this.render(text);
        // 去除外层的 <p> 标签
        return html.replace(/^<p>|<\/p>\n?$/g, '');
    }
};
