import React, { useCallback, useEffect, useRef, useState } from 'react';
import ForceGraph3D from '3d-force-graph';

interface GraphNode {
  id: string;
  label?: string;
  name?: string;
  group?: string;
  content?: string;
  timestamp?: number;
  x?: number;
  y?: number;
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}

interface GraphLink {
  from?: string;
  source?: string | { id?: string };
  target?: string | { id?: string };
  to?: string;
  label?: string;
  [key: string]: unknown;
}

interface GraphPayload {
  nodes?: GraphNode[];
  links?: GraphLink[];
  edges?: GraphLink[];
}

interface Graph3DProps {
  refreshMs?: number;
  apiEndpoint?: string;
  showAll?: boolean;
}

const GROUP_COLORS: Record<string, string> = {
  person: '#00ff88',
  place: '#0088ff',
  med: '#ff00ff',
  habit: '#ffaa00',
  condition: '#ff4444',
  preference: '#00ffff',
  flag: '#ffff00',
  alert: '#ff0088',
  pending: '#888888',
  caa_button: '#4488ff',
  unknown: '#cccccc',
};

const GROUP_SIZE: Record<string, number> = {
  alert: 13,
  condition: 12,
  med: 11,
  person: 11,
  place: 10,
  habit: 10,
  preference: 9,
  caa_button: 9,
  pending: 8,
  flag: 7,
  unknown: 7,
};

const colorFor = (group?: string) => GROUP_COLORS[group ?? 'unknown'] ?? GROUP_COLORS.unknown;
const sizeFor = (group?: string) => GROUP_SIZE[group ?? 'unknown'] ?? GROUP_SIZE.unknown;

