# Memora 🧠

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Track:** Personal AI (Nebius x NVIDIA Global AI Hackathon)

## Description
Memora is a private, persistent personal AI assistant designed to support individuals with mild cognitive impairment (MCI) and their caregivers. It acts as an always-on companion that helps retain context, recall past events, and provide a secure bridge to external information and caregiver notifications.

## Problem & Solution
**The Problem:** People with mild cognitive impairment often experience memory lapses, confusion, and anxiety. They need a non-judgmental companion that remembers for them, while their caregivers need a way to monitor their well-being without being invasive.

**The Solution:** Memora provides a conversational interface powered by NVIDIA Nemotron models. It builds a persistent, local Knowledge Graph (MemoryGraph) of the user's life. The system prioritizes privacy by keeping raw data local and redacting Personal Identifiable Information (PII) before interacting with cloud LLMs.

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

## How We Use Nebius Token Factory
Nebius provides the OpenAI-compatible runtime that powers Memora's intelligence. By setting the `base_url` to `https://api.tokenfactory.nebius.com/v1/`, Memora leverages high-performance inference endpoints securely and reliably, using `tenacity` for resilient retry logic.

## How We Use NVIDIA Nemotron Models
Memora dynamically routes tasks to different Nemotron tiers to optimize latency and reasoning:
- **Nemotron-3 Nano (30b):** Used for ultra-fast intent classification (e.g., greeting vs. help request) to minimize latency on initial user contact.
- **Nemotron-3 Super (120b):** The workhorse for daily dialogue. Generates empathetic, clear responses using the retrieved context from the MemoryGraph.
- **Nemotron-3 Ultra:** Invoked for complex reasoning tasks, such as generating weekly behavioral reports for caregivers or detecting anomalous interaction patterns (e.g., repeated questions indicating confusion).

## How We Use Tavily
Tavily is integrated as an external tool accessible via the agent. It is specifically used for context-aware, real-time web searches tailored to the user's location, such as finding the nearest open pharmacy, local emergency medical contacts (guardia medica), or caregiver support groups.

## Feedback on Nebius and NVIDIA
- **Latency**: Nano: 1.4s, Super: 2.7s, Ultra: 14s
- **Cost**: Nano: $0.000144, Super: $0.0015, Ultra: $0.002
- **Issue**: Model names differ between the web catalog and the `/models` endpoint.
- **Positives**: Excellent instruction-following capabilities when using system prompts.
- **Missing Feature**: Dedicated endpoint for embeddings.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
