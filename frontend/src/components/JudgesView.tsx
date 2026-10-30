import { useState, useEffect } from 'react'

export default function JudgesView({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [encrypted, setEncrypted] = useState<boolean | null>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const [metricsLoading, setMetricsLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => { setEncrypted(d.encrypted === true) })
      .catch(() => setEncrypted(null))

    const loadMetrics = () => {
      fetch('/api/usage')
        .then(r => r.json())
        .then(d => { setMetrics(d); setMetricsLoading(false) })
        .catch(() => { setMetricsLoading(false) })
    }
    loadMetrics()
    const iv = setInterval(loadMetrics, 10000)
    return () => clearInterval(iv)
  }, [])

  return (
    <div className="judges-view">
      <nav className="judges-nav">
        <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('/caregiver') }} style={{ color: '#87e0c0', textDecoration: 'none', marginRight: 16 }}>
          ← Caregiver Dashboard
        </a>
        <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('/patient') }} style={{ color: '#87e0c0', textDecoration: 'none' }}>
          Patient App →
        </a>
      </nav>

      <h1 style={{ color: '#87e0c0', marginBottom: 30 }}>Memora — Technical Overview for Judges</h1>

      <div className="card section">
        <h2 className="card-title">1. 60-Second Overview</h2>
        <p>
          <strong>What is Memora?</strong> A private AI assistant acting as a second brain.<br />
          <strong>For whom?</strong> People with Mild Cognitive Impairment (MCI) and their caregivers.<br />
          <em style={{ color: '#87e0c0', fontSize: 16, display: 'block', marginTop: 10 }}>
            "The user forgets. The system doesn't."
          </em>
        </p>
      </div>

      <div className="card section">
        <h2 className="card-title">2. Try it in 60 seconds</h2>
        <div className="step">
          <div className="step-num">1</div>
          <div style={{ flex: 1 }}>
            Open the Patient App and say (or type): <strong>"Which medication is scheduled for 9 AM?"</strong>. Memora will route this to the memory graph and answer from Alex's real schedule.
          </div>
          <a href="#" className="btn btn-primary" onClick={(e) => { e.preventDefault(); onNavigate('/patient') }}>Open Patient App</a>
        </div>
        <div className="step">
          <div className="step-num">2</div>
          <div style={{ flex: 1 }}>
            Ask 3 times: <strong>"Who is Alex's geriatrician?"</strong>. Memora detects the repetition and logs confusion.
          </div>
        </div>
        <div className="step">
          <div className="step-num">3</div>
          <div style={{ flex: 1 }}>
            Open the Caregiver Dashboard to see the newly generated Alert and the updated Memory Graph.
          </div>
          <a href="#" className="btn btn-primary" style={{ background: '#00ff88', borderColor: '#00ff88', color: '#0b0e14' }} onClick={(e) => { e.preventDefault(); onNavigate('/caregiver') }}>Open Caregiver Dashboard</a>
        </div>
      </div>

      <div className="card section">
        <h2 className="card-title">3. What is Real vs Simulated</h2>
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>LLMs & Orchestration</strong></td>
              <td><span className="badge badge-success">REAL</span></td>
              <td>Using Nebius Token Factory (Nano, Super, Ultra, Qwen embeddings). Real multi-model routing based on intent.</td>
            </tr>
            <tr>
              <td><strong>Web Search</strong></td>
              <td><span className="badge badge-success">REAL</span></td>
              <td>Tavily API used for real-time external world queries.</td>
            </tr>
            <tr>
              <td><strong>Memory Graph DB</strong></td>
              <td><span className="badge badge-success">REAL</span></td>
              <td>Turso libSQL (remote, encrypted at rest by Turso) when TURSO_DATABASE_URL is set; local SQLite fallback otherwise.</td>
            </tr>
            <tr>
              <td><strong>Patient History</strong></td>
              <td><span className="badge badge-orange">SIMULATED</span></td>
              <td>"Sarah Morgan" is a simulated person (Alex's adult daughter and primary caregiver). 7 days of past interaction logs are seeded on boot to populate the caregiver graphs.</td>
            </tr>
            <tr>
              <td><strong>Medical Data</strong></td>
              <td><span className="badge badge-orange">SIMULATED</span></td>
              <td>No real clinical data. Memora is strictly <em>not</em> a medical device.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card section">
        <h2 className="card-title">4. Architecture Diagram</h2>
        <pre className="mermaid">
{`flowchart LR
    App["Patient App (Browser)"] -->|HTTPS| API["FastAPI (Python)"]
    Dash["Caregiver Dashboard"] <-->|HTTPS| API
    API --> Nebius["Nebius Token Factory"]
    API --> Tavily["Tavily Search API"]
    API <--> DB[("Turso libSQL Memory Graph")]`}
        </pre>
        <script type="module" dangerouslySetInnerHTML={{ __html: `
          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({ startOnLoad: true, theme: 'dark' });
        `}} />
      </div>

      <div className="card section">
        <h2 className="card-title">5. LIVE Metrics (Nebius Token Factory)</h2>
        <table id="metrics-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Calls</th>
              <th>Avg Latency</th>
              <th>Last Latency</th>
              <th>Est. Cost</th>
            </tr>
          </thead>
          <tbody id="metrics-body">
            {metricsLoading ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', color: '#8794a8' }}>Loading metrics...</td></tr>
            ) : metrics && metrics.latency_by_model && Object.keys(metrics.latency_by_model).length > 0 ? (
              Object.entries(metrics.latency_by_model).map(([model, stats]: [string, any]) => (
                <tr key={model}>
                  <td style={{ fontWeight: 500 }}>{model}</td>
                  <td>{stats.calls}</td>
                  <td>{stats.avg_ms ? ((stats.avg_ms / 1000) as number).toFixed(2) + 's' : 'N/A'}</td>
                  <td>{stats.last_ms ? ((stats.last_ms / 1000) as number).toFixed(2) + 's' : 'N/A'}</td>
                  <td>See total</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={5} style={{ textAlign: 'center', color: '#8794a8' }}>not measured yet</td></tr>
            )}
            {metrics && (
              <tr style={{ backgroundColor: 'rgba(135, 224, 192, 0.1)', fontWeight: 'bold' }}>
                <td>Total Cost (Session)</td>
                <td colSpan={3}></td>
                <td>${metrics.estimated_cost_usd ? metrics.estimated_cost_usd.toFixed(6) : '0.000000'}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="judges-footer">
        <div className="badge" style={{ float: 'right' }}>
          Application-level DB encryption: {encrypted === true ? 'YES 🔒' : encrypted === false ? 'NO ⚠️' : 'Checking...'}
        </div>
      </div>
    </div>
  )
}
