# Devpost Feedback Notes: Nebius & Tavily

This document contains specific, technical feedback gathered during the development of Memora for the NVIDIA Global AI Hackathon. These notes are intended to be included in the Devpost submission to provide value to the API providers.

## 1. Feedback for Nebius (Token Factory) & NVIDIA Nemotron

### What Worked Perfectly: Dynamic Routing & OpenAI Compatibility
The OpenAI-compatible layer of Token Factory was flawless. We were able to implement a dynamic model routing architecture in `src/nebius_client.py` without installing custom SDKs. 
- **Nemotron-3 Nano** proved exceptionally fast (1.4s latency) for zero-shot intent classification (`quick_intent`).
- **Nemotron-3 Super** served as an incredibly reliable conversational backbone. Its instruction-following capabilities are top-tier: it perfectly respected strict system prompts like *"NON dare MAI consigli medici"* (NEVER give medical advice) and *"Fai UNA SOLA domanda per volta"* (Ask ONLY one question at a time), which is notoriously difficult for mid-sized LLMs when context gets long.

### Areas for Improvement / Friction Points:
- **Model Name Discrepancies:** There is a mismatch between the human-readable model names listed in the Nebius web catalog and the actual string identifiers required to call them via the API. Developers must query the `/models` endpoint directly to discover the exact string to pass to the `model` parameter, which slows down initial onboarding.
- **Embeddings Latency:** The embeddings endpoint works using Qwen/Qwen3-Embedding-8B, but latency was the issue for real-time interactions. Since Memora relies heavily on cosine similarity for heuristic anomaly detection over the Knowledge Graph, we had to optimize our architecture to cache embeddings aggressively.

---

## 2. Feedback for Tavily (Web Search API)

### What Worked Perfectly: Context Injection Format
Once authenticated, the `tavily-python` SDK is incredibly ergonomic. The payload structure (`results` containing `title`, `url`, and `content`) is perfectly sized and formatted for direct injection into an LLM's context window. We used it to search for local pharmacies (e.g., `"farmacia di turno vicino a Milano Centrale"`), and the snippets returned contained exactly the dense information (addresses, phone numbers) Nemotron needed to assist the patient, without bloating the prompt.

### Areas for Improvement / Friction Points:
- **Ambiguous 403 Errors:** During development, we encountered persistent `403 Forbidden` errors when calling the API, even though our API key was correctly formatted (starting with `tvly-`). It was unclear whether the 403 was due to an unverified email, exhausted free-tier credits, or a temporary system outage. 
- **Documentation Clarity:** The documentation lacks a clear troubleshooting section differentiating between `401 Unauthorized` (bad key), `403 Forbidden` (feature/plan restricted), and `429 Too Many Requests` (rate limited). Improving the API error messages (e.g., `{"error": "403: Free tier credit limit reached"}`) rather than a generic HTTP 403 would significantly speed up developer debugging during high-pressure hackathons.
