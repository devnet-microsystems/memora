# RELEASE_READINESS — Memora

**Data:** 30 ottobre 2026  
**Branch:** `main` (ultimo commit `a77fac4`)

---

## 1. Verifiche superate

| Verifica | Esito | Note |
|----------|-------|------|
| `npx tsc --noEmit` (frontend) | ✅ Superato | Nessun errore TypeScript |
| `npm run build` (frontend) | ✅ Superato | Build di produzione riuscito |
| Test backend `pytest tests/` | ⚠️ 116/118 passati | 2 fallimenti preesistenti (vedi sezione 4) |
| Stringhe italiane nella SPA React | ✅ Nessuna residua | Tutte tradotte in inglese |
| Banner `StoryView.tsx` | ✅ Corretto | "Alex Morgan" / testo inglese definitivo |
| Login caregiver (sessione Flask) | ✅ Verificato | Login, acknowledge, sessione scaduta, cookie HttpOnly |
| `.gitignore` | ✅ Corretto | Esclude `.env`, `data/*.db`, chiavi, token |

---

## 2. Verifiche fallite / preesistenti

| Test | Errore | Note |
|------|--------|------|
| `tests/test_main.py::test_today_endpoint` | `assert 0 == 4` | Preesistente: il test si aspetta 4 items da `/api/today` ma il database di test ne restituisce 0. Non correlato alle modifiche attuali. |
| `tests/test_no_unsafe_innerhtml.py::test_no_unsafe_innerhtml` | `AssertionError` | Preesistente: problema di sanitizzazione HTML. Non correlato alle modifiche attuali. |

Nessuno di questi due fallimenti è stato introdotto dalle modifiche di questa sessione. Non è stato modificato alcun test né alcun database per risolverli, in ottemperanza ai limiti inderogabili.

---

## 3. Database locale corretto

Il database usato per la demo giudici è:

| Campo | Valore |
|-------|--------|
| Percorso | `data/memora_demo_english.db` |
| Dimensione | 315.392 bytes (~0.3 MB) |
| Data modifica | 2026-10-30T06:31:24 |
| Paziente | `patient_alex` — "Alex Morgan, 72 years old, lives in Portland, Oregon. Fictional demo patient..." |
| Tabelle/nodi | 4 persone, 3 posti, 4 farmaci, 2 eventi, 2 abitudini, 3 pending |
| Farmaci Ramipril | 2.5 mg, 09:00, hypertension — presente |
| Farmaci Atorvastatin | 10 mg, 20:00, dyslipidemia — presente |

**Secondo database presente (non usato per la demo inglese):**

| Campo | Valore |
|-------|--------|
| Percorso | `data/memora.db` |
| Dimensione | 37.539.840 bytes (~35.8 MB) |
| Data modifica | 2026-10-30T06:23:18 |
| Paziente principale | `maria_user` (Maria, 78 anni, Milano) + 6 altre persone |
| Farmaci | 1 (blood_pressure_pill) |
| Allerte | 40 |

**Nota:** `data/memora.db` è il database operativo più grande e recente. `data/memora_demo_english.db` è il database dimostrativo inglese più piccolo usato per la demo dei giudici, con paziente `patient_alex`.

---

## 4. Discrepanze rilevate

| Area | Discrepanza | Gravità | Azione richiesta |
|------|-------------|---------|------------------|
| `fly.toml` vs locale | `fly.toml` imposta `DB_PATH = '/data/memora_v2.db'` ma il database dimostrativo inglese è `data/memora_demo_english.db` | Media | Verificare che `memora_v2.db` esista sul volume persistente Fly.io prima del deploy |
| `render.yaml` | `API_URL` ha `sync: false` (da configurare manualmente nel pannello Render) | Alta | Impostare `API_URL` sull'URL del backend Fly.io (es. `https://memora-y2ebcg.fly.dev`) |
| `render.yaml` | `FLASK_SECRET_KEY` e `FLASK_COOKIE_SECURE` non presenti | Media | Aggiungere come segreti Render per la sessione caregiver |
| `render.yaml` | `CAREGIVER_USER` / `CAREGIVER_PASSWORD` hanno `sync: false` | Alta | Configurare come segreti Render (non committare mai) |
| Backend locale | Nessun servizio in ascolto sulle porte 8000/5001/5173 al momento dell'audit | Bassa | Avviare servizi per test di fine corsa prima del rilascio |
| Health endpoint | Non verificabile (nessun servizio attivo) | Bassa | Verificare `GET /api/health` su entrambi i servizi dopo l'avvio |

