# Memora — Submission Description for Nebius × NVIDIA Global AI Hackathon

## Track: Personal AI

## One-Line Pitch
**Memora is a private, persistent AI companion for people with Mild Cognitive Impairment (MCI) and their caregivers—built on NVIDIA Nemotron models via Nebius Token Factory, with local encrypted memory, PII redaction, and Tavily-grounded local intelligence.**

---

## The Problem
Mild Cognitive Impairment affects 15–20% of adults over 65. Patients experience memory lapses, disorientation, and anxiety—especially when alone. Caregivers need visibility without intrusion. Existing assistants either hallucinate, lack persistence, or send raw personal data to the cloud.

---

## The Solution
Memora provides a **dual-interface system**:
- **Patient view** (`/patient`): Conversational chat, AAC visual buttons for aphasia, instant SOS button
- **Caregiver dashboard** (`/caregiver`): Live memory graph (vis.js), medication adherence, anomaly alerts, SOS acknowledgment

All backed by a **local, encrypted Knowledge Graph** (MemoryGraph) that never leaves the device unredacted.

---

## Technical Architecture

```
User Input
    │
    ▼
FastAPI Backend (src/main.py)
    │
    ├──► MemoraAgent (src/agent.py) — Custom deterministic loop
    │       │
    │       ├──► MemoryGraph (src/memory.py) — NetworkX + SQLCipher
    │       │       ├── Nodes: id, type, content, timestamp, embedding
    │       │       ├── Edges: typed relationships
    │       │       ├── Persistence: Encrypted SQLite (sqlcipher3)
    │       │       └── Right to be Forgotten: DELETE cascade
    │       │
    │       ├──► NebiusClient (src/nebius_client.py) — OpenAI SDK + Nebius Token Factory
    │       │       ├── Nemotron-3 Nano (30B): Intent classification
    │       │       ├── Nemotron-3 Super (120B): Daily dialogue
    │       │       ├── Nemotron-3 Ultra: Reports, onboarding, anomaly reasoning
    │       │       ├── Qwen3-Embedding-8B: Semantic search
    │       │       ├── PII Redaction: Phone, Email, DOB, Codice Fiscale
    │       │       └── Tenacity retry logic (3 attempts, exponential backoff)
    │       │
    │       └──► TavilyTool (src/tavily_tool.py) — Context-aware web search
    │               ├── find_pharmacy(location)
    │               ├── find_guardia_medica(location)
    │               └── find_support_group(type, location)
    │
    ▼
Flask Dashboard (dashboard/app.py) — Caregiver UI
    ├── /caregiver — Graph, stats, alerts, meds, pending approvals
    ├── /patient — Chat, AAC, SOS
    ├── /story — Project narrative
    └── /judges — Evaluation summary
```

---

## Why Custom Agent Loop (Not NemoClaw/OpenShell)

| Requirement | NemoClaw/OpenShell | Memora Custom Loop |
|-------------|-------------------|-------------------|
| Vulnerable users (MCI) | General autonomous agents | Rigid guardrails: one question, no diagnosis, calm tone |
| Structural privacy | Guardrail layers | PII redacted **before** cloud; SQLCipher local; HITL writes |
| Deterministic safety | LLM-based reasoning | Cosine similarity thresholds on rolling windows |
| Latency predictability | Variable skill chains | Explicit model routing (Nano/Super/Ultra) |

---

## Nemotron Model Routing (Measured Latency & Cost)

| Model | Role | Latency | Cost/1k tokens | Use Case |
|-------|------|---------|----------------|----------|
| Nemotron-3 Nano | Intent | ~1.4s | $0.000144 | Greeting vs Help vs Confusion |
| Nemotron-3 Super | Dialogue | ~2.7s | $0.0015 | Empathetic, context-aware responses |
| Nemotron-3 Ultra | Reasoning | ~14s | $0.002 | Weekly reports, onboarding extraction |

**Prompt discipline matters**: Without system prompt, Super used 750 tokens (5.8s). With strict prompt ("max 2 sentences, one question"), same query used ~10 tokens (2.7s).

---

## Nebius Token Factory Integration
- **Endpoint**: `https://api.tokenfactory.nebius.com/v1/` (OpenAI-compatible)
- **Authentication**: API key via `X-Memora-Key` header + Basic Auth for dashboard
- **Resilience**: `tenacity` with 3 retries, exponential backoff (2-10s)
- **Usage tracking**: Per-model latency, token counts, estimated cost

---

## Persistent MemoryGraph (Privacy by Design)
- **Storage**: NetworkX DiGraph + SQLCipher-encrypted SQLite
- **Schema**: Nodes (id, type, content, timestamp, embedding, schedule, meta) + Edges (source, target, relation)
- **Node types**: person, place, event, habit, med, preference, condition, caa_button, alert, flag, interaction, pending
- **Right to be Forgotten**: `DELETE /memory/{id}` removes node + all edges from graph & DB
- **HITL writes**: LLM proposes `pending` nodes → caregiver approves via dashboard
- **Untrusted context**: Wrapped in `<reference_data>` delimiters, sanitized (control chars, tags, role spoofing removed)

---

