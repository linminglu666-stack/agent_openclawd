// DecisionTree.js - 决策树可视化 (D3.js)
export default {
    props: ['data'],
    template: `
        <div ref="container" class="w-full h-full overflow-hidden bg-white dark:bg-dark-lighter rounded-lg relative">
            <svg ref="svg" class="w-full h-full cursor-grab active:cursor-grabbing"></svg>
            <div class="absolute bottom-4 right-4 flex space-x-2">
                <button @click="resetZoom" class="p-2 bg-white dark:bg-gray-800 rounded shadow hover:bg-gray-100 dark:hover:bg-gray-700">🔄</button>
            </div>
        </div>
    `,
    mounted() {
        this.initD3();
    },
    watch: {
        data: {
            handler() { this.updateChart(); },
            deep: true
        }
    },
    methods: {
        initD3() {
            if (!this.data) return;
            
            const width = this.$refs.container.clientWidth;
            const height = this.$refs.container.clientHeight;
            
            this.svg = d3.select(this.$refs.svg)
                .attr("viewBox", [-width / 2, -height / 2, width, height]);
                
            this.g = this.svg.append("g");
            
            this.zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on("zoom", (event) => {
                    this.g.attr("transform", event.transform);
                });
                
            this.svg.call(this.zoom);
            
            this.updateChart();
        },
        updateChart() {
            if (!this.data || !this.g) return;
            
            // Clear previous
            this.g.selectAll("*").remove();
            
            // Convert to hierarchy
            const root = d3.stratify()
                .id(d => d.id)
                .parentId(d => {
                    const edge = this.data.edges.find(e => e.to === d.id);
                    return edge ? edge.from : null;
                })(this.data.nodes);
                
            const treeLayout = d3.tree().nodeSize([150, 100]);
            treeLayout(root);
            
            // Links
            this.g.append("g")
                .attr("fill", "none")
                .attr("stroke", "#94a3b8")
                .attr("stroke-opacity", 0.4)
                .attr("stroke-width", 1.5)
                .selectAll("path")
                .data(root.links())
                .join("path")
                .attr("d", d3.linkVertical()
                    .x(d => d.x)
                    .y(d => d.y));
                    
            // Nodes
            const node = this.g.append("g")
                .selectAll("g")
                .data(root.descendants())
                .join("g")
                .attr("transform", d => `translate(${d.x},${d.y})`);
                
            // Node Circle
            node.append("circle")
                .attr("fill", d => d.data.is_selected ? "#3b82f6" : "#fff")
                .attr("stroke", d => d.data.is_selected ? "#2563eb" : "#94a3b8")
                .attr("stroke-width", 2)
                .attr("r", 6)
                .on("click", (event, d) => {
                    console.log("Clicked node", d.data);
                });
                
            // Labels
            node.append("text")
                .attr("dy", "0.31em")
                .attr("x", d => d.children ? -10 : 10)
                .attr("text-anchor", d => d.children ? "end" : "start")
                .text(d => d.data.label)
                .clone(true).lower()
                .attr("stroke", "white")
                .attr("stroke-width", 3);
        },
        resetZoom() {
            this.svg.transition().duration(750).call(this.zoom.transform, d3.zoomIdentity);
        }
    }
};
