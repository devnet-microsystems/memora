import React, { useCallback, useState } from 'react';

interface OnboardingResponse {
  status: string;
  extracted: Array<{
    type: string;
    label: string;
    description: string;
    when?: string;
  }>;
}

const OnboardingView: React.FC = () => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string>('');
  const [feedbackType, setFeedbackType] = useState<'success' | 'error' | null>(null);
  const [voiceUnsupported, setVoiceUnsupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const recognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  const runOnboarding = useCallback(async () => {
    const t = text.trim();
    if (!t) return;
    setLoading(true);
    setFeedback('');
    setFeedbackType(null);
    try {
      const res = await fetch('/api/onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interview_text: t }),
      });
      const data: OnboardingResponse = await res.json();
      if (res.ok && data.status === 'success') {
        setFeedback(`Extracted ${data.extracted.length} facts!`);
        setFeedbackType('success');
        setText('');
      } else {
        throw new Error('Extraction failed');
      }
    } catch (err) {
      setFeedback(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setFeedbackType('error');
    } finally {
      setLoading(false);
      setTimeout(() => { setFeedback(''); setFeedbackType(null); }, 5000);
    }
  }, [text]);

  const startRecording = useCallback(() => {
    if (!recognitionCtor) {
      setVoiceUnsupported(true);
      return;
    }
    try {
      const recognition = new recognitionCtor();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.onresult = (event: any) => {
        const result = event.results[event.results.length - 1];
        if (result.isFinal) {
          setText((prev) => (prev ? prev + ' ' : '') + result[0].transcript);
        }
      };
      recognition.onerror = () => {
        setIsRecording(false);
        setVoiceUnsupported(true);
      };
      recognition.onend = () => setIsRecording(false);
      recognition.start();
      setIsRecording(true);
    } catch {
      setVoiceUnsupported(true);
    }
  }, []);

  const stopRecording = useCallback(() => {
    setIsRecording(false);
  }, []);

  return (
    <div className="memora-section" style={{ minHeight: 440 }}>
      <div style={{ marginBottom: 20 }}>
        <div className="memora-eyebrow">AI ONBOARDING</div>
        <h2 style={{ margin: '0 0 8px 0', fontSize: 24, fontWeight: 600 }}>Auto-Extract Facts</h2>
        <p style={{ color: '#8794a8', marginBottom: 16 }}>
          Describe the patient's condition, routines, and family in plain text.
          Nemotron-3-Ultra will automatically extract and link all relevant information.
        </p>
      </div>

      <div style={{
        background: '#111722', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 15, padding: 20,
      }}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="e.g. My father Alex is 72 years old. He lives in Portland, Oregon and takes Lisinopril every morning at 8:00 AM."
          style={{
            width: '100%', minHeight: 100, padding: 12, borderRadius: 8,
            border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
            color: '#edf2fa', fontSize: 13, fontFamily: 'inherit', resize: 'vertical',
          }}
        />
        <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading || voiceUnsupported}
            style={{
              padding: '10px 16px', borderRadius: 8, border: 'none',
              background: isRecording ? '#ef4444' : 'transparent',
              color: isRecording ? '#fff' : '#87e0c0',
              fontWeight: 700, cursor: loading || voiceUnsupported ? 'not-allowed' : 'pointer',
              fontSize: 13,
            }}
          >
            {isRecording ? '🛑 Stop Recording' : '🎙️ Record Voice'}
          </button>
          <button
            onClick={runOnboarding}
            disabled={loading || !text.trim()}
            className="btn btn-primary"
            style={{
              padding: '10px 20px', fontSize: 13, fontWeight: 700,
              borderRadius: 8, border: 'none',
              background: '#87e0c0', color: '#0b0e14', cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Processing…' : 'Extract & Populate Graph'}
          </button>
          {feedback && (
            <span style={{
              fontSize: 12, fontWeight: 600, marginLeft: 8,
              color: feedbackType === 'success' ? '#00ff88' : '#ff4444',
            }}>{feedback}</span>
          )}
          {voiceUnsupported && (
            <span style={{ fontSize: 11, color: '#8794a8', marginLeft: 8 }}>
              Voice not supported in this browser
            </span>
          )}
        </div>
        <div style={{ fontSize: 11, color: '#8794a8', marginTop: 8 }}>
          Dictation uses your browser's speech service; audio may be processed by the browser vendor.
        </div>
      </div>
    </div>
  );
};

export default OnboardingView;
