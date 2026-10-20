# Memora - Video Script & Outline (< 3 minutes)

## Target: Nebius × NVIDIA Global AI Hackathon Submission
## Track: Personal AI
## Duration: 2:45 - 3:00 minutes

---

### 0:00-0:15 | HOOK & PROBLEM (15s)
**Visual**: Split screen - elderly person confused, caregiver worried
**Audio**: "What if your grandmother forgets her medication? What if she can't find the nearest pharmacy at night?"
**Text overlay**: "Mild Cognitive Impairment affects 15-20% of adults over 65"
**Voice**: "Memora is a private, persistent AI companion for MCI patients and their caregivers."

---

### 0:15-0:45 | LIVE DEMO - PATIENT VIEW (30s)
**Visual**: Screen recording of `/patient` route
**Actions**:
1. Type: "Where is the nearest pharmacy?"
2. Show AI response with Tavily results (real pharmacy data)
3. Tap AAC button: "💊 Medicine?" → Shows med schedule
4. Press SOS button → "Help is on the way" animation
**Voice**: "Patients chat naturally. Tavily grounds responses in live local data. AAC buttons work for aphasia. SOS is instant—no LLM delay."

---

### 0:45-1:15 | LIVE DEMO - CAREGIVER DASHBOARD (30s)
**Visual**: Screen recording of `/caregiver` route (Basic Auth)
**Actions**:
1. Show memory graph (vis.js) - nodes: patient, meds, people, places
2. Show real-time alerts panel - SOS just triggered
3. Click "Acknowledge" on SOS → patient screen updates
4. Show medication status: confirmed/missed/pending
5. Show anomaly detection: "Repeated question 3x in 1 hour"
**Voice**: "Caregivers see everything—memory graph, live alerts, medication adherence. Deterministic anomaly detection flags confusion without LLM hallucination."

---

### 1:15-1:45 | ARCHITECTURE & NEMOTRON ROUTING (30s)
**Visual**: Animated architecture diagram (from README)
**Key points**:
- FastAPI backend + Flask dashboard
- MemoryGraph: NetworkX + SQLCipher (encrypted, local)
- **Nemotron-3 Nano**: Intent classification (<1.5s)
- **Nemotron-3 Super**: Empathetic dialogue (~2.7s)
- **Nemotron-3 Ultra**: Reports & onboarding (~14s)
- Nebius Token Factory: OpenAI-compatible, tenacity retries
- Tavily: Hyper-local web search
- PII redaction BEFORE cloud calls

---

### 1:45-2:15 | PRIVACY & SECURITY (30s)
**Visual**: Bullet points + code snippets
**Features**:
1. **Right to be Forgotten**: DELETE /memory/{id} removes node + edges
2. **PII Redaction**: Phone, email, DOB, CF stripped before Nebius
3. **HITL Memory Writes**: LLM proposes → caregiver approves
4. **Untrusted Context**: Wrapped in `<reference_data>` delimiters
5. **Dashboard Auth**: Public read, Basic Auth for writes
6. **Rate Limits + Daily Budget**: DoS protection
7. **VAPID Key Rotated**: Documented in Security section

---

### 2:15-2:45 | TAIVLY INTEGRATION - BONUS TRACK (30s)
**Visual**: Code + live result
**Scenario**: "Patient asks: 'Dove è la guardia medica stasera?'"
**Code**: `tavily_tool.find_guardia_medica("Milano")`
**Result**: Real addresses, phone numbers, hours
**Voice**: "Best Use of Tavily candidate. MCI patients panic about meds/health at night. Memora grounds LLMs with live, verified local data—no hallucinated closed pharmacies."

---

### 2:45-3:00 | CLOSING & CALL TO ACTION (15s)
**Visual**: Logo + links
**Text**:
- GitHub: github.com/devnet-microsystems/memora
- Demo: memora-ht5c.onrender.com
- API Docs: memora-y2ebcg.fly.dev/docs
**Voice**: "Memora—private, persistent, privacy-first. Built for the vulnerable, not the viral. Thank you."

---

## Production Notes

### Recording Setup
- Resolution: 1920x1080 (or 1280x720)
- Frame rate: 30fps
- Audio: Clear narration, minimize background noise
- Browser: Chrome/FF with clean profile (no extensions visible)

### Screen Recording Tips
- Use OBS or built-in screen recorder
- Record each section separately, edit together
- Zoom on code/terminal for readability
- Show cursor clicks clearly

### Post-Production
- Add subtle transitions (cut, not fade)
- Lower thirds for section titles
- Background music: calm, instrumental, low volume
- Color correct for consistency

### Assets Needed
- [ ] Screen recording of `/patient` flow
- [ ] Screen recording of `/caregiver` flow
- [ ] Architecture diagram animation (can use Mermaid live editor)
- [ ] Code snippets for Nemotron routing, PII redaction, Tavily
- [ ] Final logo/title card

---

## Alternative: 60-Second "Speed Run" Version
If time-constrained:
1. 0-10s: Problem + logo
2. 10-25s: Patient chat + pharmacy result
3. 25-40s: Dashboard graph + SOS ack
4. 40-50s: Nemotron routing diagram
5. 50-55s: Privacy features (PII, delete, HITL)
6. 55-60s: Links + "Not a medical device"

---

## Judges Checklist (from `/judges` route)
- [ ] Nemotron 3-tier routing demonstrated
- [ ] Nebius Token Factory integration shown
- [ ] Persistent MemoryGraph (SQLCipher) shown
- [ ] PII redaction before cloud calls
- [ ] Tavily live search for local data
- [ ] SOS instant alert + caregiver ack
- [ ] Anomaly detection (deterministic)
- [ ] Right to be forgotten (DELETE endpoint)
- [ ] AAC accessibility buttons
- [ ] Not a diagnostic tool disclaimer visible