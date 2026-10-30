import React, { useCallback, useEffect, useRef, useState } from 'react';
import Graph3D from './Graph3D';

const GraphView: React.FC = () => {
  const [showAll, setShowAll] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadGraph = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = '';
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph, showAll]);

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div className="memora-eyebrow">MEMORY GRAPH</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Memory Graph</h2>
        </div>
        <label style={{
          display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
          fontSize: 12, color: '#8794a8',
        }}>
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => setShowAll(e.target.checked)}
            style={{ width: 14, height: 14, accentColor: '#87e0c0' }}
          />
          Show all nodes (including AAC and pending)
        </label>
      </div>

      <div style={{
        background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 15, height: 500, minHeight: 500,
        position: 'relative', overflow: 'hidden',
      }}>
        <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
          <Graph3D showAll={showAll} />
        </div>
        <div style={{
          position: 'absolute', bottom: 12, left: 12, zIndex: 10,
          fontSize: 11, color: '#8794a8',
          background: 'rgba(17, 23, 34, 0.8)', padding: '6px 10px', borderRadius: 6,
          border: '1px solid rgba(167,185,213,0.13)',
        }}>
          Interactive 3D view — click nodes for details
        </div>
      </div>
    </div>
  );
};

export default GraphView;
