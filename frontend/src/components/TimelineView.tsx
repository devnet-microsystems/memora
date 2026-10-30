import React, { useCallback, useEffect, useRef, useState } from 'react';

interface TimelineItem {
  event_date: string;
  content: string;
}

const TimelineView: React.FC = () => {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTimeline = useCallback(async () => {
    try {
      const res = await fetch('/api/timeline');
      if (!res.ok) throw new Error('Failed to load timeline');
      const data: TimelineItem[] = await res.json();
      setTimeline(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading timeline');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTimeline();
    intervalRef.current = setInterval(fetchTimeline, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchTimeline]);

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">⌁</div>
        <div className="memora-eyebrow">PEOPLE & ROUTINE</div>
        <h2>Timeline</h2>
        <p style={{ color: '#aab5c6' }}>Loading timeline…</p>
      </div>
    );
  }

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div className="memora-eyebrow">PEOPLE & ROUTINE</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Timeline</h2>
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
        {timeline.length === 0 ? (
          <div style={{ padding: 40, color: '#8794a8', textAlign: 'center' }}>
            No timeline events yet.
          </div>
        ) : (
          <div style={{ padding: 0 }}>
            {timeline.map((t, i) => (
              <div key={i} style={{
                padding: 16, borderBottom: '1px solid rgba(167,185,213,0.13)',
                display: 'flex', gap: 15, alignItems: 'flex-start',
              }}>
                <div style={{
                  fontWeight: 600, width: 110, color: '#87e0c0', flexShrink: 0,
                  fontSize: 13, lineHeight: 1.4,
                }}>{t.event_date || 'Past'}</div>
                <div style={{ color: '#edf2fa', lineHeight: 1.5, fontSize: 14 }}>
                  {t.content}
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
        Auto-refresh every 30 seconds
      </div>
    </div>
  );
};

export default TimelineView;
