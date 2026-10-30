import { useCallback, useState } from 'react'

export default function LoginView({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/caregiver/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) throw new Error('Invalid credentials')
      onLogin()
    } catch {
      setError('Username o password non corretti.')
    } finally {
      setLoading(false)
    }
  }, [username, password, onLogin])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: 'calc(100vh - 64px)', background: '#0b0e14',
    }}>
      <div style={{
        background: '#111722', border: '1px solid rgba(167,185,213,0.13)',
        borderRadius: 16, padding: 40, width: 400, maxWidth: '90vw',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <span style={{ fontSize: 40, display: 'block', marginBottom: 8 }}>m</span>
          <div style={{ color: '#87e0c0', fontSize: 28, fontWeight: 700, letterSpacing: -1 }}>Memora</div>
          <div style={{ color: '#8794a8', fontSize: 13, marginTop: 6 }}>Caregiver access</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, color: '#8794a8', marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
                color: '#edf2fa', fontSize: 14, boxSizing: 'border-box',
              }}
            />
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 12, color: '#8794a8', marginBottom: 6, letterSpacing: 1, textTransform: 'uppercase' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid rgba(167,185,213,0.13)', background: '#0b0e14',
                color: '#edf2fa', fontSize: 14, boxSizing: 'border-box',
              }}
            />
          </div>
          {error && (
            <div style={{
              background: '#2d1a1a', border: '1px solid #ff6b6b', borderRadius: 8,
              padding: 12, color: '#ff9999', fontSize: 13, marginBottom: 20,
            }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '10px 16px', borderRadius: 8,
              border: 'none', background: '#87e0c0', color: '#0b0e14',
              fontWeight: 700, fontSize: 14, cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Signing in…' : 'Log in'}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center', color: '#8794a8', fontSize: 12 }}>
          Caregiver restricted area. Demo data is fictional.
        </div>
      </div>
    </div>
  )
}
