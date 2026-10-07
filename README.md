# Memora 🧠

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Track:** Personal AI (Nebius x NVIDIA Global AI Hackathon)

**Live demo:** [memora-ht5c.onrender.com](https://memora-ht5c.onrender.com/) (dashboard) · [API docs](https://memora-y2ebcg.fly.dev/docs)  
**Video:** _to be added before submission_

## Test in 60 seconds
1. Open `/patient`.
2. Type or say "Where is the nearest pharmacy?".
3. Open `/caregiver` to see the memory graph and logs update live.

## Description
Memora is a private, persistent personal AI assistant designed to support individuals with mild cognitive impairment (MCI) and their caregivers. It acts as an always-on companion that helps retain context, recall past events, and provide a secure bridge to external information and caregiver notifications.

## Problem & Solution
**The Problem:** People with mild cognitive impairment often experience memory lapses, confusion, and anxiety. They need a non-judgmental companion that remembers for them, while their caregivers need a way to monitor their well-being without being invasive.

**The Solution:** Memora provides a conversational interface powered by NVIDIA Nemotron models. It builds a persistent, local Knowledge Graph (MemoryGraph) of the user's life. The system prioritizes privacy by keeping raw data local and redacting Personal Identifiable Information (PII) before interacting with cloud LLMs.

## Who is Memora for
Memora is designed for two primary users:
- **Patients with Mild Cognitive Impairment (MCI)**: It acts as an always-available companion during hours of solitude, helping them remember daily tasks, answering repetitive questions without judgment, and reducing anxiety.
- **Caregivers**: It provides peace of mind by monitoring the patient's well-being, detecting anomalies or confusion, and offering a clear, analytical dashboard of the patient's cognitive status without being intrusive.

## Safety Features
Safety is our top priority. Memora includes:
- **SOS Button**: A highly visible emergency button. The alert is written instantly (no LLM, no embedding) and the patient screen only says *help is on the way* after a caregiver has actually acknowledged it; otherwise it says it is still waiting and suggests calling 112.
- **Automated Alerts**: The system detects anomalies (e.g., repeating the same question multiple times in a short window) and automatically raises red flags on the caregiver's dashboard.
- **Wearable Roadmap**: In future iterations, we plan to integrate Memora with wearable devices (like smartwatches) for fall detection, heart rate monitoring, and even more immediate SOS capabilities.

## Accessibility — AAC Support
To support patients with aphasia or severe speech difficulties, Memora integrates **Augmentative and Alternative Communication (AAC)** features. 
- **AAC Buttons**: The mobile interface includes quick-action visual buttons (e.g., "💧 I'm thirsty", "💊 Medicine?") that allow patients to communicate their needs with a single tap, bypassing the need to type or speak.

## Architecture
```text
User 
  │ (Input)
  ▼
API (FastAPI) ───────► Dashboard (Flask) -> Caregiver view
  │
  ▼
Agent (Core Logic)
  │
  ├──► MemoryGraph (Local SQLite/SQLCipher) ──► PII Redaction
  │
  ├──► Nebius Token Factory (NVIDIA Nemotron Models)
  │
  └──► TavilyTool (Web Search API)
```

## Architecture Decisions: Why a custom loop over NemoClaw/OpenShell?
While the NVIDIA ecosystem offers powerful generalized frameworks like **[NemoClaw](https://github.com/NVIDIA/nemoclaw-community)** (for always-on autonomous agents with reusable skills) and **[OpenShell](https://github.com/NVIDIA/OpenShell)** (for systemic guardrails), Memora explicitly implements a custom, highly deterministic agent loop (`src/agent.py`). 

The reasons for this deliberate choice are:
1. **Vulnerable User Base (MCI):** Mild Cognitive Impairment patients require a highly reactive, predictable, and rigidly scoped conversational partner—not an "always-on" autonomous agent that might take unpredictable actions in the background. Our custom loop enforces strict, hard-coded guardrails at the prompt and execution level (e.g., "ask only one question at a time", "never diagnose").
2. **Structural vs. General Guardrails:** Instead of relying on general-purpose guardrail layers, Memora's safety is enforced at the data architecture level. PII is redacted *before* hitting the LLMs, and the "right to be forgotten" is built directly into the persistent local `MemoryGraph`.
3. **Deterministic Anomaly Detection:** Rather than relying on autonomous reasoning to detect anomalies, Memora uses strict cosine similarity thresholds over rolling time windows to detect repetitive confusion. This ensures a 100% deterministic trigger for caregiver notifications.

## Wired Features
- **Nano → intent**: Fast routing for simple queries (e.g., greeting vs. help request).
- **Super → dialogue**: Empathetic, context-aware daily dialogue.
- **Ultra → report/onboarding**: Complex reasoning for caregiver reports and onboarding extraction.
- **Tavily routing**: Context-aware dynamic web search fallback.
- **SOS → notify**: Instant, deterministic caregiver alerts.

## Setup and Installation
### Prerequisites
- Python 3.11+
- [Nebius Token Factory API Key](https://nebius.com)
- [Tavily API Key](https://tavily.com)

### Installation
1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

### Running the Application
**Backend (FastAPI):**
```bash
python -m src.main
```
**Dashboard (Flask):**
```bash
python dashboard/app.py
```
**Nightly Job:**
```bash
python -m src.jobs.nightly
```

### Running Tests
```bash
pytest --cov=src --cov-report=term-missing
```
**Results (measured):** 65 tests passed, 75% line coverage of `src/`.

## How We Use Nebius Token Factory
Nebius provides the OpenAI-compatible runtime that powers Memora's intelligence. By setting the `base_url` to `https://api.tokenfactory.nebius.com/v1/`, Memora leverages high-performance inference endpoints securely and reliably, using `tenacity` for resilient retry logic.

## How We Use NVIDIA Nemotron Models
Memora dynamically routes tasks to different Nemotron tiers to optimize latency and reasoning:
- **Nemotron-3 Nano (30b):** Used for ultra-fast intent classification (e.g., greeting vs. help request) to minimize latency on initial user contact.
- **Nemotron-3 Super (120b):** The workhorse for daily dialogue. Generates empathetic, clear responses using the retrieved context from the MemoryGraph.
- **Nemotron-3 Ultra:** Invoked for complex reasoning tasks, such as generating weekly behavioral reports for caregivers or detecting anomalous interaction patterns (e.g., repeated questions indicating confusion).

## How We Use Tavily
Tavily is integrated as an external tool accessible via the agent. It is specifically used for context-aware, real-time web searches tailored to the user's location, such as finding the nearest open pharmacy, local emergency medical contacts (guardia medica), or caregiver support groups.
Our implementation utilizes the **Search API** (`tavily_search`) to find relevant URLs and pull detailed, clean content directly from those specific web pages when deeper context is required.

### Bonus Track: Best Use of Tavily
**We are explicitly submitting Memora for the "Best Use of Tavily" Bonus Award.**  
Mild Cognitive Impairment (MCI) patients can get easily disoriented or experience sudden panic, particularly regarding their medication or minor health issues. Memora uses Tavily to instantly ground the LLM with live, hyper-local data. For example, if a patient is confused at night, the agent transparently executes `tavily_tool.find_pharmacy("Milano")` to retrieve open pharmacies ("Farmacia S. Teresa. corso Magenta, 96. tel. +39 02 48195412" — *example output from test fixture*) without hallucinating a closed or non-existent business. This turns a generic AI into a reliable, localized emergency companion. (See `tests/test_tavily_tool.py::test_best_use_of_tavily_scenario` for the verifiable integration).

## Security

Memora deals with data that is sensitive by nature, even though the public demo uses simulated data only.
On 3 October 2026 we ran an automated white-box penetration test with Strix (deep scan). It reported 8 findings:
1 critical, 6 high, 1 medium.

| Finding | Severity | Status |
|---|---|---|
| Dashboard acted as an open proxy and injected the backend key into anonymous requests | Critical | Fixed in code: public patient routes, read-only demo routes, Basic-auth for every write (`tests/test_proxy.py`, `tests/test_dashboard_regressions.py`) |
| Stored DOM XSS from unescaped memory data | High | Fixed in code: DOM built with `textContent` / `esc()`, lint-style test (`tests/test_no_unsafe_innerhtml.py`) |
| Indirect prompt injection via memory context | High | Mitigated: untrusted context in a delimited user block, sanitized; actions are never driven by model output |
| VAPID private key committed to git | High | Key files removed. The key was exposed once and must be treated as compromised: rotate it before any real deployment |
| Vulnerable Node dependencies (braces, node-forge, uuid) | High | Belong to the optional Expo app, which is not part of this repository |
| Weak domain allow-list in a Tavily helper | Medium | Fixed: exact hostname matching (`tests/test_tavily_tool.py`) |

A full re-test with Strix after these fixes has **not** been run yet.

### Security & Known Limitations
- The public demo instance exposes simulated data read-only and accepts patient interactions from anyone (rate-limited, with a daily LLM budget cap). A production deployment would require authentication for every route.
- Automated testing is not a formal security audit.
- Browser speech recognition may send audio to the browser vendor.
- Prompt-injection mitigations reduce but cannot eliminate risk; actions are never driven by model output.
- **Not a Diagnostic Tool:** Memora is a companion app, not a medical device. It cannot and should not be used to diagnose, treat, or cure any medical condition. Not an emergency service.
- **Not Clinically Validated:** The conversational patterns and UI/UX have been designed following general best practices for cognitive accessibility, but have *not* been validated in clinical trials.
- **Simulated Data Only:** All testing, demonstrations, and graphs were generated using simulated personas (e.g., "Maria"). No real patient data has been processed by this application.
- **Heuristic Anomaly Detection:** The repetition detection is currently heuristic (based on cosine similarity of embeddings over a rolling time window) rather than using an LLM to dynamically reason over the entire behavioral graph, in order to maintain deterministic reliability and low latency.
- **Scaling Costs:** While routing simple tasks to Nemotron Nano saves money, the heavy reasoning required by Nemotron Ultra for daily/weekly caregiver reports scales linearly with usage and could become expensive at scale without further prompt optimization.

## Feedback on Nebius and NVIDIA
- **Latency**: Nano: 1.4s, Super: 2.7s, Ultra: 14s.
- **Cost**: Nano: $0.000144, Super: $0.0015, Ultra: $0.002.
- **Prompt discipline**: with no system prompt Nemotron Super answered a simple question with ~750 output tokens (5.8 s); with a strict system prompt ("max 2 sentences, one question at a time") the same question took ~10 tokens (2.7 s).
- **Issue**: Model names differ between the web catalog and the `/models` API endpoint, causing some initial friction.
- **Positives**: Excellent instruction-following capabilities when using system prompts.
- **Issue**: `Qwen3-Embedding-8B` embedding calls took 20–29 s in our tests (single call, cold). Memora therefore stores alerts without embeddings and falls back gracefully when an embedding is slow.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
