import requests
import time
import json

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")
MEMORA_KEY = os.getenv("MEMORA_API_KEY", "")
HEADERS = {"X-Memora-Key": MEMORA_KEY} if MEMORA_KEY else {}

def seed():
    print("Seeding Memory Graph for Demo...")
    
    nodes = [
        {"id": "maria_utente", "type": "person", "content": "Maria, 78 anni, abita a Milano, diagnosticata con MCI lieve."},
        {"id": "luca_figlio", "type": "person", "content": "Luca, figlio di Maria, vive a 20 minuti di distanza, numero di emergenza."},
        {"id": "giulia_badante", "type": "person", "content": "Giulia, passa il martedì e giovedì mattina per dare una mano."},
        {"id": "dr_rossi", "type": "person", "content": "Dottor Rossi, geriatra di Maria, studio in via Roma 12."},
        {"id": "milano_casa", "type": "place", "content": "Casa di Maria, Via Torino 5, Milano."},
        {"id": "pillola_pressione", "type": "med", "content": "Pillola per la pressione, da prendere ogni mattina a colazione.", "schedule": "08:00"},
        {"id": "passeggiata_parco", "type": "habit", "content": "Passeggiata quotidiana al parchetto vicino casa alle 10:30.", "schedule": "10:30"},
        {"id": "visita_geriatra", "type": "event", "content": "Visita geriatrica dal Dottor Rossi", "schedule": "TUE,THU 10:00"}
    ]
    
    edges = [
        {"source": "maria_utente", "target": "luca_figlio", "relation": "madre_di"},
        {"source": "luca_figlio", "target": "maria_utente", "relation": "caregiver_primario"},
        {"source": "maria_utente", "target": "giulia_badante", "relation": "assistita_da"},
        {"source": "maria_utente", "target": "dr_rossi", "relation": "paziente_di"},
        {"source": "maria_utente", "target": "milano_casa", "relation": "abita_a"},
        {"source": "maria_utente", "target": "pillola_pressione", "relation": "assume"},
        {"source": "maria_utente", "target": "passeggiata_parco", "relation": "abitudine"},
        {"source": "maria_utente", "target": "visita_geriatra", "relation": "impegno"}
    ]

    # Add Nodes
    for node in nodes:
        resp = requests.post(f"{API_URL}/memory", json=node, headers=HEADERS)
        if resp.status_code == 200:
            print(f"Added node: {node['id']}")
        else:
            print(f"Error adding {node['id']}: {resp.text}")
        time.sleep(0.5)

    print("\nAdding edges...")

    for edge in edges:
        resp = requests.post(f"{API_URL}/memory/edge", json=edge, headers=HEADERS)
        if resp.status_code == 200:
            print(f"Added edge: {edge['source']} -> {edge['target']} ({edge['relation']})")
        else:
            print(f"Error adding edge {edge['source']}->{edge['target']}: {resp.text}")
        time.sleep(0.5)

    print("\nSimulating anomaly pattern (repeated question on medication)...")
    questions = [
        "Ho già preso la pillola per la pressione?",
        "Mi ricordi se ho preso la pillola per la pressione?",
        "Devo prendere la pillola per la pressione?"
    ]
    
    for q in questions:
        print(f"Simulated user asks: '{q}'")
        resp = requests.post(f"{API_URL}/chat", json={"user_input": q}, headers=HEADERS)
        if resp.status_code == 200:
            print("Response:", resp.json()["response"])
        else:
            print("Error:", resp.text)
        time.sleep(1)

    print("\nDone seeding!")

if __name__ == "__main__":
    seed()
