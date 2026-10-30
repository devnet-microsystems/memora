import React, { useCallback, useState } from 'react';

interface StatTotals {
  interactions: number;
  sos: number;
  meds_confirmed: number;
  repeats: number;
}

interface StatsResponse {
  totals: StatTotals;
  metrics_per_day: Record<string, any>;
  simulated: boolean;
}

interface ReportResponse {
  report: string;
  stats: StatsResponse;
}

const ReportView: React.FC = () => {
  const [report, setReport] = useState<string>('');
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/report', { method: 'POST' });
      if (!res.ok) throw new Error('Report generation failed');
      const data: ReportResponse = await res.json();
      setReport(data.report);
      setStats(data.stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error generating report');
    } finally {
      setLoading(false);
    }
  }, []);

  const simulated = stats?.simulated ?? false;
  const totals = stats?.totals ?? { interactions: 0, sos: 0, meds_confirmed: 0, repeats: 0 };

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">▥</div>
        <div className="memora-eyebrow">WEEKLY REPORT</div>
        <h2>Weekly Report</h2>
        <p style={{ color: '#aab5c6' }}>Generating report…</p>
      </div>
    );
  }

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div className="memora-eyebrow">WEEKLY REPORT</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>AI Weekly Report</h2>
        </div>
        {simulated && (
          <span style={{
            fontSize: 11, fontWeight: 700, color: '#f59e0b',
            background: '#1a1100', padding: '2px 8px', borderRadius: 20,
            border: '1px solid rgba(245,158,11,0.3)',
          }}>Simulated demo data</span>
        )}
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
        display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap',
      }}>
        {[
          { label: 'Interactions', value: totals.interactions, color: '#87e0c0' },
          { label: 'SOS Calls', value: totals.sos, color: '#ff4444' },
          { label: 'Meds Confirmed', value: totals.meds_confirmed, color: '#00ff88' },
          { label: 'Repeats', value: totals.repeats, color: '#f59e0b' },
        ].map((m) => (
          <div key={m.label} style={{
            background: '#111722', border: '1px solid rgba(167,185,213,0.13)',
            borderRadius: 12, padding: 16, minWidth: 140,
          }}>
            <div style={{ fontSize: 10, letterSpacing: 1.4, textTransform: 'uppercase', color: '#8794a8', fontWeight: 700, marginBottom: 6 }}>
              {m.label}
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div style={{
        background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 15, padding: 0,
      }}>
        <div style={{ padding: 20, borderBottom: '1px solid rgba(167,185,213,0.13)' }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            <button
              onClick={generateReport}
              disabled={loading}
              className="btn btn-primary"
              style={{
                padding: '10px 20px', fontSize: 13, fontWeight: 600,
                borderRadius: 8, border: 'none',
                background: '#87e0c0', color: '#0b0e14', cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Generating…' : '✨ Generate AI Report'}
            </button>
            <button
              onClick={() => window.print()}
              style={{
                padding: '10px 20px', fontSize: 13, fontWeight: 600,
                borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)',
                background: 'transparent', color: '#8794a8', cursor: 'pointer',
              }}
            >
              🖨️ Download PDF
            </button>
          </div>
        </div>

        <div style={{ padding: 20 }}>
          {report ? (
            <div style={{
              whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.7, color: '#edf2fa',
              background: '#0b0e14', padding: 20, borderRadius: 8,
              border: '1px solid rgba(167,185,213,0.13)',
            }}>{report}</div>
          ) : (
            <div style={{ padding: 40, color: '#8794a8', textAlign: 'center' }}>
              Click "Generate AI Report" to render the report here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportView;