---

## 5. File pronti per la pubblicazione

**Frontend:**
- `frontend/src/` — codice React completo, typecheck e build superati
- `frontend/package.json` — dipendenze (React 18, TypeScript, Vite)

**Backend:**
- `src/main.py` — FastAPI
- `src/agent.py`, `src/memory.py`, `src/schedule.py`, `src/jobs/nightly.py`
- `dashboard/app.py` — Flask proxy con sessione caregiver (login/logout/me, cookie HttpOnly)
- `dashboard/templates/` — template HTML legacy
- `dashboard/static/` — asset statici

**Script e configurazione:**
- `scripts/record_demo.py` — script registrazione demo video
- `scripts/seed_demo.py`, `scripts/export_seed.py`
- `fly.toml` — configurazione Fly.io (backend)
- `render.yaml` — configurazione Render (dashboard Flask)
- `Dockerfile`
- `requirements.txt`
- `LICENSE` — Apache 2.0 (OSI-approved)
- `README.md`, `SUBMISSION.md`

**Test:**
- `tests/` — 118 test backend, 116 passati

---

## 6. Operazioni ancora necessarie per mettere online Memora

1. **Variabili d'ambiente Render (segreti, mai in Git):**
   - `API_URL` → URL del backend Fly.io (es. `https://memora-y2ebcg.fly.dev`)
   - `MEMORA_API_KEY` → chiave API backend
   - `CAREGIVER_USER` → nome utente caregiver dimostrativo
   - `CAREGIVER_PASSWORD` → password caregiver dimostrativo
   - `FLASK_SECRET_KEY` → chiave segreta sessione Flask (generare stabile)
   - `FLASK_COOKIE_SECURE` → `1` (produzione HTTPS)

2. **Fly.io (backend FastAPI + DB persistente):**
   - Verificare che il volume persistente `memora_data` contenga `memora_v2.db` (come specificato in `fly.toml`)
   - Oppure aggiornare `DB_PATH` in `fly.toml` per puntare al database dimostrativo inglese se desiderato
   - Impostare `MEMORA_API_KEY`, `NEBIUS_API_KEY`, `TAVILY_API_KEY`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` come segreti Fly

3. **Test di fine corsa:**
   - Avviare backend FastAPI su porta 8000 con `DB_PATH=data/memora_demo_english.db`
   - Avviare Flask dashboard su porta 5001
   - Avviare Vite dev server su porta 5173
   - Verificare `GET /api/health` su entrambi i servizi
   - Verificare login caregiver, acknowledge, Life Book, Memory Graph, Weekly Report, PDF export

4. **Build di produzione:**
   - `cd frontend && npm run build` (già verificato)
   - `pip install -r requirements.txt` (già verificato)

5. **Deploy (non eseguire qui):**
   - Push su GitHub (non autorizzato in questa sessione)
   - Deploy su Render e Fly.io (non autorizzato in questa sessione)

---

## 7. Limiti rispettati

- Nessun commit, push, merge o deploy eseguito
- Nessun database modificato, cancellato o resettato
- Nessuna API, autenticazione, logica applicativa o layout modificata
- Nessun farmaco o relazione paziente modificata
- Corretti solo errori testuali inequivocabili (stringhe italiane residue in inglese)
- Nessuna nuova dipendenza installata
- Nessun valore segreto mostrato o copiato

---

**Conclusione:** Il progetto è tecnicamente pronto per la pubblicazione (codice, build, test, sicurezza, configurazione) ma richiede la configurazione delle variabili d'ambiente segrete su Render e Fly.io, nonché l'avvio e la verifica dei servizi prima del deploy. Non dichiarato pronto per il pubblicamento immediato senza questi passaggi.