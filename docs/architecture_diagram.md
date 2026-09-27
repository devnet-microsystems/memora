# Memora Architecture Diagram

This diagram provides a high-level overview of Memora's data flow, illustrating how a patient's voice input is orchestrated through the custom agent loop, dynamically routed to appropriate Nemotron models, anchored with real-world data via Tavily, and finally persisted in the local Memory Graph for caregiver visualization.

```mermaid
graph TD
    %% Styling
    classDef input fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef agent fill:#f5f5f5,stroke:#424242,stroke-width:2px,color:#000;
    classDef model fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef db fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000;
    classDef dash fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;
    classDef ext fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#000;

    %% Nodes
    Patient("🎙️ Patient Voice Input"):::input
    Agent{"⚙️ src/agent.py<br>(Core Orchestrator)"}:::agent
    
    Nano["🤖 Nemotron Nano<br>(Fast Intent Routing)"]:::model
    Super["🤖 Nemotron Super<br>(Empathetic Dialogue)"]:::model
    Ultra["🤖 Nemotron Ultra<br>(Async Deep Reports)"]:::model
    
    Tavily("🌐 Tavily Search API<br>(Live Hyper-Local Data)"):::ext
    Memory[("🧠 src/memory.py<br>(Local Knowledge Graph)")]:::db
    
    Caregiver("📊 Caregiver Dashboard<br>(Live Graph & Red Flags)"):::dash

    %% Flows
    Patient -->|1. User Speaks| Agent
    
    Agent -->|2. Route Intent| Nano
    Agent -->|3. Route Conversation| Super
    Agent -->|4. Request Reports| Ultra
    
    Super -->|Injects live context| Tavily
    
    Agent <-->|Fetches past context<br>& Detects repetitive anomalies| Memory
    
    Memory -->|Auto-syncs live updates| Caregiver
    Ultra -.->|Outputs weekly summaries| Caregiver
```

### Key Highlights
1. **Dynamic Routing:** `agent.py` acts as a strict deterministic router, ensuring the fast, cheap `Nano` model is used for intents, while `Super` handles the core chat.
2. **Grounding:** Before the LLM answers, context is retrieved simultaneously from the local `Memory Graph` (past habits) and `Tavily` (live world data like open pharmacies).
3. **Safety & Monitoring:** Anomalies (e.g., asking the same question 3 times) are detected mathematically during the graph interaction, triggering a Red Flag node directly on the `Caregiver Dashboard`.
