import { useState, useEffect, useCallback } from 'react'

interface TimelineItem {
  id: string
  content: string
  event_date: string
}

interface MemoryNode {
  id: string
  label: string
  group: string
  timestamp: number
}

interface MemoryEdge {
  from: string
  to: string
  label: string
}

interface MemoryGraph {
  nodes: MemoryNode[]
  edges: MemoryEdge[]
}

interface TodayResponse {
  patient_name?: string
  weekday?: string
  date_label?: string
  part_of_day?: string
  items: Array<{
    id: string
    kind: string
    time: string | null
    text: string
    status: string
    med_state: string | null
    due_time: string
  }>
}

function formatDate(ts: number | string | undefined | null): string {
  if (ts == null) return 'Data not available'
  const d = typeof ts === 'string' ? new Date(ts) : new Date(ts * 1000)
  if (isNaN(d.getTime())) return String(ts)
  return d.toLocaleDateString('it-IT', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatTime(ts: number | string | undefined | null): string {
  if (ts == null) return ''
  const d = typeof ts === 'string' ? new Date(ts) : new Date(ts * 1000)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  person: { label: 'Person', color: '#87e0c0' },
  place: { label: 'Luogo', color: '#0088ff' },
  event: { label: 'Evento', color: '#ffaa00' },
  habit: { label: 'Abitudine', color: '#00ff88' },
  med: { label: 'Farmaco', color: '#ff4444' },
  preference: { label: 'Preferenza', color: '#00ffff' },
  condition: { label: 'Condizione', color: '#ffaa00' },
  pending: { label: 'In attesa', color: '#888888' },
  alert: { label: 'Allerta', color: '#ff0088' },
  flag: { label: 'Segnalazione', color: '#ffaa00' },
  interaction: { label: 'Interazione', color: '#888888' },
  caa_button: { label: 'Pulsante CAA', color: '#4488ff' },
}

const escapeHTML = (str: string): string => {
  if (!str) return ''
  return str.toString().replace(/[&<>'"]/g,
    (tag: string) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  )
}

export default function StoryView({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [title, setTitle] = useState("Life Book")
  const [patientName, setPatientName] = useState<string | null>(null)
  const [timeline, setTimeline] = useState<TimelineItem[]>([])
  const [graph, setGraph] = useState<MemoryGraph>({ nodes: [], edges: [] })
  const [today, setToday] = useState<TodayResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [todayRes, timelineRes, graphRes] = await Promise.all([
        fetch('/api/today?patient_id=patient_alex&lang=en'),
        fetch('/api/timeline'),
        fetch('/api/memory'),
      ])

      if (todayRes.ok) {
        const todayData = await todayRes.json()
        setToday(todayData)
        if (todayData.patient_name) {
          setPatientName(todayData.patient_name)
          setTitle(`${todayData.patient_name}'s Life Book`)
        }
      }

      if (timelineRes.ok) {
        const timelineData = await timelineRes.json()
        setTimeline(Array.isArray(timelineData) ? timelineData : [])
      }

      if (graphRes.ok) {
        const graphData = await graphRes.json()
        setGraph(graphData || { nodes: [], edges: [] })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load Life Book.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStory()
  }, [loadStory])

  const nodeById = new Map<string, MemoryNode>()
  graph.nodes.forEach((n) => nodeById.set(n.id, n))

  const narrativeNodes = graph.nodes.filter((n) =>
    n.group !== 'alert' && n.group !== 'flag' && n.group !== 'interaction' && n.group !== 'pending'
  )

  const nodesByType = new Map<string, MemoryNode[]>()
  narrativeNodes.forEach((n) => {
    const arr = nodesByType.get(n.group) || []
    arr.push(n)
    nodesByType.set(n.group, arr)
  })

  nodesByType.forEach((arr) => arr.sort((a, b) => a.timestamp - b.timestamp))

  const edgesBySource = new Map<string, MemoryEdge[]>()
  graph.edges.forEach((e) => {
    const arr = edgesBySource.get(e.from) || []
    arr.push(e)
    edgesBySource.set(e.from, arr)
  })

  const hasStories = timeline.length > 0
  const hasAnyData = graph.nodes.length > 0 || (today && today.items && today.items.length > 0) || patientName != null

  const demoNotice = hasAnyData
    ? (
      <div style={{
        background: 'rgba(245, 158, 11, 0.1)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        borderRadius: 8,
        padding: 12,
        marginBottom: 24,
        fontSize: 13,
        color: '#fbbf24',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
      }}>
        <span style={{ fontSize: 18 }}>⚠️</span>
        <div>
          <strong style={{ color: '#fdba74' }}>Simulated demo data</strong>
            <p style={{ margin: '4px 0 0 0', fontSize: 12, color: '#fbbf24' }}>
              The Life Book displays fictional demonstration data for Alex Morgan. These are not real personal memories or clinical records. Memora is not a medical device.
            </p>
        </div>
      </div>
    )
    : null

  // Pre-compute all mapped JSX arrays
  const todayItemsJSX = today && today.items && today.items.length > 0
    ? today.items.map((item) => {
      const isMed = item.kind === 'med'
      const isConfirmed = item.status === 'confirmed'
      const icon = isMed ? '💊' : item.kind === 'event' ? '📅' : '🔁'
      return (
        <div key={item.id} style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: 10,
          background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 8,
        }}>
          <span style={{ fontSize: 18 }}>{icon}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#edf2fa' }}>{escapeHTML(item.text)}</div>
            <div style={{ fontSize: 12, color: '#8794a8' }}>
              {item.time ? item.time : 'Orario non specificato'}
              {isMed && item.med_state && item.med_state !== 'none' && ` • ${item.med_state}`}
            </div>
          </div>
          {isConfirmed && (
            <span style={{ color: '#00ff88', fontWeight: 700, fontSize: 20 }}>✓</span>
          )}
        </div>
      )
    })
    : null

  const peopleJSX = nodesByType.has('person') && nodesByType.get('person')!.length > 0
    ? nodesByType.get('person')!.map((person) => {
      const meta = (person as any).meta || {}
      const edges = edgesBySource.get(person.id) || []
      const relations = edges.map((e) => {
        const target = nodeById.get(e.to)
        return target ? `${e.label} → ${escapeHTML(target.label || target.id)}` : e.label
      })
      return (
        <div key={person.id} style={{
          padding: 14, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 8,
        }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#edf2fa', marginBottom: 4 }}>
            {escapeHTML(person.label || person.id)}
            {meta.role && (
              <span style={{ fontSize: 11, color: '#87e0c0', textTransform: 'uppercase', letterSpacing: 1, marginLeft: 8 }}>
                {meta.role}
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: '#8794a8', marginBottom: 6 }}>
            {escapeHTML(person.label || '')}
          </div>
          {relations.length > 0 && (
            <div style={{ fontSize: 12, color: '#8794a8' }}>
              <span style={{ fontWeight: 600, color: '#8794a8' }}>Relazioni:</span> {relations.join('; ')}
            </div>
          )}
        </div>
      )
    })
    : null

  const placesJSX = nodesByType.has('place') && nodesByType.get('place')!.length > 0
    ? nodesByType.get('place')!.map((place) => (
      <div key={place.id} style={{
        padding: 14, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 8,
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#edf2fa', marginBottom: 4 }}>{escapeHTML(place.label || place.id)}</div>
        <div style={{ fontSize: 13, color: '#8794a8' }}>{escapeHTML(place.label || '')}</div>
      </div>
    ))
    : null

  const medsJSX = nodesByType.has('med') && nodesByType.get('med')!.length > 0
    ? nodesByType.get('med')!.map((med) => {
      const meta = (med as any).meta || {}
      return (
        <div key={med.id} style={{
          padding: 14, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
          borderRadius: 8,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#edf2fa', marginBottom: 2 }}>{escapeHTML(med.label || med.id)}</div>
            <span style={{ fontSize: 11, color: '#ff4444', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
              FICTIONAL TEST DATA
            </span>
          </div>
          <div style={{ fontSize: 13, color: '#8794a8', marginBottom: 6 }}>{escapeHTML(med.label || '')}</div>
          <div style={{ fontSize: 12, color: '#8794a8' }}>
            {meta.dosage && <span>Dosaggio: {escapeHTML(meta.dosage)}</span>}
            {meta.frequency && <span style={{ marginLeft: 8 }}>Frequenza: {escapeHTML(meta.frequency)}</span>}
            {meta.time && <span style={{ marginLeft: 8 }}>{escapeHTML(meta.time)}</span>}
          </div>
        </div>
      )
    })
    : null

  const sectionTypes = ['habit', 'preference', 'condition', 'event']
  const habitSections = sectionTypes
    .filter((t) => nodesByType.has(t) && nodesByType.get(t)!.length > 0)
    .map((type) => {
      const typeNodes = nodesByType.get(type)!
      const typeLabel = TYPE_LABELS[type].label
      return (
        <section key={type} style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
            {typeLabel}
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {typeNodes.map((node) => (
              <div key={node.id} style={{
                padding: 14, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
                borderRadius: 8,
              }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#edf2fa', marginBottom: 4 }}>{escapeHTML(node.label || node.id)}</div>
                <div style={{ fontSize: 13, color: '#8794a8' }}>{escapeHTML(node.label || '')}</div>
              </div>
            ))}
          </div>
        </section>
      )
    })

  const storiesJSX = hasStories
    ? timeline.map((item) => (
      <div key={item.id} style={{
        padding: 16, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#87e0c0' }}>
          {formatDate(item.event_date)}
          {item.event_date && <span style={{ fontSize: 12, color: '#8794a8', marginLeft: 8 }}>{formatTime(item.event_date)}</span>}
        </div>
        <div style={{ fontSize: 15, color: '#edf2fa', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {escapeHTML(item.content)}
        </div>
      </div>
    ))
    : null

  const memoryTimelineJSX = narrativeNodes.length > 0 && !hasStories
    ? narrativeNodes.map((node) => (
      <div key={node.id} style={{
        padding: 14, background: '#0b0e14', border: '1px solid rgba(167, 185, 213, 0.13)',
        borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: TYPE_LABELS[node.group].color || '#8794a8' }}>
            {escapeHTML(node.label || node.id)}
          </div>
          <span style={{ fontSize: 11, color: '#8794a8' }}>{formatDate(node.timestamp)}</span>
        </div>
        <div style={{ fontSize: 13, color: '#8794a8', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
          {escapeHTML(node.label || '')}
        </div>
      </div>
    ))
    : null

  return (
    <div className="story-view">
      <nav className="story-nav">
        <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('/caregiver') }} style={{ color: '#87e0c0', textDecoration: 'none', marginRight: 16 }}>
          ← Caregiver Dashboard
        </a>
        <button className="btn-print" onClick={() => window.print()}>🖨️ Print / Save as PDF</button>
      </nav>

      {demoNotice}

      <div className="story-container">
        <h1 id="book-title">{title}</h1>

        {loading && (
          <div style={{ fontSize: 20, color: '#8794a8', textAlign: 'center', padding: 40 }}>Loading Life Book…</div>
        )}

        {error && (
          <div style={{ color: '#ff4444', textAlign: 'center', padding: 40 }}>{error}</div>
        )}

        {!loading && !error && (
          <>
            {patientName && (
              <div style={{
                background: '#111722',
                border: '1px solid rgba(167, 185, 213, 0.13)',
                borderRadius: 12,
                padding: 20,
                marginBottom: 24,
                display: 'flex',
                alignItems: 'center',
                gap: 16,
              }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '50%',
                  background: 'rgba(135, 224, 192, 0.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 24, color: '#87e0c0',
                }}>{patientName.charAt(0).toUpperCase()}</div>
                <div>
                  <div style={{ fontSize: 11, letterSpacing: 1.6, textTransform: 'uppercase', color: '#8794a8', fontWeight: 700 }}>                  Patient profile</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#edf2fa' }}>{patientName}</div>
                </div>
              </div>
            )}

            {today && today.items && today.items.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  Today ({today.weekday || ''}, {today.date_label || ''})
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {todayItemsJSX}
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: '#8794a8' }}>
                  {today.part_of_day ? today.part_of_day : ''}
                </div>
              </section>
            )}

            {nodesByType.has('person') && nodesByType.get('person')!.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  People and relationships
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {peopleJSX}
                </div>
              </section>
            )}

            {nodesByType.has('place') && nodesByType.get('place')!.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  Places
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {placesJSX}
                </div>
              </section>
            )}

            {nodesByType.has('med') && nodesByType.get('med')!.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  Medications
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {medsJSX}
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: '#8794a8', fontStyle: 'italic' }}>
                  Medications shown are fictional test data, not prescriptions or medical advice.
                </div>
              </section>
            )}

            {habitSections.length > 0 && habitSections}

            {hasStories && (
              <section>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  Personal stories
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {storiesJSX}
                </div>
              </section>
            )}

            {narrativeNodes.length > 0 && !hasStories && (
              <section>
                <h2 style={{ fontSize: 20, color: '#edf2fa', marginBottom: 12, borderBottom: '1px solid rgba(167, 185, 213, 0.13)', paddingBottom: 8 }}>
                  Memory timeline
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {memoryTimelineJSX}
                </div>
              </section>
            )}

            {!hasAnyData && (
              <div style={{ textAlign: 'center', padding: 60, color: '#8794a8' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>📖</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#edf2fa', marginBottom: 8 }}>
                  No memories available
                </div>
                <div style={{ fontSize: 13 }}>                  The Life Book populates when the patient or caregiver adds memories, habits, or stories to the diary.</div>
              </div>
            )}
          </>
        )}
      </div>

      <footer className="story-footer">
        <div>
          <a href="https://github.com/memora" target="_blank" rel="noopener noreferrer">GitHub Repository</a>
          | <strong>Not a medical device</strong>
          | <em>Simulated demo data</em>
        </div>
      </footer>
    </div>
  )
}
