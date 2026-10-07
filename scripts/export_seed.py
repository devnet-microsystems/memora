import json
import os
import sys

# Aggiungi il percorso root per l'import di src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nebius_client import NebiusClient
from src.demo_events import demo_events

def export_seed():
    print("Generating embeddings for demo seed data...")
    client = NebiusClient()
    
    nodes = [
        {"id": "luca_figlio", "type": "person", "content": "Luca, figlio di Maria, vive a 20 minuti di distanza, numero di emergenza."},
        {"id": "giulia_badante", "type": "person", "content": "Giulia, passa il martedì e giovedì mattina per dare una mano."},
        {"id": "dr_rossi", "type": "person", "content": "Dottor Rossi, geriatra di Maria, studio in via Roma 12."},
        {"id": "milano_casa", "type": "place", "content": "Casa di Maria, Via Torino 5, Milano."},
        {"id": "pillola_pressione", "type": "med", "content": "Pillola per la pressione, da prendere ogni mattina a colazione.", "schedule": "08:00"},
        {"id": "passeggiata_parco", "type": "habit", "content": "Passeggiata quotidiana al parchetto vicino casa alle 10:30.", "schedule": "10:30"},
        {"id": "visita_geriatra", "type": "event", "content": "Visita geriatrica dal Dottor Rossi", "schedule": "TUE,THU 10:00"},
        
        # Nodi aggiuntivi richiesti
        {"id": "patient", "type": "person", "content": "Maria, 78 anni, vive a Milano, MCI lieve", "meta": {"name": "Maria"}},
        {"id": "caa_thirsty", "type": "caa_button", "content": "💧 I'm thirsty"},
        {"id": "caa_medicine", "type": "caa_button", "content": "💊 Medicine?"},
        {"id": "caa_bathroom", "type": "caa_button", "content": "🚽 Bathroom"},
        {"id": "caa_call_family", "type": "caa_button", "content": "📞 Call my family"}
    ]
    
    edges = [
        {"source": "patient", "target": "luca_figlio", "relation": "madre_di"},
        {"source": "luca_figlio", "target": "patient", "relation": "caregiver_primario"},
        {"source": "patient", "target": "giulia_badante", "relation": "assistita_da"},
        {"source": "patient", "target": "dr_rossi", "relation": "paziente_di"},
        {"source": "patient", "target": "milano_casa", "relation": "abita_a"},
        {"source": "patient", "target": "pillola_pressione", "relation": "assume"},
        {"source": "patient", "target": "passeggiata_parco", "relation": "abitudine"},
        {"source": "patient", "target": "visita_geriatra", "relation": "impegno"}
    ]
    
    for n in nodes:
        print(f"Embedding {n['id']}...")
        n['embedding'] = client.embed(n['content'])
        
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'seed_demo.json')
    
    events = demo_events()

    with open(out_file, 'w') as f:
        json.dump({"nodes": nodes, "edges": edges, "events": events}, f, indent=2)
        
    print(f"Seed data exported to {out_file}")

if __name__ == "__main__":
    export_seed()
