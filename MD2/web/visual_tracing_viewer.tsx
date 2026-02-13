/**
 * OpenClaw-X 可视化追踪系统 - React前端组件
 * 使用 D3.js 进行决策树和思维树可视化
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';

// ============================================
// 类型定义
// ============================================

interface ThoughtNode {
  id: string;
  name: string;
  type: string;
  status: string;
  duration_ms: number;
  depth: number;
  parent_id?: string;
}

interface TraceEvent {
  event_id: string;
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  timestamp: number;
  event_type: string;
  agent_id: string;
  node: ThoughtNode;
  data: Record<string, any>;
  metadata: Record<string, any>;
}

interface DecisionTreeNode {
  id: string;
  label: string;
  type: string;
  depth: number;
  confidence: number;
  is_selected: boolean;
  content: string;
}

interface DecisionTreeEdge {
  from: string;
  to: string;
  selected: boolean;
}

interface ReasoningStep {
  step_id: number;
  action: string;
  prompt: string;
  response: string;
  duration_ms: number;
  confidence: number;
}

interface WaterfallSpan {
  id: string;
  name: string;
  type: string;
  start_ms: number;
  duration_ms: number;
  depth: number;
  parent_id?: string;
  status: string;
  confidence: number;
}

// ============================================
// 决策树视图组件
// ============================================

interface DecisionTreeViewProps {
  treeData: {
    nodes: DecisionTreeNode[];
    edges: DecisionTreeEdge[];
    selected_path: string[];
  };
  onNodeClick?: (nodeId: string) => void;
}

export const DecisionTreeView: React.FC<DecisionTreeViewProps> = ({ 
  treeData, 
  onNodeClick 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const handleResize = () => {
      if (svgRef.current?.parentElement) {
        setDimensions({
          width: svgRef.current.parentElement.clientWidth,
          height: 600
        });
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!svgRef.current || !treeData.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;
    const margin = { top: 40, right: 120, bottom: 40, left: 120 };

    // 构建层级数据
    const root = d3.hierarchy({
      id: 'root',
      children: treeData.nodes.filter(n => n.depth === 1).map(n => ({
        ...n,
        children: treeData.nodes.filter(c => c.depth === n.depth + 1)
      }))
    });

    const treeLayout = d3.tree<any>()
      .size([height - margin.top - margin.bottom, width - margin.left - margin.right])
      .separation((a, b) => a.parent === b.parent ? 1 : 1.5);

    const treeData_ = d3.hierarchy(treeData.nodes[0] || {});
    const treeNodes = treeLayout(treeData_);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // 绘制连线
    g.selectAll('.link')
      .data(treeNodes.links())
      .enter()
      .append('path')
      .attr('class', 'link')
      .attr('d', d3.linkHorizontal<any, any>()
        .x(d => d.y)
        .y(d => d.x))
      .attr('fill', 'none')
      .attr('stroke', d => {
        const targetId = d.target.data.id || d.target.data.node_id;
        return treeData.selected_path.includes(targetId) ? '#10B981' : '#E5E7EB';
      })
      .attr('stroke-width', 2);

    // 绘制节点
    const nodes = g.selectAll('.node')
      .data(treeNodes.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', d => `translate(${d.y},${d.x})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        const nodeId = d.data.id || d.data.node_id;
        onNodeClick?.(nodeId);
      });

    // 节点外圈
    nodes.append('circle')
      .attr('r', 24)
      .attr('fill', d => {
        const nodeId = d.data.id || d.data.node_id;
        const isSelected = treeData.selected_path.includes(nodeId);
        const isRoot = d.data.depth === 0;
        return isSelected ? '#10B981' : isRoot ? '#3B82F6' : '#8B5CF6';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 3);

    // 节点图标
    nodes.append('text')
      .attr('dy', 4)
      .attr('text-anchor', 'middle')
      .attr('fill', '#fff')
      .attr('font-size', '12px')
      .text(d => {
        const type = d.data.type;
        if (type === 'root') return '?';
        if (type === 'thought_branch') return '💭';
        if (type === 'decision') return '✓';
        return '•';
      });

    // 节点标签
    nodes.append('text')
      .attr('dy', 40)
      .attr('text-anchor', 'middle')
      .attr('fill', '#374151')
      .attr('font-size', '12px')
      .text(d => d.data.label?.substring(0, 12) || '');

    // 置信度
    nodes.append('text')
      .attr('dy', 54)
      .attr('text-anchor', 'middle')
      .attr('fill', '#6B7280')
      .attr('font-size', '10px')
      .text(d => d.data.confidence ? `${(d.data.confidence * 100).toFixed(0)}%` : '');

  }, [treeData, dimensions, onNodeClick]);

  return (
    <div className="decision-tree-view">
      <svg ref={svgRef} width="100%" height={dimensions.height} />
      <div className="legend">
        <span><span style={{color: '#3B82F6'}}>●</span> 根节点</span>
        <span><span style={{color: '#8B5CF6'}}>●</span> 思考分支</span>
        <span><span style={{color: '#10B981'}}>●</span> 选中路径</span>
      </div>
    </div>
  );
};

// ============================================
// 时间线/瀑布图视图组件
// ============================================

interface TimelineViewProps {
  waterfallData: {
    trace_id: string;
    total_duration_ms: number;
    spans: WaterfallSpan[];
  };
  onSpanClick?: (spanId: string) => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ 
  waterfallData, 
  onSpanClick 
}) => {
  const { spans, total_duration_ms } = waterfallData;

  const maxDepth = Math.max(...spans.map(s => s.depth), 0);
  const rowHeight = 40;
  const height = Math.max(300, (maxDepth + 2) * rowHeight);

  const colors: Record<string, string> = {
    thought: '#3B82F6',
    decision: '#8B5CF6',
    action: '#10B981',
    tool: '#F59E0B',
    memory: '#EC4899',
    synthesize: '#06B6D4'
  };

  return (
    <div className="timeline-view">
      <div className="timeline-header">
        <span>trace_id: {waterfallData.trace_id}</span>
        <span>总耗时: {(total_duration_ms / 1000).toFixed(2)}s</span>
      </div>
      <div className="timeline-ruler">
        {Array.from({ length: 11 }).map((_, i) => (
          <div key={i} className="ruler-mark" style={{ left: `${i * 10}%` }}>
            <span>{Math.round(total_duration_ms * i / 10)}ms</span>
          </div>
        ))}
      </div>
      <div className="timeline-spans" style={{ height }}>
        {spans.map((span) => {
          const left = (span.start_ms / total_duration_ms) * 100;
          const width = Math.max((span.duration_ms / total_duration_ms) * 100, 1);
          
          return (
            <div
              key={span.id}
              className={`timeline-bar ${span.status}`}
              style={{
                left: `${left}%`,
                width: `${width}%`,
                top: span.depth * rowHeight + 20,
                backgroundColor: colors[span.type] || '#6B7280'
              }}
              onClick={() => onSpanClick?.(span.id)}
              title={`${span.name}: ${span.duration_ms}ms`}
            >
              <span className="bar-label">{span.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================
// 推理链视图组件
// ============================================

interface ReasoningChainViewProps {
  chainData: {
    chain_type: string;
    steps: ReasoningStep[];
    total_duration_ms: number;
    model_info: {
      model: string;
      temperature: number;
      total_tokens: number;
    };
  };
}

export const ReasoningChainView: React.FC<ReasoningChainViewProps> = ({ chainData }) => {
  const { steps, model_info, total_duration_ms } = chainData;

  return (
    <div className="reasoning-chain-view">
      <div className="chain-header">
        <span className="badge">{chainData.chain_type.toUpperCase()}</span>
        <span>模型: {model_info.model}</span>
        <span>Tokens: {model_info.total_tokens}</span>
        <span>耗时: {total_duration_ms}ms</span>
      </div>
      
      <div className="chain-steps">
        {steps.map((step, index) => (
          <div key={step.step_id} className="chain-step">
            <div className="step-connector">
              <div className="step-line" />
              <div className="step-number">{index + 1}</div>
            </div>
            <div className="step-content">
              <div className="step-header">
                <span className="step-action">{step.action}</span>
                <span className="step-duration">{step.duration_ms}ms</span>
                <span className="step-confidence">
                  置信度: {(step.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="step-body">
                <div className="step-prompt">
                  <label>输入:</label>
                  <pre>{step.prompt.substring(0, 200)}...</pre>
                </div>
                <div className="step-response">
                  <label>输出:</label>
                  <pre>{step.response.substring(0, 300)}...</pre>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================
// ToT思维树探索视图组件
// ============================================

interface ToTExplorerProps {
  treeData: {
    nodes: DecisionTreeNode[];
    edges: DecisionTreeEdge[];
    selected_path: string[];
  };
  onPathSelect?: (path: string[]) => void;
}

export const ToTExplorer: React.FC<ToTExplorerProps> = ({ 
  treeData, 
  onPathSelect 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !treeData.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 900;
    const height = 500;
    const levels = d3.group(Array.from(treeData.nodes), d => d.depth);
    const maxLevel = Math.max(...levels.keys());

    const levelWidth = width / (maxLevel + 1);
    const nodeSpacing = height / (Math.max(...Array.from(levels.values()).map(v => v.length)) + 1);

    const g = svg.append('g').attr('transform', 'translate(40, 20)');

    // 绘制连线
    treeData.edges.forEach(edge => {
      const fromNode = treeData.nodes.find(n => n.id === edge.from);
      const toNode = treeData.nodes.find(n => n.id === edge.to);
      if (!fromNode || !toNode) return;

      const fromX = fromNode.depth * levelWidth;
      const fromY = (Array.from(levels.get(fromNode.depth) || []).indexOf(fromNode) + 1) * nodeSpacing;
      const toX = toNode.depth * levelWidth;
      const toY = (Array.from(levels.get(toNode.depth) || []).indexOf(toNode) + 1) * nodeSpacing;

      g.append('path')
        .attr('d', `M ${fromX} ${fromY} Q ${(fromX + toX) / 2} ${fromY} ${toX} ${toY}`)
        .attr('fill', 'none')
        .attr('stroke', edge.selected ? '#10B981' : '#D1D5DB')
        .attr('stroke-width', edge.selected ? 3 : 1.5);
    });

    // 绘制节点
    treeData.nodes.forEach((node, i) => {
      const x = node.depth * levelWidth;
      const levelNodes = levels.get(node.depth) || [];
      const y = (levelNodes.indexOf(node) + 1) * nodeSpacing;

      const isSelected = treeData.selected_path.includes(node.id);

      const nodeG = g.append('g')
        .attr('transform', `translate(${x}, ${y})`)
        .style('cursor', 'pointer');

      // 节点背景
      nodeG.append('rect')
        .attr('x', -50)
        .attr('y', -20)
        .attr('width', 100)
        .attr('height', 40)
        .attr('rx', 8)
        .attr('fill', isSelected ? '#10B981' : node.depth === 0 ? '#3B82F6' : '#F3F4F6')
        .attr('stroke', isSelected ? '#059669' : '#E5E7EB')
        .attr('stroke-width', 2);

      // 节点标签
      nodeG.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', 5)
        .attr('fill', isSelected || node.depth === 0 ? '#fff' : '#374151')
        .attr('font-size', '11px')
        .text(node.label.substring(0, 10));

      // 评估分数
      if (node.confidence > 0) {
        nodeG.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', 30)
          .attr('fill', '#6B7280')
          .attr('font-size', '10px')
          .text(`评估: ${(node.confidence * 10).toFixed(0)}`);
      }
    });

  }, [treeData]);

  return (
    <div className="tot-explorer">
      <svg ref={svgRef} width="100%" height={500} />
      <div className="tot-controls">
        <button>展开所有路径</button>
        <button>模拟评估</button>
        <button>导出决策报告</button>
      </div>
    </div>
  );
};

// ============================================
// 主追踪查看器组件
// ============================================

interface TraceViewerProps {
  traceId: string;
}

type ViewMode = 'decision-tree' | 'timeline' | 'reasoning-chain' | 'tot' | 'logs';

export const TraceViewer: React.FC<TraceViewerProps> = ({ traceId }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('decision-tree');
  const [traceData, setTraceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTraceData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/v1/traces/${traceId}`);
        const data = await response.json();
        setTraceData(data);
      } catch (error) {
        console.error('Failed to fetch trace:', error);
      }
      setLoading(false);
    };
    fetchTraceData();
  }, [traceId]);

  if (loading) {
    return <div className="trace-viewer-loading">Loading trace {traceId}...</div>;
  }

  return (
    <div className="trace-viewer">
      <div className="trace-viewer-header">
        <h2>🔍 Trace Explorer</h2>
        <span className="trace-id">trace_id: {traceId}</span>
      </div>

      <div className="view-tabs">
        {(['decision-tree', 'timeline', 'reasoning-chain', 'tot', 'logs'] as ViewMode[]).map(mode => (
          <button
            key={mode}
            className={viewMode === mode ? 'active' : ''}
            onClick={() => setViewMode(mode)}
          >
            {mode === 'decision-tree' && '🎯 决策树'}
            {mode === 'timeline' && '⏱️ 时间线'}
            {mode === 'reasoning-chain' && '🔗 推理链'}
            {mode === 'tot' && '🌳 ToT'}
            {mode === 'logs' && '📋 日志'}
          </button>
        ))}
      </div>

      <div className="trace-meta">
        <div className="meta-item">
          <label>状态:</label>
          <span className={`status ${traceData?.status}`}>{traceData?.status}</span>
        </div>
        <div className="meta-item">
          <label>Agent:</label>
          <span>{traceData?.agent_id}</span>
        </div>
        <div className="meta-item">
          <label>耗时:</label>
          <span>{traceData?.total_duration_ms}ms</span>
        </div>
        <div className="meta-item">
          <label>事件数:</label>
          <span>{traceData?.events_count}</span>
        </div>
      </div>

      <div className="view-content">
        {viewMode === 'decision-tree' && traceData?.decision_tree && (
          <DecisionTreeView 
            treeData={traceData.decision_tree}
            onNodeClick={(id) => console.log('Node clicked:', id)}
          />
        )}
        {viewMode === 'timeline' && traceData?.waterfall && (
          <TimelineView 
            waterfallData={traceData.waterfall}
            onSpanClick={(id) => console.log('Span clicked:', id)}
          />
        )}
        {viewMode === 'reasoning-chain' && traceData?.reasoning_chain && (
          <ReasoningChainView chainData={traceData.reasoning_chain} />
        )}
        {viewMode === 'tot' && traceData?.decision_tree && (
          <ToTExplorer 
            treeData={traceData.decision_tree}
            onPathSelect={(path) => console.log('Path selected:', path)}
          />
        )}
        {viewMode === 'logs' && (
          <div className="logs-view">
            {traceData?.events?.map((event: TraceEvent) => (
              <div key={event.event_id} className="log-entry">
                <span className="log-time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                <span className="log-type">{event.event_type}</span>
                <span className="log-message">{event.node.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TraceViewer;
