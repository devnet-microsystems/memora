import { useState, useEffect, useCallback, useRef } from 'react'
import Graph3D from './components/Graph3D'
import Overview from './components/Overview'
import PatientView from './components/PatientView'
import StoryView from './components/StoryView'
import JudgesView from './components/JudgesView'
import VoiceMemory from './components/VoiceMemory'
import MedicationsView from './components/MedicationsView'
import AlertsView from './components/AlertsView'
import PendingApprovalsView from './components/PendingApprovalsView'
import TimelineView from './components/TimelineView'
import ReportView from './components/ReportView'
import OnboardingView from './components/OnboardingView'
import SettingsView from './components/SettingsView'
import LoginView from './components/LoginView'
import './dashboard.css'

type ViewId = 'caregiver' | 'patient' | 'story' | 'judges'

const sections = [
  { id: 'overview', label: 'Overview', icon: '◫' },
  { id: 'meds', label: 'Medications', icon: '✚' },
  { id: 'alerts', label: 'Alerts', icon: '◉' },
  { id: 'stories', label: 'Pending Approvals', icon: '▤' },
  { id: 'timeline', label: 'People & Routine', icon: '⌁' },
  { id: 'graph', label: 'Memory Graph', icon: '◎' },
  { id: 'report', label: 'Weekly Report', icon: '▥' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
  { id: 'onboarding', label: 'AI Onboarding', icon: '◇' },
] as const

type SectionId = (typeof sections)[number]['id']

const viewFromPath = (path: string): ViewId => {
  if (path === '/patient') return 'patient'
  if (path === '/story') return 'story'
  if (path === '/judges') return 'judges'
  return 'caregiver'
}

export default function App() {
  const [view, setView] = useState<ViewId>(() => viewFromPath(window.location.pathname))
  const [active, setActive] = useState<SectionId>('overview')
  const [voiceMemoryOpen, setVoiceMemoryOpen] = useState(false)
  const [sosOpen, setSosOpen] = useState(false)
  const [sosMessage, setSosMessage] = useState<string | null>(null)
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [user, setUser] = useState<string | null>(null)

  const checkAuth = useCallback(async () => {
    try {
      const res = await fetch('/api/caregiver/me', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const data = await res.json()
        setAuthenticated(!!data.authenticated)
        setUser(data.user || null)
      } else {
        setAuthenticated(false)
        setUser(null)
      }
    } catch {
      setAuthenticated(false)
      setUser(null)
    } finally {
      // authChecked handled by caller
    }
  }, [])

  useEffect(() => {
    checkAuth().then(() => {})
  }, [checkAuth])

  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/caregiver')
      setView('caregiver')
      return
    }
    const onPopState = () => {
      setView(viewFromPath(window.location.pathname))
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  // SOS auto-refresh: poll alerts every 10 seconds to surface new alerts without manual refresh
  const [alertCount, setAlertCount] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const checkSosAlerts = useCallback(async () => {
    if (!authenticated) return
    try {
      const res = await fetch('/api/memory', {
        credentials: 'include',
      })
      if (!res.ok) return
      const data = await res.json()
      const openAlerts = (data.nodes || []).filter(
        (n: any) => n.group === 'alert' && n.status !== 'acknowledged'
      )
      setAlertCount(openAlerts.length)
      if (openAlerts.length > 0 && !sosOpen) {
        const latest = openAlerts[0]
        setSosMessage(`${latest.label} — acknowledge in Caregiver workspace`)
        setSosOpen(true)
      }
    } catch {
      // silently ignore poll errors
    }
  }, [authenticated, sosOpen])

  useEffect(() => {
    checkSosAlerts()
    intervalRef.current = setInterval(checkSosAlerts, 10000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [checkSosAlerts])

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, '', path)
    setView(viewFromPath(path))
  }, [])

  const handleLogout = useCallback(async () => {
    try {
      await fetch('/api/caregiver/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // ignore
    }
    setAuthenticated(false)
    setUser(null)
    navigate('/caregiver')
  }, [navigate])

  // Direct view routing: patient / story / judges bypass the caregiver workspace
  if (view === 'patient') return <PatientView onNavigate={navigate} />
  if (view === 'story') return <StoryView onNavigate={navigate} />
  if (view === 'judges') return <JudgesView onNavigate={navigate} />

  // Caregiver workspace requires authentication
  if (authenticated === null) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 64px)', background: '#0b0e14', color: '#8794a8' }}>
        Loading caregiver session…
      </div>
    )
  }
  if (authenticated === false) {
    return (
      <LoginView onLogin={() => { checkAuth().then(() => {}) }} />
    )
  }

  const current = sections.find((section) => section.id === active)!

  return (
    <div className="memora-app">
      <aside className="memora-sidebar">
        <a className="memora-brand" href="#" onClick={(e) => { e.preventDefault(); navigate('/caregiver') }} aria-label="Memora home">
          <span className="memora-brand-mark">m</span>
          <span>
            <strong>memora</strong>
            <small>CAREGIVER SPACE</small>
          </span>
        </a>

        <div className="memora-nav-label">WORKSPACE</div>
        <nav aria-label="Caregiver navigation">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`memora-nav-item ${active === section.id ? 'active' : ''}`}
              aria-current={active === section.id ? 'page' : undefined}
              onClick={() => { setVoiceMemoryOpen(false); setActive(section.id) }}
            >
              <span className="memora-nav-icon" aria-hidden="true">
                {section.icon}
              </span>
              <span>{section.label}</span>
              {section.id === 'alerts' && (
                <span className="memora-nav-dot" aria-label="Alerts" />
              )}
              {section.id === 'alerts' && alertCount > 0 && (
                <span style={{
                  width: 18, height: 18, borderRadius: '50%', background: '#ef4444',
                  color: '#fff', fontSize: 10, fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginLeft: 'auto',
                }}>
                  {alertCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="memora-sidebar-footer">
          <span className="memora-status-dot" />
          <span>Memory system</span>
          <span className="memora-status-text">Connected UI</span>
        </div>
      </aside>

      <main className="memora-main">
        <header className="memora-topbar">
          <div>
            <div className="memora-eyebrow">CAREGIVER WORKSPACE</div>
            <h1>{current.label}</h1>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <a className="memora-patient-link" href="#" onClick={(e) => { e.preventDefault(); navigate('/patient') }}>
              <span className="memora-avatar">P</span>
              <span>
                <strong>Patient view</strong>
                <small>Open patient experience ↗</small>
              </span>
            </a>
            <button
              type="button"
              className="memora-patient-link"
              onClick={() => setVoiceMemoryOpen(true)}
              style={{
                padding: '6px 12px',
                fontSize: '11px',
                border: '1px solid var(--muted)',
                borderRadius: 6,
                background: 'transparent',
                color: 'var(--muted)',
                textDecoration: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
              title="Add memory by voice"
            >
              <span style={{ fontSize: 14 }}>🎙️</span>
              <span>Add memory by voice</span>
            </button>
            <a href="#" className="memora-patient-link" style={{ padding: '6px 10px', fontSize: '11px', border: 'none', background: 'transparent', color: 'var(--muted)', textDecoration: 'none' }} onClick={(e) => { e.preventDefault(); navigate('/story') }}>
              Life Book
            </a>
            <a href="#" className="memora-patient-link" style={{ padding: '6px 10px', fontSize: '11px', border: 'none', background: 'transparent', color: 'var(--muted)', textDecoration: 'none' }} onClick={(e) => { e.preventDefault(); navigate('/judges') }}>
              Judges
            </a>
            {authenticated !== null && (
              authenticated ? (
                <button
                  type="button"
                  onClick={handleLogout}
                  style={{
                    padding: '6px 12px', fontSize: '11px', borderRadius: 6,
                    border: '1px solid #ff6b6b', background: 'transparent',
                    color: '#ff9999', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  Log out ({user})
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate('/caregiver')}
                  style={{
                    padding: '6px 12px', fontSize: '11px', borderRadius: 6,
                    border: '1px solid #87e0c0', background: 'transparent',
                    color: '#87e0c0', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  Log in
                </button>
              )
            )}
          </div>
        </header>

        <section className="memora-content">
          {voiceMemoryOpen ? (
            <div className="memora-voice-memory-wrapper" style={{ padding: 24 }}>
              <button
                type="button"
                onClick={() => setVoiceMemoryOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#8794a8',
                  fontSize: 13,
                  cursor: 'pointer',
                  marginBottom: 16,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span>← Back</span>
              </button>
              <VoiceMemory onSaved={() => {
                setVoiceMemoryOpen(false)
              }} />
            </div>
          ) : active === 'graph' ? (
            <div className="memora-graph-panel">
              <div className="memora-panel-heading">
                <div>
                  <div className="memora-eyebrow">CONNECTED MEMORIES</div>
                  <h2>Memory Graph</h2>
                  <p>Explore relationships between people, events and memories.</p>
                </div>
                <span className="memora-live-label">
                  <span className="memora-status-dot" /> LIVE VIEW
                </span>
              </div>
              <div className="memora-graph-canvas">
                <Graph3D />
              </div>
            </div>
          ) : active === 'overview' ? (
            <Overview />
          ) : active === 'meds' ? (
            <MedicationsView />
          ) : active === 'alerts' ? (
            <AlertsView />
          ) : active === 'stories' ? (
            <PendingApprovalsView />
          ) : active === 'timeline' ? (
            <TimelineView />
          ) : active === 'report' ? (
            <ReportView />
          ) : active === 'settings' ? (
            <SettingsView />
          ) : active === 'onboarding' ? (
            <OnboardingView />
          ) : (
            <Overview />
          )}
        </section>

        {sosOpen && (
          <div style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
            background: '#ef4444', color: '#fff', padding: 14, borderRadius: 12,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            maxWidth: 320, fontSize: 13, lineHeight: 1.5,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              🆘 New Alert
            </div>
            <div>{sosMessage}</div>
            <button
              onClick={() => { setSosOpen(false); setSosMessage(null); setActive('alerts') }}
              style={{
                marginTop: 10, padding: '6px 12px', borderRadius: 6,
                border: 'none', background: 'rgba(255,255,255,0.2)',
                color: '#fff', fontSize: 12, cursor: 'pointer',
              }}
            >
              Go to Alerts
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
