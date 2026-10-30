import React, { useCallback, useEffect, useState } from 'react';

interface HealthResponse {
  status: string;
  encrypted: boolean;
}

interface StatsTotals {
  interactions: number;
  repeats: number;
  confusion: number;
  sos: number;
  meds_confirmed: number;
  meds_missed: number;
  meds_unsure: number;
  diary_turns: number;
}

interface StatsResponse {
  days: number;
  simulated: boolean;
  metrics_per_day: Record<string, StatsTotals>;
  totals: StatsTotals;
  prev_totals: StatsTotals;
}

const METRIC_LABELS: Record<string, { label: string; color: string }> = {
  interactions: { label: 'Interactions', color: '#87e0c0' },
  meds_confirmed: { label: 'Meds confirmed', color: '#00ff88' },
  diary_turns: { label: 'Diary turn', color: '#0088ff' },
  sos: { label: 'SOS', color: '#ff4444' },
  confusion: { label: 'Confusion', color: '#ffaa00' },
  meds_missed: { label: 'Meds missed', color: '#ff4444' },
  meds_unsure: { label: 'Meds unsure', color: '#ffaa00' },
  repeats: { label: 'Repeats', color: '#888888' },
};

const Overview: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, statsRes] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/stats?days=7'),
      ]);

      if (!healthRes.ok) {
        throw new Error(`Health check failed: HTTP ${healthRes.status}`);
      }
      setHealth(await healthRes.json());

      if (!statsRes.ok) {
        throw new Error(`Stats failed: HTTP ${statsRes.status}`);
      }
      setStats(await statsRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading data');
      setHealth(null);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const systemStatus = health?.status ?? '–';
  const isHealthy = health?.status === 'ok';
  const totals = stats?.totals ?? {
    interactions: 0, repeats: 0, confusion: 0, sos: 0,
    meds_confirmed: 0, meds_missed: 0, meds_unsure: 0, diary_turns: 0,
  };
  const prevTotals = stats?.prev_totals ?? {
    interactions: 0, repeats: 0, confusion: 0, sos: 0,
    meds_confirmed: 0, meds_missed: 0, meds_unsure: 0, diary_turns: 0,
  };
  const simulated = stats?.simulated ?? false;

  const deltaPct = (current: number, previous: number) => {
    if (previous === 0) return current > 0 ? 100 : 0;
    return Math.round(((current - previous) / previous) * 100);
  };

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">◫</div>
              <div className="memora-eyebrow">MEMORA WORKSPACE</div>
        <h2>Overview</h2>
        <p style={{ color: '#aab5c6' }}>Loading summary data…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">◫</div>
              <div className="memora-eyebrow">MEMORA WORKSPACE</div>
        <h2>Overview</h2>
        <p style={{ color: '#ff9999' }}>{error}</p>
      </div>
    );
  }

  const daysWithData = Object.keys(stats?.metrics_per_day ?? {}).length;

  return (
    <div className="memora-overview" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, minHeight: 440 }}>
      {/* Status card */}
      <div style={{
        gridColumn: '1 / -1',
        background: '#111722',
        border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 15,
        padding: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
      }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: isHealthy ? '#87e0c0' : '#ffaa00',
        }} />
        <div>
          <div style={{ fontSize: 10, letterSpacing: 1.6, textTransform: 'uppercase', color: '#8794a8', fontWeight: 700 }}>Stato sistema</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#edf2fa', textTransform: 'capitalize' }}>{systemStatus}</div>
          {simulated && (
            <div style={{ fontSize: 11, marginTop: 4, color: '#ffaa00' }}>Demo data active</div>
          )}
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#8794a8' }}>
          {daysWithData} giorni con dati
        </div>
      </div>

      {/* Metric cards */}
      {Object.entries(totals).map(([key, value]) => {
        const meta = METRIC_LABELS[key];
        const prev = prevTotals[key as keyof StatsTotals] ?? 0;
        const delta = deltaPct(value, prev);
        return (
          <div key={key} style={{
            background: '#111722',
            border: '1px solid rgba(167, 185, 213, 0.13)',
            borderRadius: 15,
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ fontSize: 10, letterSpacing: 1.6, textTransform: 'uppercase', color: '#8794a8', fontWeight: 700 }}>{meta.label}</div>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: meta.color,
              }} />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#edf2fa' }}>{value}</div>
            <div style={{
              fontSize: 11,
              color: delta >= 0 ? '#00ff88' : '#ff4444',
              fontWeight: 600,
            }}>
              {delta >= 0 ? '+' : ''}{delta}% vs settimana precedente
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Overview;
