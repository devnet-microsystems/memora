# Architecture Overview

This document describes the structural and functional architecture of Memora, detailing the execution flow, routing algorithms, and privacy guarantees.

## High-Level Execution Flow

```text
User 
  │ (Input string)
  ▼
[ FastAPI Server ] ────► [ Flask Dashboard ] (Caregiver monitoring view)
  │
  ▼
[ Memora Agent ]
  │
  ├──► 1. Intent Check & Redaction ──► [ NVIDIA Nemotron-3 Nano ]
  │
  ├──► 2. Memory Context Retrieval ──► [ Local MemoryGraph ] ──► (Cosine Similarity on Embeddings)
  │
  ├──► 3. Web Search (if needed)   ──► [ Tavily API ]
  │
  └──► 4. Response Generation      ──► [ NVIDIA Nemotron-3 Super ]
```

## Model Routing Algorithm
Memora leverages a multi-model architecture, dynamically delegating tasks based on the complexity required. This optimizes cost, latency, and reasoning power via the **Nebius Token Factory**:

- **NVIDIA Nemotron-3 Nano (30b):** Used exclusively for real-time classification (e.g., `quick_intent`). Its small footprint allows the agent to immediately determine if the user's message is a casual greeting, a request for help, or a sign of confusion.
- **NVIDIA Nemotron-3 Super (120b):** The core reasoning engine for dialogues. It balances speed with the deep contextual understanding required to generate empathetic responses and interpret retrieved graph memory.
- **NVIDIA Nemotron-3 Ultra:** Reserved for heavy computational and reasoning loads. It runs asynchronously (or in backend jobs) to detect behavioral anomalies in recent message histories and to compile detailed weekly reports for caregivers.

## PII Redaction Layer
Since Memora interacts with vulnerable users, it acts as a privacy shield between the user and the cloud LLMs.
The `NebiusClient` includes an internal `_redact(text)` step. Before any text is sent to the Nebius endpoints (either for chat completions or embeddings), a regex-based filter strips out:
- Phone Numbers (`[PHONE]`)
- Email Addresses (`[EMAIL]`)
- Dates of Birth (`[DOB]`)
- Fiscal Codes/IDs (`[CF REDACTED]`)

This ensures that while the LLM understands the context (e.g., "The user mentioned their phone number"), the actual sensitive sequence never leaves the local environment.

## Privacy Model (Local vs Cloud)
Memora enforces strict data sovereignty boundaries:
- **Local Persistence:** The raw `MemoryGraph` is stored entirely on the local filesystem in a SQLite database (with `SQLCipher` encryption fallback). No unredacted memories are stored in the cloud.
- **Stateless Cloud LLM:** The NVIDIA models running on Nebius are treated as stateless functional components. They receive only the specific (and redacted) context retrieved for a single query. They do not hold the user's graph.
- **Right to be Forgotten:** Through the dashboard or API, caregivers can trigger the `/memory/{node_id}` DELETE endpoint. This instantly expunges the targeted memory and its edges from the local graph, effectively making the system "forget" it forever.
