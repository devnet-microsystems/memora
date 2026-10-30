import React, { useState } from 'react';

const SettingsView: React.FC = () => {
  const [medName, setMedName] = useState('');
  const [medTime, setMedTime] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactRelation, setContactRelation] = useState('');
  const [caaText, setCaaText] = useState('');
  const [caaIcon, setCaaIcon] = useState('');
  const [eventDesc, setEventDesc] = useState('');
  const [eventSchedule, setEventSchedule] = useState('');
  const [feedback, setFeedback] = useState<string>('');
  const [feedbackType, setFeedbackType] = useState<'success' | 'error' | null>(null);

  const showFeedback = (msg: string, type: 'success' | 'error') => {
    setFeedback(msg);
    setFeedbackType(type);
    setTimeout(() => { setFeedback(''); setFeedbackType(null); }, 5000);
  };

  const addMed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!medName || !medTime) return;
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: `med_${Date.now()}`, type: 'med', content: medName, schedule: medTime }),
      });
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();
      if (data.status === 'pending_approval') {
        showFeedback('Medication submitted for caregiver approval.', 'success');
      } else {
        showFeedback('Medication added.', 'success');
      }
      setMedName('');
      setMedTime('');
    } catch (err) {
      showFeedback(`Error adding medication: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  const addContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactName || !contactPhone || !contactRelation) return;
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: `person_${Date.now()}`, type: 'person', content: `${contactName} (${contactRelation}) - Tel: ${contactPhone}` }),
      });
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();
      if (data.status === 'pending_approval') {
        showFeedback('Contact submitted for caregiver approval.', 'success');
      } else {
        showFeedback('Contact added.', 'success');
      }
      setContactName('');
      setContactPhone('');
      setContactRelation('');
    } catch (err) {
      showFeedback(`Error adding contact: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  const addCAA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caaText || !caaIcon) return;
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: `caa_${Date.now()}`, type: 'caa_button', content: `${caaIcon} ${caaText}` }),
      });
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();
      if (data.status === 'pending_approval') {
        showFeedback('AAC button submitted for caregiver approval.', 'success');
      } else {
        showFeedback('AAC button added.', 'success');
      }
      setCaaText('');
      setCaaIcon('');
    } catch (err) {
      showFeedback(`Error adding AAC button: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  const addEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventDesc || !eventSchedule) return;
    const reTime = /^(\d{2}):(\d{2})$/;
    const reDays = /^([A-Z,]+)\s+(\d{2}):(\d{2})$/;
    const reDate = /^(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})$/;
    if (!reTime.test(eventSchedule) && !reDays.test(eventSchedule) && !reDate.test(eventSchedule)) {
      showFeedback('Invalid schedule format. Use HH:MM or MON,TUE HH:MM or YYYY-MM-DD HH:MM', 'error');
      return;
    }
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: `event_${Date.now()}`, type: 'event', content: eventDesc, schedule: eventSchedule }),
      });
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const data = await res.json();
      if (data.status === 'pending_approval') {
        showFeedback('Appointment submitted for caregiver approval.', 'success');
      } else {
        showFeedback('Appointment added.', 'success');
      }
      setEventDesc('');
      setEventSchedule('');
    } catch (err) {
      showFeedback(`Error adding event: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  const feedbackColor = feedbackType === 'success' ? '#00ff88' : '#ff4444';

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div className="memora-eyebrow">SETTINGS</div>
      <h2 style={{ margin: '0 0 20px 0', fontSize: 24, fontWeight: 600 }}>Caregiver Settings</h2>
      {feedback && (
        <div style={{
          background: feedbackType === 'error' ? '#2d1a1a' : '#1a2d1a',
          border: `1px solid ${feedbackType === 'error' ? '#ff6b6b' : '#00ff88'}`,
          borderRadius: 8, padding: 12, color: feedbackColor, fontSize: 13,
          marginBottom: 16,
        }}>
          {feedback}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
        <div style={{
          background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 15, padding: 20,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#edf2fa', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
            Add Medication
          </div>
          <form onSubmit={addMed} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Name and Dosage</label>
              <input
                type="text" placeholder="e.g. Lisinopril 10 mg"
                value={medName} onChange={(e) => setMedName(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Time</label>
              <input
                type="time" value={medTime} onChange={(e) => setMedTime(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <button type="submit" style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>Add Medication</button>
          </form>
        </div>

        <div style={{
          background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 15, padding: 20,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#edf2fa', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
            Add Contact
          </div>
          <form onSubmit={addContact} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Name</label>
              <input
                type="text" placeholder="e.g. Sarah Morgan"
                value={contactName} onChange={(e) => setContactName(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Phone</label>
              <input
                type="text" placeholder="e.g. +1 503-555-0100"
                value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Relationship</label>
              <input
                type="text" placeholder="e.g. Daughter"
                value={contactRelation} onChange={(e) => setContactRelation(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <button type="submit" style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>Add Contact</button>
          </form>
        </div>

        <div style={{
          background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 15, padding: 20,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#edf2fa', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
            Add AAC Button
          </div>
          <form onSubmit={addCAA} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Action Text</label>
              <input
                type="text" placeholder="e.g. I am cold"
                value={caaText} onChange={(e) => setCaaText(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Icon (Emoji)</label>
              <input
                type="text" placeholder="e.g. 🥶"
                value={caaIcon} onChange={(e) => setCaaIcon(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <button type="submit" style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>Add AAC Button</button>
          </form>
        </div>

        <div style={{
          background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 15, padding: 20,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#edf2fa', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
            Add Appointment (Event)
          </div>
          <form onSubmit={addEvent} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Description</label>
              <input
                type="text" placeholder="e.g. Cardiology follow-up"
                value={eventDesc} onChange={(e) => setEventDesc(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, color: '#8794a8', marginBottom: 4, fontWeight: 600 }}>Schedule</label>
              <input
                type="text" placeholder="e.g. 15:30 or MON,WED 09:00 or 2026-10-05 14:00"
                value={eventSchedule} onChange={(e) => setEventSchedule(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14', color: '#edf2fa', fontSize: 13 }}
              />
            </div>
            <button type="submit" style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', fontWeight: 700, cursor: 'pointer', fontSize: 13,
            }}>Add Appointment</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;
