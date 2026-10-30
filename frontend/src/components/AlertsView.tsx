import React, { useCallback, useEffect, useRef, useState } from 'react';

interface AlertNode {
  id: string;
  label: string;
  group: string;
  timestamp?: number;
  status?: string;
}

interface MemoryResponse {
  nodes: AlertNode[];
  edges: Array<{ from: string; to: string; label?: string }>;
}

const AlertsView: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/memory');
      if (!res.ok) throw new Error('Failed to load alerts');
      const data: MemoryResponse = await res.json();
      const openAlerts = (data.nodes || [])
        .filter((n) => n.group === 'alert' && n.status !== 'acknowledged')
        .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
        .slice(0, 10);
      setAlerts(openAlerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  const acknowledgeAlert = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/alerts/${encodeURIComponent(id)}/ack`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!res.ok) throw new Error('Acknowledge failed');
      fetchAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not acknowledge alert');
    }
  }, [fetchAlerts]);

  useEffect(() => {
    fetchAlerts();
    intervalRef.current = setInterval(fetchAlerts, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAlerts]);

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">◉</div>
        <div className="memora-eyebrow">ALERTS</div>
        <h2>Alerts</h2>
        <p style={{ color: '#aab5c6' }}>Loading alerts…</p>
      </div>
    );
  }

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div className="memora-eyebrow">ALERTS</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Needs your attention</h2>
        </div>
        {error && (
          <div style={{
            background: '#2d1a1a', border: '1px solid #ff6b6b', borderRadius: 8,
            padding: 12, color: '#ff9999', fontSize: 13,
          }}>
            {error}
          </div>
        )}
      </div>

      <div style={{
        background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 15, padding: 0,
      }}>
        {alerts.length === 0 ? (
          <div style={{ padding: 40, color: '#8794a8', textAlign: 'center' }}>
            No alerts.
          </div>
        ) : (
          <div style={{ padding: 0 }}>
            {alerts.map((a) => (
              <div key={a.id} style={{
                padding: 14, borderBottom: '1px solid rgba(167,185,213,0.13)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12,
              }}>
                <div style={{ flex: 1, minWidth: 0, overflowWrap: 'break-word', wordBreak: 'break-word' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <strong style={{ color: '#87e0c0', textTransform: 'uppercase', fontSize: 11, letterSpacing: 1 }}>
                      [{a.group.toUpperCase()}]
                    </strong>
                    <span style={{ color: '#8794a8', fontSize: 11 }}>
                      {a.timestamp ? new Date(a.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                  <div style={{ fontSize: 15, color: '#edf2fa', fontWeight: 500, overflowWrap: 'break-word', wordBreak: 'break-word' }}>{a.label}</div>
                </div>
                <button
                  onClick={() => acknowledgeAlert(a.id)}
                  style={{
                    padding: '8px 14px', fontSize: 12, borderRadius: 6,
                    border: '1px solid #87e0c0', background: 'transparent',
                    color: '#87e0c0', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  Acknowledge
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        marginTop: 16, fontSize: 11, color: '#8794a8',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />
        Auto-refresh every 10 seconds
      </div>
    </div>
  );
};

export default AlertsView;
