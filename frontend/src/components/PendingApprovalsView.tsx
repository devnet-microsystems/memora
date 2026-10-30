import React, { useCallback, useEffect, useRef, useState } from 'react';

interface PendingItem {
  id: string;
  content: string;
  proposed_type: string;
  event_date?: string;
  meta?: Record<string, any>;
}

const PendingApprovalsView: React.FC = () => {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPending = useCallback(async () => {
    try {
      const res = await fetch('/api/pending');
      if (!res.ok) throw new Error('Failed to load pending items');
      const data: PendingItem[] = await res.json();
      setItems(data);
      setEdits(Object.fromEntries(data.map((p) => [p.id, p.content])));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading pending items');
    } finally {
      setLoading(false);
    }
  }, []);

  const approvePending = useCallback(async (id: string) => {
    const content = edits[id];
    if (content === undefined) return;
    try {
      const res = await fetch(`/api/pending/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error('Approve failed');
      fetchPending();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not approve item');
    }
  }, [edits, fetchPending]);

  const discardPending = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/memory/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Discard failed');
      fetchPending();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not discard item');
    }
  }, [fetchPending]);

  useEffect(() => {
    fetchPending();
    intervalRef.current = setInterval(fetchPending, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchPending]);

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">▤</div>
        <div className="memora-eyebrow">PENDING APPROVALS</div>
        <h2>Stories to review</h2>
        <p style={{ color: '#aab5c6' }}>Loading pending items…</p>
      </div>
    );
  }

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div className="memora-eyebrow">PENDING APPROVALS</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Stories to review</h2>
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
        {items.length === 0 ? (
          <div style={{ padding: 40, color: '#8794a8', textAlign: 'center' }}>
            No stories to review.
          </div>
        ) : (
          <div style={{ padding: 0 }}>
            {items.map((p) => (
              <div key={p.id} style={{
                padding: 16, borderBottom: '1px solid rgba(167,185,213,0.13)',
              }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: '#87e0c0', marginRight: 6,
                    textTransform: 'uppercase', letterSpacing: 1,
                  }}>{p.proposed_type}</span>
                  {p.event_date && (
                    <span style={{ fontSize: 11, color: '#8794a8' }}>{p.event_date}</span>
                  )}
                </div>
                <input
                  type="text"
                  value={edits[p.id] ?? p.content}
                  onChange={(e) => setEdits({ ...edits, [p.id]: e.target.value })}
                  className="form-control"
                  style={{
                    width: '100%', padding: '8px 12px', borderRadius: 6,
                    border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
                    color: '#edf2fa', fontSize: 13, marginBottom: 8,
                  }}
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => approvePending(p.id)}
                    style={{
                      padding: '8px 14px', fontSize: 12, borderRadius: 6,
                      border: 'none', background: '#87e0c0', color: '#0b0e14',
                      fontWeight: 700, cursor: 'pointer',
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => discardPending(p.id)}
                    style={{
                      padding: '8px 14px', fontSize: 12, borderRadius: 6,
                      border: '1px solid rgba(167,185,213,0.13)', background: 'transparent',
                      color: '#ff6b6b', cursor: 'pointer', fontWeight: 600,
                    }}
                  >
                    Discard
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        marginTop: 16, fontSize: 11, color: '#8794a8',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#87e0c0', display: 'inline-block' }} />
        Auto-refresh every 10 seconds
      </div>
    </div>
  );
};

export default PendingApprovalsView;
