# Hackathon Devpost Notes

## Highlight: L'impatto del System Prompt (NVIDIA Nemotron Super)
Questo è il contrasto tra una chiamata libera e una disciplinata tramite il `MemoraAgent`:

| Metrica | Test 2 (no system prompt) | Test 5 (con system prompt) |
|---|---|---|
| Output token | 753 | ~10 |
| Latenza | 5.81s | 2.72s |
| Qualità percepita | 6/10 | **10/10** |
| Rispetta "una domanda per volta" | No | Sì |

*Conclusione*: Nemotron è altamente istruibile. Il valore aggiunto e la sicurezza clinica dipendono dal metaprompting.

---

## Test 1 — Nano (data: 2026-09-17)
- Modello: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
- Latenza: ~1.7s
- Costo: $0.000144
- Qualità: OK, risposta concisa e corretta (10/10 per la task di base "Rispondi solo con OK")
- Note: Nomi esatti scoperti interrogando l'API `/models` al posto dei nomi commerciali del catalog web.

## Test 2 — Super (senza system prompt)
- Modello: nvidia/nemotron-3-super-120b-a12b
- Latenza: 5.81s
- Costo: $0.001537
- Token: 31 in, 753 out
- Qualità: 6/10
- Note: risposta troppo lunga per utente con declino cognitivo.
  Causa: chiamata diretta a client.respond() senza passare da
  MemoraAgent, quindi senza system prompt restrittivo.
  Da ritestare con l'agent completo per validare il comportamento
  "frasi brevi, una domanda per volta".

## Test 3 — Embedding (data: 2026-09-17)
- Modello: Qwen/Qwen3-Embedding-8B
- Latenza: 1.36s (totale per 3 frasi, ~0.45s a frase)
- Costo: $0.0000025
- Qualità: OK. Dimensione del vettore 4096 restituita correttamente, nessun errore di formato.

## Test 4 — Agente Completo con System Prompt (data: 2026-09-17)
- Modello A (Dialogo): nvidia/nemotron-3-super-120b-a12b
- Modello B (Intent): nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
- Latenza A: 2.72s
- Latenza B: 1.40s
- Costo totale (incluse le chiamate embedding): ~$0.00076
- Token in output di A: ~10 token ("Quando le hai viste l'ultima volta?")
- Qualità A: 10/10
- Qualità B: 10/10 (Ha classificato l'intento esattamente come "SALUTO")
- Note per Devpost: **Most Valuable Feedback**. 
  Nemotron Super, senza system prompt restrittivo (Test 2), ha generato risposte lunghe e articolate (753 token in output), risultando inadatto a utenti con declino cognitivo. 
  Tuttavia, quando vincolato dall'Agent con un system prompt esplicito ("Una sola domanda per volta. Tono calmo, rassicurante, frasi brevi e semplici"), la lunghezza è crollata a una singola frase essenziale ("Quando le hai viste l'ultima volta?").
  La qualità percepita è passata da 6/10 a 10/10. Il modello ha un eccellente livello di *instruction-following* e rispetta i vincoli di sicurezza se inquadrato correttamente tramite metaprompting.
