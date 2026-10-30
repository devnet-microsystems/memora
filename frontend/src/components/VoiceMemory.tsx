import { useState, useRef, useCallback } from 'react'

interface Fact {
  type: string
  label: string
  description: string
  when: string
}

export default function VoiceMemory({ onSaved }: { onSaved?: (count: number) => void }) {
  const [isListening, setIsListening] = useState(false)
  const [transcriptPreview, setTranscriptPreview] = useState(false)
  const [pendingTranscript, setPendingTranscript] = useState('')
  const [factPreview, setFactPreview] = useState(false)
  const [pendingFacts, setPendingFacts] = useState<Fact[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const speechRecognitionRef = useRef<any>(null)
  const recognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  const startListening = useCallback(() => {
    if (!recognitionCtor || speechRecognitionRef.current || isListening) return

    setError(null)
    const recognition = new recognitionCtor()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.continuous = false

    const finalSegments: string[] = []
    const processedIndices = new Set<number>()

    recognition.onstart = () => {
      if (speechRecognitionRef.current !== recognition) return
      setIsListening(true)
    }

    recognition.onresult = (event: any) => {
      if (speechRecognitionRef.current !== recognition) return
      const start = event.resultIndex ?? 0
      for (let i = start; i < event.results.length; i++) {
        if (processedIndices.has(i)) continue
        const result = event.results[i]
        if (!result.isFinal) continue
        processedIndices.add(i)
        const part = result[0].transcript
        if (!part || part.trim() === '') continue
        finalSegments[i] = part.trim()
      }
    }

    recognition.onend = () => {
      if (speechRecognitionRef.current !== recognition) return
      speechRecognitionRef.current = null
      setIsListening(false)

      const transcriptText = finalSegments.filter(Boolean).join(' ').trim()
      if (!transcriptText) {
        setError("I didn't catch anything. Please try again.")
        return
      }

      setPendingTranscript(transcriptText)
      const textarea = document.getElementById('voice-preview-text') as HTMLTextAreaElement | null
      if (textarea) textarea.value = transcriptText
      setTranscriptPreview(true)
    }

    recognition.onerror = (event: any) => {
      if (speechRecognitionRef.current !== recognition) return
      speechRecognitionRef.current = null
      setIsListening(false)

      if (event.error === 'aborted') return

      let msg = ''
      switch (event.error) {
        case 'not-allowed':
        case 'service-not-allowed':
          msg = 'Microphone access denied. Please check your permissions and try again.'
          break
        case 'audio-capture':
          msg = 'Microphone not available.'
          break
        case 'no-speech':
          msg = 'No speech detected. Please try again.'
          break
        case 'network':
          msg = 'Voice recognition is unavailable due to a network problem.'
          break
        default:
          msg = "Didn't catch that. Please try again."
          break
      }
      setError(msg)
    }

    speechRecognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      speechRecognitionRef.current = null
      setError('Could not start voice recognition. Please try again.')
    }
  }, [isListening])

  const cancelListening = useCallback(() => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.abort()
      speechRecognitionRef.current = null
    }
    setIsListening(false)
    setPendingTranscript('')
    setTranscriptPreview(false)
    setError(null)
  }, [])

  const useTranscript = useCallback(() => {
    const text = pendingTranscript.trim()
    if (!text) return
    setTranscriptPreview(false)
    setLoading(true)
    setError(null)

    fetch('/api/voice/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Extraction failed')
        return res.json()
      })
      .then((data) => {
        const facts: Fact[] = (data.facts || []).map((f: any) => ({
          type: f.type || 'fact',
          label: f.label || '',
          description: f.description || '',
          when: f.when || '',
        }))
        setPendingFacts(facts)
        setFactPreview(facts.length > 0)
        if (facts.length === 0) {
          setError('No facts found in the transcript.')
        }
      })
      .catch(() => {
        setError('Could not extract facts. Please try again.')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [pendingTranscript])

  const cancelTranscript = useCallback(() => {
    setTranscriptPreview(false)
    setPendingTranscript('')
    setError(null)
  }, [])

  const editTranscript = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPendingTranscript(e.target.value)
  }, [])

  const cancelFacts = useCallback(() => {
    setFactPreview(false)
    setPendingFacts([])
    setError(null)
  }, [])

  const confirmFacts = useCallback(async () => {
    if (!pendingFacts || pendingFacts.length === 0) return
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/voice/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts: pendingFacts }),
      })
      if (!res.ok) throw new Error('Save failed')
      const data = await res.json()
      setFactPreview(false)
      setPendingFacts([])
      setLoading(false)
      onSaved?.(data.created || 0)
    } catch {
      setLoading(false)
      setError('Could not save facts. Please try again.')
    }
  }, [pendingFacts, onSaved])

  const editFactLabel = useCallback((idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const next = [...pendingFacts]
    next[idx].label = e.target.value
    setPendingFacts(next)
  }, [pendingFacts])

  const editFactDescription = useCallback((idx: number, e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const next = [...pendingFacts]
    next[idx].description = e.target.value
    setPendingFacts(next)
  }, [pendingFacts])

  const editFactWhen = useCallback((idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const next = [...pendingFacts]
    next[idx].when = e.target.value
    setPendingFacts(next)
  }, [pendingFacts])

  const removeFact = useCallback((idx: number) => {
    const next = [...pendingFacts]
    next.splice(idx, 1)
    setPendingFacts(next)
  }, [pendingFacts])

  if (!recognitionCtor) {
    return (
      <div className="memora-placeholder" style={{ textAlign: 'center', padding: 40 }}>
        <div className="memora-placeholder-icon" aria-hidden="true">🎙️</div>
        <div className="memora-eyebrow">ADD MEMORY BY VOICE</div>
        <h2>Voice not supported</h2>
        <p style={{ color: '#aab5c6' }}>This browser does not support voice recognition.</p>
      </div>
    )
  }

  return (
    <div className="memora-voice-memory" style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <div className="memora-eyebrow">ADD MEMORY BY VOICE</div>
      <h2 style={{ margin: '0 0 16px 0', color: '#edf2fa' }}>Caregiver Voice Input</h2>
      <p style={{ color: '#8794a8', marginBottom: 24 }}>
        Speak to add information to Memora's memory. You will review everything before it is saved.
      </p>

      {error && (
        <div style={{
          background: '#2d1a1a',
          border: '1px solid #ff6b6b',
          borderRadius: 8,
          padding: 12,
          color: '#ff9999',
          fontSize: 13,
          marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      <button
        id="btn-voice-memory"
        className={`btn ${isListening ? 'btn-primary' : 'btn-outline'}`}
        onClick={isListening ? cancelListening : startListening}
        disabled={loading}
        style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          fontSize: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 16,
        }}
        aria-label={isListening ? 'Stop listening' : 'Start listening'}
      >
        {isListening ? '⏹️' : '🎙️'}
      </button>
      <div style={{ fontSize: 12, color: '#8794a8', textAlign: 'center', marginBottom: 24 }}>
        {isListening ? 'Listening…' : 'Tap to speak'}
      </div>

      {transcriptPreview && (
        <div className="preview-overlay" style={{ display: 'block' }}>
          <div className="preview-card">
            <div className="preview-header">
              <span style={{ fontSize: 24 }}>🎙️</span>
              <h3 style={{ margin: 0, color: '#edf2fa', fontSize: 20 }}>Review what you said</h3>
            </div>
            <p className="preview-hint">Review and edit your transcript before extracting facts:</p>
            <textarea
              id="voice-preview-text"
              className="form-control"
              rows={4}
              defaultValue={pendingTranscript}
              onChange={editTranscript}
              style={{
                width: '100%',
                background: '#0b1018',
                color: '#edf2fa',
                border: '1px solid rgba(167,185,213,0.13)',
                borderRadius: 8,
                padding: 12,
                fontFamily: 'inherit',
                fontSize: 14,
                marginBottom: 12,
              }}
            />
            <div className="preview-actions">
              <button className="btn" onClick={cancelTranscript}>Cancel</button>
              <button className="btn btn-primary" onClick={useTranscript} disabled={loading}>
                {loading ? 'Extracting facts…' : 'Extract facts'}
              </button>
            </div>
          </div>
        </div>
      )}

      {factPreview && (
        <div className="preview-overlay" style={{ display: 'block' }}>
          <div className="preview-card">
            <div className="preview-header">
              <span style={{ fontSize: 24 }}>📋</span>
              <h3 style={{ margin: 0, color: '#edf2fa', fontSize: 20 }}>Review what I heard</h3>
            </div>
            <p className="preview-hint">I found these facts. Review and confirm before saving:</p>
            <div id="fact-list">
              {pendingFacts.map((fact, idx) => (
                <div key={idx} style={{ marginBottom: 10, padding: 10, background: '#111722', border: '1px solid rgba(167,185,213,0.13)', borderRadius: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#87e0c0', marginRight: 8 }}>{fact.type}</span>
                    <input
                      type="text"
                      value={fact.label}
                      onChange={(e) => editFactLabel(idx, e)}
                      style={{
                        flex: 1,
                        fontWeight: 600,
                        fontSize: 14,
                        background: 'transparent',
                        color: '#edf2fa',
                        border: 'none',
                        borderBottom: '1px solid rgba(167,185,213,0.3)',
                        padding: '2px 4px',
                      }}
                    />
                  </div>
                  <textarea
                    value={fact.description}
                    onChange={(e) => editFactDescription(idx, e)}
                    rows={2}
                    style={{
                      width: '100%',
                      fontSize: 13,
                      color: '#8794a8',
                      background: 'transparent',
                      border: 'none',
                      resize: 'vertical',
                      marginBottom: 6,
                    }}
                  />
                  {fact.when && (
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 11, color: '#8794a8', marginRight: 6 }}>When:</span>
                      <input
                        type="text"
                        value={fact.when}
                        onChange={(e) => editFactWhen(idx, e)}
                        style={{
                          fontSize: 12,
                          color: '#8794a8',
                          background: 'transparent',
                          border: 'none',
                          borderBottom: '1px solid rgba(167,185,213,0.3)',
                          padding: '2px 4px',
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => removeFact(idx)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#ff6b6b',
                          cursor: 'pointer',
                          fontSize: 12,
                          padding: 0,
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="preview-actions">
              <button className="btn" onClick={cancelFacts}>Cancel</button>
              <button className="btn btn-primary" onClick={confirmFacts} disabled={loading}>
                {loading ? 'Saving…' : `Save ${pendingFacts.length} fact(s)`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
