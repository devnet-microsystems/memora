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
        {"id": "luca_son", "type": "person", "content": "Luca, Maria's son, lives 20 minutes away, emergency contact."},
        {"id": "giulia_caregiver", "type": "person", "content": "Giulia, comes Tuesday and Thursday mornings to help out."},
        {"id": "dr_rossi", "type": "person", "content": "Dr. Rossi, Maria's geriatrician, office at via Roma 12."},
        {"id": "milan_home", "type": "place", "content": "Maria's home, Via Torino 5, Milan."},
        {"id": "blood_pressure_pill", "type": "med", "content": "Blood pressure pill, to be taken every morning at breakfast.", "schedule": "08:00"},
        {"id": "park_walk", "type": "habit", "content": "Daily walk to the nearby park at 10:30.", "schedule": "10:30"},
        {"id": "geriatric_visit", "type": "event", "content": "Geriatric visit with Dr. Rossi", "schedule": "TUE,THU 10:00"},
        
        # Nodi aggiuntivi richiesti
        {"id": "patient", "type": "person", "content": "Maria, 78 years old, lives in Milan, MCI mild", "meta": {"name": "Maria"}},
        {"id": "caa_thirsty", "type": "caa_button", "content": "💧 I'm thirsty"},
        {"id": "caa_medicine", "type": "caa_button", "content": "💊 Medicine?"},
        {"id": "caa_bathroom", "type": "caa_button", "content": "🚽 Bathroom"},
        {"id": "caa_call_family", "type": "caa_button", "content": "📞 Call my family"}
    ]
    
    edges = [
        {"source": "patient", "target": "luca_son", "relation": "mother_of"},
        {"source": "luca_son", "target": "patient", "relation": "primary_caregiver"},
        {"source": "patient", "target": "giulia_caregiver", "relation": "assisted_by"},
        {"source": "patient", "target": "dr_rossi", "relation": "patient_of"},
        {"source": "patient", "target": "milan_home", "relation": "lives_at"},
        {"source": "patient", "target": "blood_pressure_pill", "relation": "takes"},
        {"source": "patient", "target": "park_walk", "relation": "habit"},
        {"source": "patient", "target": "geriatric_visit", "relation": "appointment"}
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
