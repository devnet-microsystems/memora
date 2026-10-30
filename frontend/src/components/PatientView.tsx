import { useState, useEffect, useRef, useCallback } from 'react'

const PATIENT_ID = 'patient_alex'

interface TodayItem {
  id: string
  kind: string
  time: string | null
  text: string
  status: string
  med_state: string | null
  due_time: string | null
}

interface AACNode {
  id: string
  content: string
}

interface Fact {
  type: string
  label: string
  description: string
  when: string
}

export default function PatientView({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [greeting, setGreeting] = useState('Hello')
  const [todayItems, setTodayItems] = useState<TodayItem[]>([])
  const [weekday, setWeekday] = useState('')
  const [dateLabel, setDateLabel] = useState('')
  const [partOfDay, setPartOfDay] = useState('')

  const [chatHistory, setChatHistory] = useState<{ sender: string; text: string }[]>([])
  const [chatLatest, setChatLatest] = useState('')
  const [historyVisible, setHistoryVisible] = useState(false)

  const [aacButtons, setAACButtons] = useState<AACNode[]>([])

  const [orbState, setOrbState] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle')
  const [orbStatusText, setOrbStatusText] = useState('Tap to talk')
  const [isProcessing, setIsProcessing] = useState(false)

  const [factPreview, setFactPreview] = useState(false)
  const [transcriptPreview, setTranscriptPreview] = useState(false)
  const [pendingTranscript, setPendingTranscript] = useState('')
  const [pendingFacts, setPendingFacts] = useState<Fact[]>([])
  const [pendingIsDiary, setPendingIsDiary] = useState(false)

  const [diaryMode, setDiaryMode] = useState(false)
  const [diarySessionId, setDiarySessionId] = useState('')

  const [sosMessage, setSosMessage] = useState('Alert sent, waiting for confirmation')

  const [medReminderVisible, setMedReminderVisible] = useState(false)
  const [medReminderTitle, setMedReminderTitle] = useState('Time for your medicine')
  const [medReminderName, setMedReminderName] = useState('')
  const [medReminderButtonsVisible, setMedReminderButtonsVisible] = useState(true)
  const [medReminderFeedback, setMedReminderFeedback] = useState('')
  const [medReminderFeedbackVisible, setMedReminderFeedbackVisible] = useState(false)
  const [activeMedId, setActiveMedId] = useState<string | null>(null)
  const [lastSpokenMedId, setLastSpokenMedId] = useState<string | null>(null)

  const [networkError, setNetworkError] = useState(false)
  const [voiceUnsupported, setVoiceUnsupported] = useState(false)

  const speechRecognitionRef = useRef<any>(null)
  const sosPollRef = useRef<any>(null)
  const voicesRef = useRef<SpeechSynthesisVoice[]>([])
  const speakSessionRef = useRef(0)
  const speakSafetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const recognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  const loadToday = useCallback(async () => {
    try {
      setNetworkError(false)
      const res = await fetch(`/api/today?patient_id=${PATIENT_ID}&lang=en`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setWeekday(data.weekday || '')
      setDateLabel(data.date_label || '')
      setPartOfDay(data.part_of_day || '')
      setGreeting('Hello' + (data.patient_name ? ' ' + data.patient_name : ''))
      setTodayItems(data.items || [])
    } catch {
      setNetworkError(true)
    }
  }, [])

  const loadAAC = useCallback(async () => {
    try {
      const res = await fetch('/api/aac')
      if (!res.ok) throw new Error()
      const data = await res.json()
      if (data.length > 0) {
        setAACButtons(data.map((n: any) => ({ id: n.id, content: n.content || n.id })))
      } else {
        setAACButtons([
          { id: 'caa_thirsty', content: '💧 I\'m thirsty' },
          { id: 'caa_medicine', content: '💊 Medicine?' },
          { id: 'caa_bathroom', content: '🚽 Bathroom' },
          { id: 'caa_family', content: '📞 Call family' },
        ])
      }
    } catch {
      setAACButtons([
        { id: 'caa_thirsty', content: '💧 I\'m thirsty' },
        { id: 'caa_medicine', content: '💊 Medicine?' },
        { id: 'caa_bathroom', content: '🚽 Bathroom' },
        { id: 'caa_family', content: '📞 Call family' },
      ])
    }
  }, [])

  const appendMessage = useCallback((sender: string, text: string) => {
    setChatHistory(prev => [...prev, { sender, text }])
    setChatLatest(text)
  }, [])

  const speakResponse = useCallback((text: string) => {
    if (speakSafetyTimerRef.current) {
      clearTimeout(speakSafetyTimerRef.current)
      speakSafetyTimerRef.current = null
    }

    const sessionId = ++speakSessionRef.current

    const resetSpeaking = () => {
      if (speakSessionRef.current !== sessionId) return
      if (speakSafetyTimerRef.current) {
        clearTimeout(speakSafetyTimerRef.current)
        speakSafetyTimerRef.current = null
      }
      setOrbState('idle')
      setOrbStatusText('Tap to talk')
    }

    if (!('speechSynthesis' in window)) {
      resetSpeaking()
      return
    }

    const synth = window.speechSynthesis
    synth.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-US'
    utterance.rate = 0.9

    const englishVoice =
      voicesRef.current.find((v) => v.name === 'Samantha' && v.lang === 'en-US') ||
      voicesRef.current.find(
        (v) =>
          v.lang.startsWith('en') &&
          !/fun|alien|badger|bells|boing|bubbles|caricat|cellos|deranged|good news|hysterical|organ|pepper|stem|trinoids|whacky|zoo|bad news/i.test(v.name)
      )

    if (englishVoice) {
      utterance.voice = englishVoice
    }

    utterance.onstart = () => {
      if (speakSessionRef.current !== sessionId) return
      setOrbState('speaking')
      setOrbStatusText('Speaking...')
    }

    utterance.onend = () => {
      if (speakSessionRef.current !== sessionId) return
      resetSpeaking()
    }

    utterance.onerror = () => {
      if (speakSessionRef.current !== sessionId) return
      resetSpeaking()
      appendMessage('System', 'Voice playback failed. The response text is shown above.')
    }

    synth.speak(utterance)

    setOrbState('speaking')
    setOrbStatusText('Speaking...')

    const estimatedMs = Math.min(Math.max(3000, text.length * 80), 15000)

    speakSafetyTimerRef.current = setTimeout(() => {
      if (speakSessionRef.current !== sessionId) return
      if (!synth.speaking && !synth.pending) {
        resetSpeaking()
        return
      }
      synth.cancel()
      resetSpeaking()
      appendMessage('System', 'Voice playback did not complete. The response text is shown above.')
    }, estimatedMs)
  }, [appendMessage])

  useEffect(() => {
    if (!('speechSynthesis' in window)) return
    const synth = window.speechSynthesis
    const loadVoices = () => {
      voicesRef.current = synth.getVoices()
    }
    if (synth.getVoices().length > 0) {
      loadVoices()
    }
    synth.addEventListener('voiceschanged', loadVoices)
    return () => synth.removeEventListener('voiceschanged', loadVoices)
  }, [])

  const askAgent = useCallback(async (text: string) => {
    try {
      setNetworkError(false)
      let endpoint = '/api/chat'
      let bodyData: any = { user_input: text, patient_id: PATIENT_ID }

      if (diaryMode) {
        endpoint = '/api/diary/turn'
        bodyData = { session_id: diarySessionId, text: text }
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyData),
      })
      if (!res.ok) throw new Error('API Error')
      const data = await res.json()

      if (data.reply) {
        appendMessage('Memora', data.reply)
        speakResponse(data.reply)
        if (diaryMode && data.reply.includes("Let's take a break")) {
          setDiaryMode(false)
          setDiarySessionId('')
        }
      } else if (data.response) {
        appendMessage('Memora', data.response)
        speakResponse(data.response)
      }
    } catch {
      setNetworkError(true)
      appendMessage('System', 'Connection error.')
      speakResponse('There was a connection error.')
    } finally {
      setIsProcessing(false)
    }
  }, [diaryMode, diarySessionId, appendMessage, speakResponse])

  useEffect(() => {
    loadToday()
    loadAAC()
    const todayInterval = setInterval(loadToday, 30000)
    const aacInterval = setInterval(loadAAC, 15000)
    return () => {
      clearInterval(todayInterval)
      clearInterval(aacInterval)
    }
  }, [loadToday, loadAAC])

  useEffect(() => {
    if (!recognitionCtor) {
      setVoiceUnsupported(true)
      setOrbState('idle')
      setOrbStatusText('Voice recognition not supported in this browser.')
      appendMessage('System', 'Voice recognition is not supported in this browser.')
    }
  }, [recognitionCtor, appendMessage])

  const startListening = () => {
    if (voiceUnsupported || !recognitionCtor || speechRecognitionRef.current || isProcessing || orbState === 'speaking') return
    const recognition = new recognitionCtor()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.continuous = false

    const finalSegments: string[] = []
    const processedIndices = new Set<number>()

    recognition.onstart = () => {
      if (speechRecognitionRef.current !== recognition) return
      setOrbState('listening')
      setOrbStatusText('I\'m listening')
    }

    recognition.onresult = (event: any) => {
      if (speechRecognitionRef.current !== recognition) return
      if (isProcessing) return
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

      const transcript = finalSegments.filter(Boolean).join(' ').trim()
      if (!transcript) {
        appendMessage('System', "I didn't catch anything. Please try again.")
        setIsProcessing(false)
        setOrbState('idle')
        setOrbStatusText('Tap to talk')
        return
      }

      setIsProcessing(true)
      setOrbState('thinking')
      setOrbStatusText('Thinking...')
      setPendingTranscript(transcript)
      setPendingIsDiary(diaryMode)
      const textarea = document.getElementById('preview-text') as HTMLTextAreaElement | null
      if (textarea) textarea.value = transcript
      setTranscriptPreview(true)
    }

    recognition.onerror = (event: any) => {
      if (speechRecognitionRef.current !== recognition) return
      const reset = () => {
        speechRecognitionRef.current = null
        setIsProcessing(false)
        setOrbState('idle')
        setOrbStatusText('Tap to talk')
      }

      if (event.error === 'aborted') {
        reset()
        return
      }

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

      appendMessage('System', msg)
      speakResponse(msg)
      reset()
    }

    speechRecognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      speechRecognitionRef.current = null
      setIsProcessing(false)
      setOrbState('idle')
      setOrbStatusText('Tap to talk')
    }
  }

  const toggleDiaryMode = async () => {
    setDiaryMode(!diaryMode)
    if (!diaryMode) {
      setDiarySessionId('sess_' + Date.now())
      document.getElementById('chat-history')?.replaceChildren()
      setChatHistory([])
      setChatLatest('')
      setOrbState('idle')
      setOrbStatusText('Tap to talk')
    } else {
      try {
        await fetch('/api/diary/end', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: diarySessionId }),
        })
      } catch { console.error('diary end failed') }
      setDiarySessionId('')
      setChatHistory([])
      setChatLatest('')
    }
  }

  const useTranscript = () => {
    if (!pendingTranscript) return
    const text = pendingTranscript.trim()
    if (!text) {
      appendMessage('System', 'Empty text. Please say something or cancel.')
      return
    }
    setTranscriptPreview(false)
    setPendingTranscript('')
    pendingIsDiary ? null : null
    appendMessage('You', text)
    askAgent(text)
  }

  const cancelTranscript = () => {
    setTranscriptPreview(false)
    setPendingTranscript('')
    setIsProcessing(false)
    setOrbState('idle')
    setOrbStatusText('Tap to talk')
  }

  const confirmFacts = async () => {
    if (!pendingFacts || pendingFacts.length === 0) return
    try {
      const res = await fetch('/api/voice/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts: pendingFacts }),
      })
      if (!res.ok) throw new Error('API Error')
      const data = await res.json()
      setFactPreview(false)
      setPendingFacts([])
      appendMessage('System', `Saved ${data.created} fact(s) to memory for caregiver review.`)
      speakResponse(`Saved ${data.created} fact(s) to memory for caregiver review.`)
      loadToday()
    } catch {
      setNetworkError(true)
      appendMessage('System', 'Could not save. Please try again.')
    }
  }

  const cancelFacts = () => {
    setFactPreview(false)
    setPendingFacts([])
    setIsProcessing(false)
    setOrbState('idle')
    setOrbStatusText('Tap to talk')
  }

  const sendSOS = async () => {
    setSosMessage('Alert sent, waiting for confirmation')
    try {
      const res = await fetch('/api/sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_id: PATIENT_ID, type: 'sos' }),
      })
      if (!res.ok) throw new Error('Network')
      const data = await res.json()

      let tries = 0
      if (sosPollRef.current) clearInterval(sosPollRef.current)
      sosPollRef.current = setInterval(async () => {
        tries++
        try {
          const r = await fetch(`/api/alerts/${encodeURIComponent(data.alert_id)}`)
          const a = await r.json()
          if (a.status === 'acknowledged') {
            setSosMessage('Your caregiver has seen the alert. Help is on the way.')
            if (navigator.vibrate) navigator.vibrate([100, 50, 100])
            clearInterval(sosPollRef.current)
            sosPollRef.current = null
            setTimeout(() => { setSosMessage('Alert sent, waiting for confirmation') }, 15000)
          }
        } catch { /* keep waiting */ }
        if (tries > 90) {
          setSosMessage('No confirmation yet. Call 112 if it is urgent.')
          clearInterval(sosPollRef.current)
          sosPollRef.current = null
        }
      }, 4000)
    } catch {
      setNetworkError(true)
    }
  }

  const showMedReminder = (med: any) => {
    setMedReminderVisible(true)
    setMedReminderTitle('Time for your medicine')
    setMedReminderName(`${med.text} (${med.time})`)
    setMedReminderButtonsVisible(true)
    setMedReminderFeedbackVisible(false)
    setActiveMedId(med.id)
    if (lastSpokenMedId !== med.id) {
      speakResponse(`It's time for your medicine: ${med.text}`)
      setLastSpokenMedId(med.id)
    }
  }

  const confirmReminder = async (status: 'confirmed' | 'snoozed' | 'unsure') => {
    if (!activeMedId) return

    if (status === 'unsure') {
      setMedReminderButtonsVisible(false)
      setMedReminderFeedback("I've asked your caregiver to help you.")
      setMedReminderFeedbackVisible(true)
      speakResponse("I've asked your caregiver to help you.")
    } else if (status === 'confirmed') {
      setMedReminderButtonsVisible(false)
      setMedReminderFeedback("Great, I've recorded that you took it.")
      setMedReminderFeedbackVisible(true)
      speakResponse("Great, I've recorded that you took it.")
    }

    try {
      const res = await fetch('/api/med/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ med_id: activeMedId, status }),
      })
      if (!res.ok) throw new Error()
      setNetworkError(false)
    } catch {
      setNetworkError(true)
    }

    if (status === 'snoozed') {
      setMedReminderVisible(false)
      loadToday()
    } else {
      setTimeout(() => {
        setMedReminderVisible(false)
        loadToday()
      }, 4000)
    }
  }

  useEffect(() => {
    let activeMed: TodayItem | null = null
    for (const item of todayItems) {
      if (item.kind === 'med' && (item.med_state === 'due' || item.med_state === 'missed')) {
        if (!activeMed) activeMed = item
      }
    }
    if (activeMed && medReminderVisible === false) {
      showMedReminder(activeMed)
    } else if (!activeMed && medReminderVisible) {
      setMedReminderVisible(false)
      setActiveMedId(null)
    }
  }, [todayItems, medReminderVisible])

  return (
    <div className="memora-patient-app">
      {networkError && (
        <div className="network-error">No connection. Please call your caregiver or 112.</div>
      )}

      <div className="patient-container">
        <div className="patient-header">
          <span id="header-greeting">{greeting}</span>
        </div>

        <div className="patient-card">
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <h2 id="today-weekday" style={{ margin: 0, fontSize: 32, color: '#87e0c0' }}>{weekday}</h2>
            <div id="today-date" style={{ fontSize: 20, color: '#edf2fa', marginBottom: 5 }}>{dateLabel}</div>
            <div id="today-greeting" style={{ fontSize: 24, fontWeight: 700 }}>{partOfDay}</div>
          </div>
          <div id="today-list">
            {todayItems.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#8794a8', fontSize: 16, padding: 20 }}>No events for today.</div>
            ) : (
              todayItems.map(item => {
                const isPast = item.time && item.time < new Date().toTimeString().substring(0, 5)
                let icon = ''
                if (item.kind === 'med') icon = '💊'
                else if (item.kind === 'habit') icon = '🔁'
                else if (item.kind === 'event') icon = '📅'

                let checkStr = ''
                if (item.kind === 'med' && item.status === 'confirmed') {
                  checkStr = ' <span style="color: #00ff88; font-weight: bold; font-size: 24px;">✓</span>'
                }

                return (
                  <div key={item.id} className="today-item" style={{ color: isPast ? '#8794a8' : 'inherit' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <span style={{ display: 'inline-block', minWidth: 70 }} title="Time not specified">{item.time || '—'}</span>
                      <span style={{ margin: '0 10px' }}>{icon}</span>
                      <span style={{ flex: 1, fontWeight: 500 }}>{item.text}</span>
                      <span dangerouslySetInnerHTML={{ __html: checkStr }} />
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        <div className="orb-container">
          <button
            id="btn-speak"
            className={`orb state-${orbState}`}
            onClick={startListening}
            aria-label="Tap to talk"
            disabled={isProcessing || voiceUnsupported}
          >
            🎙️
          </button>
          <div id="orb-status-text" className="orb-status-text">{orbStatusText}</div>
        </div>

        <div className="chat-latest" id="chat-latest">{chatLatest}</div>
        <button
          className="btn-history"
          id="btn-history"
          onClick={() => setHistoryVisible(!historyVisible)}
          aria-expanded={historyVisible}
          aria-controls="chat-history"
        >
          {historyVisible ? 'Hide History' : 'Show History'}
        </button>
        {historyVisible && (
          <div id="chat-history">
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <strong style={{ color: msg.sender === 'Memora' ? '#87e0c0' : '#edf2fa' }}>{msg.sender}: </strong>
                <span style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</span>
              </div>
            ))}
          </div>
        )}

        <div className="aac-grid" id="aac-grid">
          {aacButtons.map(btn => (
            <button
              key={btn.id}
              className="btn-aac"
              onClick={() => {
                appendMessage('You', btn.content)
                askAgent(btn.content)
              }}
            >
              {btn.content}
            </button>
          ))}
        </div>

        <button
          id="btn-diary"
          className="btn-diary"
          onClick={toggleDiaryMode}
        >
          {diaryMode ? 'Stop' : '📖 Tell me a story'}
        </button>
        {diaryMode && (
          <div id="diary-banner">
            <span>Diary Mode Active</span>
            <button onClick={toggleDiaryMode}>Stop</button>
          </div>
        )}

        <div className="sos-disclaimer">Memora is not an emergency service. In an emergency call 112.</div>
        <div className="sos-bar">
          <button id="btn-sos" className="sos-btn" onClick={sendSOS}>🆘 Call for help</button>
          <div id="sos-message" className="sos-msg">{sosMessage}</div>
        </div>

        {/* Fact Preview Overlay */}
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
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#87e0c0', marginRight: 8 }}>{fact.type}</span>
                    <span style={{ fontWeight: 500, display: 'block', marginBottom: 4 }}>{fact.label}</span>
                    <span style={{ display: 'block', fontSize: 14, color: '#8794a8', marginTop: 4 }}>{fact.description}</span>
                    {fact.when && <span style={{ display: 'block', fontSize: 13, color: '#8794a8', marginTop: 2 }}>When: {fact.when}</span>}
                  </div>
                ))}
              </div>
              <div className="preview-actions">
                <button className="btn" onClick={cancelFacts}>Cancel</button>
                <button className="btn btn-primary" onClick={confirmFacts}>Save to memory</button>
              </div>
            </div>
          </div>
        )}

        {/* Transcript Preview Overlay */}
        {transcriptPreview && (
          <div className="preview-overlay" style={{ display: 'block' }}>
            <div className="preview-card">
              <div className="preview-header">
                <span style={{ fontSize: 24 }}>🎙️</span>
                <h3 style={{ margin: 0, color: '#edf2fa', fontSize: 20 }}>Review what you said</h3>
              </div>
              <p className="preview-hint">Review and edit your transcript before sending:</p>
              <textarea id="preview-text" className="form-control" rows={3} defaultValue={pendingTranscript} />
              <div className="preview-actions">
                <button className="btn" onClick={cancelTranscript}>Cancel</button>
                <button className="btn btn-primary" onClick={useTranscript}>Use this text</button>
              </div>
            </div>
          </div>
        )}

        {/* Med Reminder Overlay */}
        {medReminderVisible && (
          <div className="med-reminder-overlay" style={{ display: 'flex' }}>
            <div className="med-reminder-card">
              <div style={{ fontSize: 64, marginBottom: 20 }}>💊</div>
              <h2 id="med-reminder-title" style={{ fontSize: 32, marginTop: 0, marginBottom: 15, color: '#ff4444' }}>{medReminderTitle}</h2>
              <div id="med-reminder-name" style={{ fontSize: 24, fontWeight: 700, marginBottom: 30 }}>{medReminderName}</div>
              <div id="med-reminder-buttons" style={{ display: medReminderButtonsVisible ? 'flex' : 'none', flexDirection: 'column', gap: 15 }}>
                <button onClick={() => confirmReminder('confirmed')} style={{ minHeight: 64, fontSize: 24, background: '#00ff88', color: '#0b0e14', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 700 }}>I took it</button>
                <button onClick={() => confirmReminder('snoozed')} style={{ minHeight: 64, fontSize: 24, background: '#f59e0b', color: '#fff', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 700 }}>Not yet</button>
                <button onClick={() => confirmReminder('unsure')} style={{ minHeight: 64, fontSize: 24, background: '#87e0c0', color: '#0b0e14', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 700 }}>I'm not sure</button>
              </div>
              {medReminderFeedbackVisible && (
                <div id="med-reminder-feedback" style={{ fontSize: 24, fontWeight: 700, marginTop: 20, color: '#edf2fa' }}>{medReminderFeedback}</div>
              )}
            </div>
          </div>
        )}

        <nav className="patient-footer">
          <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('/caregiver') }} style={{ color: '#87e0c0', textDecoration: 'none', fontSize: 12 }}>
            ← Caregiver Dashboard
          </a>
        </nav>
      </div>
    </div>
  )
}
