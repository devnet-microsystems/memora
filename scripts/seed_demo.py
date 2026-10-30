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
        {"id": "maria_user", "type": "person", "content": "Maria, 78 years old, lives in Milan, diagnosed with mild cognitive impairment."},
        {"id": "luca_son", "type": "person", "content": "Luca, Maria's son, lives 20 minutes away, emergency contact."},
        {"id": "giulia_caregiver", "type": "person", "content": "Giulia, comes Tuesday and Thursday mornings to help out."},
        {"id": "dr_rossi", "type": "person", "content": "Dr. Rossi, Maria's geriatrician, office at via Roma 12."},
        {"id": "milan_home", "type": "place", "content": "Maria's home, Via Torino 5, Milan."},
        {"id": "blood_pressure_pill", "type": "med", "content": "Blood pressure pill, to be taken every morning at breakfast.", "schedule": "08:00"},
        {"id": "park_walk", "type": "habit", "content": "Daily walk to the nearby park at 10:30.", "schedule": "10:30"},
        {"id": "geriatric_visit", "type": "event", "content": "Geriatric visit with Dr. Rossi", "schedule": "TUE,THU 10:00"}
    ]
    
    edges = [
        {"source": "maria_user", "target": "luca_son", "relation": "mother_of"},
        {"source": "luca_son", "target": "maria_user", "relation": "primary_caregiver"},
        {"source": "maria_user", "target": "giulia_caregiver", "relation": "assisted_by"},
        {"source": "maria_user", "target": "dr_rossi", "relation": "patient_of"},
        {"source": "maria_user", "target": "milan_home", "relation": "lives_at"},
        {"source": "maria_user", "target": "blood_pressure_pill", "relation": "takes"},
        {"source": "maria_user", "target": "park_walk", "relation": "habit"},
        {"source": "maria_user", "target": "geriatric_visit", "relation": "appointment"}
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
        "Did I already take the blood pressure pill?",
        "Remind me if I took the blood pressure pill?",
        "Do I need to take the blood pressure pill?"
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