## PII Redaction (Before Cloud)
```python
# src/nebius_client.py:_redact()
text = re.sub(r'\+?\d{2,3}[\s-]?\d{3}[\s-]?\d{4,8}', '[PHONE]', text)
text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
text = re.sub(r'[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]', '[CF REDACTED]', text, flags=re.IGNORECASE)
text = re.sub(r'\b(0[1-9]|[12][0-9]|3[01])[-/.](0[1-9]|1[012])[-/.](19|20)\d\d\b', '[DOB]', text)
```
**Applied to every message and embedding request before leaving the device.**

---

## Tavily Integration — Best Use of Tavily Candidate
**Scenario**: MCI patient confused at night: *"Dove è la farmacia aperta?"* / *"Guardia medica stasera?"*

**Implementation**:
```python
# src/agent.py:_route_tools()
if "farmacia" in user_input:
    results = self.tavily.find_pharmacy(home_location)  # Real-time, verified
elif "guardia medica" in user_input:
    results = self.tavily.find_guardia_medica(home_location)
```

**Result**: Live, hyper-local data (name, address, phone, hours) — no hallucinated closed businesses. Test fixture returns: *"Farmacia S. Teresa, corso Magenta 96, tel. +39 02 48195412"*

---

## Safety Features
1. **Instant SOS**: Written directly as `alert` node (skip_embedding=True) — appears in <100ms, no LLM
2. **Caregiver Acknowledgment**: Patient sees "waiting..." until caregiver clicks "Acknowledge" → then "help is on the way"
3. **Anomaly Detection**: Cosine similarity ≥0.85 over 1-hour window → deterministic flag + caregiver notification
4. **Medication Escalation**: Missed/unsure/denied → caregiver notified (once per day per med)
5. **Rate Limits**: Chat 20/min, SOS 5/min, Diary 20/min + Daily LLM budget (500 calls)
6. **Security Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`

---

## Security Audit (Strix — 3 Oct 2026)
| Finding | Severity | Status |
|---------|----------|--------|
| Dashboard open proxy + key injection | Critical | **Fixed** — public patient routes, read-only demo, Basic Auth for writes |
| Stored DOM XSS | High | **Fixed** — `textContent`/`esc()`, lint test `test_no_unsafe_innerhtml.py` |
| Indirect prompt injection | High | **Mitigated** — delimited context, sanitized, actions never from model output |
| VAPID private key in git | High | **Rotated** — key files removed, documented as compromised |
| Vulnerable Node deps | High | **N/A** — Expo app not in this repo |
| Weak Tavily domain allow-list | Medium | **Fixed** — exact hostname matching, test in `test_tavily_tool.py` |

**Re-test after fixes: Not yet run.**

---

## Test Results (Local Verification)
```
$ pytest --cov=src --cov-report=term-missing
========================= 67 passed, 2 warnings in 6.19s =========================
Coverage: 75% (src/), 87% (agent), 84% (memory), 66% (nebius_client)
```

All tests mocked — no real API calls required. Tests cover:
- PII redaction patterns
- Nebius client retry/stream/usage
- MemoryGraph CRUD, search, delete, seed load
- Agent intent, dialogue, anomaly, onboarding, diary
- Dashboard proxy, auth, rate limits, security headers
- Schedule/medication logic
- Tavily hostname validation

---

## Known Limitations (Honest Assessment)
- **Not a medical device** — cannot diagnose, treat, or replace emergency services
- **Not clinically validated** — UI/UX follows cognitive accessibility best practices only
- **Simulated data only** — demo uses persona "Maria"; no real patient data processed
- **Heuristic anomaly detection** — cosine similarity on embeddings, not LLM reasoning (by design for determinism)
- **Qwen3-Embedding-8B latency** — 20-29s cold; alerts stored without embeddings, graceful fallback
- **Scaling costs** — Ultra model for reports scales linearly; prompt optimization needed for production
- **VAPID key compromised** — must rotate before any real deployment

---

## Deployment
- **Backend**: Fly.io (`memora-y2ebcg.fly.dev/docs`) — FastAPI + Uvicorn
- **Dashboard**: Render (`memora-ht5c.onrender.com`) — Flask + Gunicorn
- **Nightly Job**: `python -m src.jobs.nightly` — report generation, cleanup

---

## Repository
**GitHub**: https://github.com/devnet-microsystems/memora

**License**: Apache 2.0

---

## Team
- **Backend Engineer**: FastAPI, Nebius Token Factory, Nemotron routing
- **Memory Architect**: NetworkX, SQLCipher, embeddings, privacy
- **Frontend Developer**: Flask, Bootstrap 5, vis.js, caregiver UX
- **QA Tester**: pytest, 67 tests, 75% coverage, mocked integrations

---

## Demo Script
Run locally without API keys:
```bash
python demo.py
```
Demonstrates: memory persistence, PII redaction, SOS flow, medication confirmation, agent routing, security features, dashboard routes.

---

## Video
**Duration**: <3 minutes  
**Script**: `video_script.md` — covers patient view, caregiver dashboard, architecture, privacy, Tavily bonus track.

---

## Contact
For questions about this submission, please open an issue on GitHub or contact the team via the repository.