const Graph3D: React.FC<Graph3DProps> = ({
  refreshMs = 10000,
  apiEndpoint = '/api/memory',
  showAll = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphContainerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [graphEmpty, setGraphEmpty] = useState(false);

  const loadGraph = useCallback(async () => {
    const response = await fetch(apiEndpoint);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} during graph loading`);
    }

    const payload = (await response.json()) as GraphPayload;
    if (!Array.isArray(payload.nodes)) {
      throw new Error('Invalid API response: nodes must be an array');
    }
    const rawLinks = Array.isArray(payload.links) ? payload.links : payload.edges;
    if (!Array.isArray(rawLinks)) {
      throw new Error('Invalid API response: links or edges must be an array');
    }

    const nodes = payload.nodes
      .filter(
        (node) =>
          !(node.group === 'pending' && node.label === 'Test - desc') &&
          (showAll || !(node.group === 'caa_button' || node.group === 'pending'))
      )
      .map((node) => ({
        ...node,
        name: node.label || node.name || node.id,
        color: colorFor(node.group),
        val: sizeFor(node.group),
      }));

    const links = rawLinks
      .map((link) => {
        const source =
          typeof link.source === 'string'
            ? link.source
            : link.source?.id ?? link.from;
        const target =
          typeof link.target === 'string'
            ? link.target
            : link.target?.id ?? link.to;

        if (!source || !target) return null;
        return {
          ...link,
          source,
          target,
          label: link.label || 'related_to',
          color: '#6a7a8a',
          width: 2.5,
        };
      })
      .filter((link): link is NonNullable<typeof link> => link !== null);

    graphRef.current?.graphData({ nodes, links });
    setError(null);
    setLoading(false);
    setGraphEmpty(nodes.length === 0 && links.length === 0);
  }, [apiEndpoint]);

  useEffect(() => {
    const graphContainer = graphContainerRef.current;
    if (!graphContainer) return;

    // Create the 3D graph only after the DOM container exists.
    const graph: any = (ForceGraph3D as any)()(graphContainer);
    graphRef.current = graph;

    graph
      .backgroundColor('#0a0a0c')
      .nodeLabel((node: GraphNode) => {
        const title = node.label || node.name || node.id;
        return node.group ? `${title} · ${node.group}` : title;
      })
      .nodeColor((node: { color?: string }) => node.color || GROUP_COLORS.unknown)
      .nodeVal((node: { val?: number }) => node.val || 7)
      .linkColor((link: { color?: string }) => link.color || '#6a7a8a')
      .linkWidth((link: { width?: number }) => link.width || 2.5)
      .linkOpacity(0.75)
      .onNodeClick((node: GraphNode) => {
        setSelectedNode(node);
        if (graphRef.current) {
          graphRef.current.centerAt(node.x ?? 0, node.y ?? 0, 700);
          graphRef.current.zoom(2, 700);
        }
      });

    const handleResize = () => {
      if (graphContainerRef.current && graphRef.current) {
        graphRef.current.width(graphContainerRef.current.clientWidth);
        graphRef.current.height(graphContainerRef.current.clientHeight);
        graphRef.current.refresh();
      }
    };

    window.addEventListener('resize', handleResize);
    void loadGraph().catch((err: unknown) => {
      console.error('Memora graph: initial load failed', err);
        setError(err instanceof Error ? err.message : 'Unable to load graph');
      setLoading(false);
    });

    const interval =
      refreshMs > 0
        ? window.setInterval(() => {
            void loadGraph().catch((err: unknown) => {
              console.error('Memora graph: update failed', err);
              setError(err instanceof Error ? err.message : 'Graph update failed');
            });
          }, refreshMs)
        : null;

    return () => {
      window.removeEventListener('resize', handleResize);
      if (interval !== null) window.clearInterval(interval);
      graphRef.current = null;
      if (typeof graph._destructor === 'function') graph._destructor();
      else if (typeof graph.pauseAnimation === 'function') graph.pauseAnimation();
    };
  }, [loadGraph, refreshMs]);

  const recenter = () => {
    graphRef.current?.zoomToFit(500, 40);
  };

  return (
    <div
      ref={containerRef}
      id="graph-container"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '320px',
        overflow: 'hidden',
        background: '#0a0a0c',
        color: '#fff',
      }}
    >
      <div
        ref={graphContainerRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
        }}
      />
      <button
        type="button"
        onClick={recenter}
        aria-label="Center graph"
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          zIndex: 10,
          padding: '8px 12px',
          background: '#1f5fbf',
          color: '#fff',
          border: 0,
          borderRadius: 6,
          cursor: 'pointer',
          fontFamily: 'Atkinson Hyperlegible, sans-serif',
          fontSize: 13,
        }}
      >
        ↗ Center graph
      </button>

      {loading && !error && (
        <div style={{ position: 'absolute', left: 12, bottom: 12, zIndex: 10 }}>
          Loading graph…
        </div>
      )}

      {!loading && !error && graphEmpty && (
        <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 20, textAlign: 'center', color: '#8794a8' }}>
          <div style={{ fontSize: 14, marginBottom: 6 }}>No memory nodes yet.</div>
          <div style={{ fontSize: 12, color: '#5a6a7a' }}>Interact with Memora to start building the memory graph.</div>
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 20,
            width: 'min(400px, calc(100% - 32px))',
            boxSizing: 'border-box',
            padding: 16,
            color: '#ff9999',
            background: '#1a0a0a',
            border: '1px solid #ff6666',
            borderRadius: 8,
            textAlign: 'center',
          }}
        >
          {error}
        </div>
      )}

      {selectedNode && (
        <div
          style={{
            position: 'absolute',
            left: 10,
            bottom: 10,
            zIndex: 10,
            maxWidth: 320,
            padding: 12,
            color: '#fff',
            background: 'rgba(18, 18, 28, 0.94)',
            border: `1px solid ${colorFor(selectedNode.group)}`,
            borderRadius: 8,
          }}
        >
          <button
            type="button"
            onClick={() => setSelectedNode(null)}
            aria-label="Close node details"
            style={{
              float: 'right',
              marginLeft: 12,
              color: '#fff',
              background: 'transparent',
              border: 0,
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
          <strong>{selectedNode.label || selectedNode.name || selectedNode.id}</strong>
          {selectedNode.group && (
            <div style={{ marginTop: 4, color: colorFor(selectedNode.group) }}>
              {selectedNode.group}
            </div>
          )}
          {selectedNode.content && (
            <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{selectedNode.content}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default Graph3D;
