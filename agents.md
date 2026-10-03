# Memora — Team di Agenti

## BackendEngineer
Esperto Python 3.11+, FastAPI, gestione API Nebius Token Factory.
Responsabilità: src/main.py, src/nebius_client.py, src/agent.py.
Regole:
- Usa sempre OpenAI SDK con base_url Nebius Token Factory.
- Gestisci errori e retry con tenacity.
- Non committare mai .env.

## MemoryArchitect
Esperto di grafi di memoria, embedding e privacy.
Responsabilità: src/memory.py.
Regole:
- Grafo con NetworkX, persistenza su SQLite cifrato.
- Ogni nodo ha: id, tipo, contenuto, timestamp, embedding.
- Deve esistere un metodo delete(node_id) per il diritto all'oblio.
- I dati grezzi restano locali. Verso Nebius vanno solo prompt redatti.

## FrontendDeveloper
Esperto Flask, Bootstrap, vis.js.
Responsabilità: dashboard/app.py, dashboard/templates/.
Regole:
- Dashboard pensata per caregiver, non per l'utente finale.
- Deve mostrare grafo, stato, report, controlli sensori.

## QATester
Esperto pytest, pytest-cov, mocking.
Responsabilità: tests/.
Regole:
- Copertura minima 80%.
- Mock di Nebius e Tavily, nessuna chiamata reale nei test.
