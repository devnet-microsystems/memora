import React, { useCallback, useEffect, useRef, useState } from 'react';

interface Med {
  id: string;
  content: string;
  time: string;
  status: string;
  schedule?: string;
  last_confirmation?: number;
  med_state?: string;
}

interface MedStatusResponse {
  meds: Array<{
    id: string;
    content: string;
    schedule: string;
    med_state: string;
    last_confirmation?: number;
  }>;
}

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  confirmed: { label: '✅ Confirmed', color: '#00ff88', bg: '#003300' },
  due: { label: '⏳ Due', color: '#f59e0b', bg: '#1a1100' },
  snoozed: { label: '💤 Snoozed', color: '#f59e0b', bg: '#1a1100' },
  missed: { label: '❌ Missed', color: '#ff4444', bg: '#330000' },
  upcoming: { label: '🕒 Upcoming', color: '#0369a1', bg: '#001a33' },
  denied: { label: '❌ Denied', color: '#ff4444', bg: '#330000' },
  unsure: { label: '❓ Unsure', color: '#f59e0b', bg: '#1a1100' },
};

const MedicationsView: React.FC = () => {
  const [meds, setMeds] = useState<Med[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newTime, setNewTime] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMeds = useCallback(async () => {
    try {
      const res = await fetch('/api/med/status');
      if (!res.ok) throw new Error('Failed to load medications');
      const data: MedStatusResponse = await res.json();
      setMeds(
        data.meds.map((m) => ({
          id: m.id,
          content: m.content || m.id,
          time: m.schedule || 'N/A',
          status: m.med_state || 'unknown',
          schedule: m.schedule,
          last_confirmation: m.last_confirmation,
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading medications');
    } finally {
      setLoading(false);
    }
  }, []);

  const confirmMed = useCallback(async (id: string) => {
    try {
      const res = await fetch('/api/med/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ med_id: id, status: 'confirmed' }),
      });
      if (!res.ok) throw new Error('Confirm failed');
      fetchMeds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not confirm medication');
    }
  }, [fetchMeds]);

  const addMed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newTime) return;
    setError(null);
    const id = `med_${Date.now()}`;
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, type: 'med', content: newName, schedule: newTime }),
      });
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();
      if (data.status === 'pending_approval') {
        setError('Medication submitted for caregiver approval.');
      }
      setNewName('');
      setNewTime('');
      fetchMeds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error adding medication');
    }
  };

  const statusMeta = (status: string) => STATUS_LABELS[status] || { label: status, color: '#8794a8', bg: '#0e121a' };

  useEffect(() => {
    fetchMeds();
    intervalRef.current = setInterval(fetchMeds, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchMeds]);

  if (loading) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center' }}>
        <div className="memora-placeholder-icon" aria-hidden="true">✚</div>
        <div className="memora-eyebrow">MEDICATIONS</div>
        <h2>Medications</h2>
        <p style={{ color: '#aab5c6' }}>Loading medications…</p>
      </div>
    );
  }

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20,
        gap: 12, flexWrap: 'wrap',
      }}>
        <div>
          <div className="memora-eyebrow">MEDICATIONS</div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Today's Medicines</h2>
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
        borderRadius: 15, padding: 20,
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: 'left', color: '#8794a8', fontSize: 11, letterSpacing: 1.2 }}>
              <th style={{ padding: '10px 0', fontWeight: 600 }}>Medication</th>
              <th style={{ padding: '10px 0', fontWeight: 600 }}>Time</th>
              <th style={{ padding: '10px 0', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '10px 0', fontWeight: 600 }}>Last confirmation</th>
              <th style={{ padding: '10px 0', fontWeight: 600 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {meds.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: 20, color: '#8794a8', textAlign: 'center' }}>
                  No medications configured.
                </td>
              </tr>
            ) : (
              meds.map((m) => {
                const meta = statusMeta(m.status);
                const lastConf = m.last_confirmation
                  ? new Date(m.last_confirmation * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : 'Never';
                return (
                  <tr key={m.id} style={{ borderBottom: '1px solid rgba(167,185,213,0.13)', color: '#edf2fa' }}>
                    <td style={{ padding: '12px 0', fontWeight: 500 }}>{m.content}</td>
                    <td style={{ padding: '12px 0' }}>{m.time}</td>
                    <td style={{ padding: '12px 0' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 20,
                        fontSize: 11, fontWeight: 600, color: meta.color,
                        background: meta.bg,
                      }}>{meta.label}</span>
                    </td>
                    <td style={{ padding: '12px 0', color: '#8794a8' }}>{lastConf}</td>
                    <td style={{ padding: '12px 0' }}>
                      <button
                        onClick={() => confirmMed(m.id)}
                        disabled={m.status === 'confirmed'}
                        style={{
                          padding: '6px 12px', fontSize: 12, borderRadius: 6,
                          border: '1px solid var(--line)', background: 'transparent',
                          color: m.status === 'confirmed' ? '#8794a8' : '#87e0c0',
                          cursor: m.status === 'confirmed' ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {m.status === 'confirmed' ? 'Confirmed' : 'Confirm'}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 20, background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)', borderRadius: 15, padding: 20 }}>
        <div className="memora-eyebrow">ADD MEDICATION</div>
        <h3 style={{ margin: '0 0 12px 0', fontSize: 16, fontWeight: 600, color: '#edf2fa' }}>Register new medication</h3>
        <form onSubmit={addMed} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Name and dosage (e.g. Lisinopril 10 mg)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
            style={{
              flex: 1, minWidth: 200, padding: '10px 12px', borderRadius: 8,
              border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
              color: '#edf2fa', fontSize: 13,
            }}
          />
          <input
            type="time"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
            required
            style={{
              minWidth: 140, padding: '10px 12px', borderRadius: 8,
              border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
              color: '#edf2fa', fontSize: 13,
            }}
          />
          <button
            type="submit"
            style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', fontWeight: 700,
              cursor: 'pointer', fontSize: 13,
            }}
          >
            Add
          </button>
        </form>
      </div>
    </div>
  );
};

export default MedicationsView;
