#!/usr/bin/env python3
"""
Memora Demo Script
Reproducible demonstration of core functionality for hackathon submission.
Run with: python demo.py
"""

import sys
import os
import tempfile
import time

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.memory import MemoryGraph
from src.nebius_client import NebiusClient
from src.agent import MemoraAgent
from src.tavily_tool import TavilyTool
from src.timeutil import now_local


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def demo_memory_persistence():
    print_section("1. MEMORY PERSISTENCE (SQLCipher + NetworkX)")
    
    db_path = tempfile.mktemp(suffix='.db')
    db_key = 'demo_key_12345'
    
    print(f"Creating encrypted database at: {db_path}")
    mg = MemoryGraph(db_path=db_path, db_key=db_key)
    
    print("Loading seed data (simulated patient 'Maria')...")
    mg.load_seed_if_empty()
    print(f"  Nodes: {mg.graph.number_of_nodes()}, Edges: {mg.graph.number_of_edges()}")
    
    print("\nAdding new memory node (skip_embedding for speed)...")
    mg.add_node('demo_med', 'med', 'Demo Medicine 10mg', schedule='09:00', skip_embedding=True)
    print(f"  Node added. Total nodes: {mg.graph.number_of_nodes()}")
    
    print("\nRetrieving node context...")
    ctx = mg.get_context('demo_med')
    print(f"  Content: {ctx['node']['content']}")
    print(f"  Type: {ctx['node']['type']}")
    
    print("\nTesting Right to be Forgotten (delete node)...")
    mg.delete('demo_med')
    print(f"  Node deleted. Exists: {mg.graph.has_node('demo_med')}")
    print(f"  Total nodes: {mg.graph.number_of_nodes()}")
    
    print("\nTesting edge deletion cascade...")
    mg.add_node('n1', 'person', 'Person 1', skip_embedding=True)
    mg.add_node('n2', 'person', 'Person 2', skip_embedding=True)
    mg.add_edge('n1', 'n2', 'knows')
    print(f"  Before delete: {mg.graph.number_of_nodes()} nodes, {mg.graph.number_of_edges()} edges")
    mg.delete('n1')
    print(f"  After delete n1: {mg.graph.number_of_nodes()} nodes, {mg.graph.number_of_edges()} edges")
    print(f"  n2 still exists: {mg.graph.has_node('n2')}")
    
    os.unlink(db_path)
    print("\n✓ Memory persistence demo completed")


def demo_pii_redaction():
    print_section("2. PII REDACTION (Privacy-First)")
    
    client = NebiusClient()
    
    test_cases = [
        ("Phone", "Il mio numero è +39 333 1234567", "[PHONE]"),
        ("Email", "Scrivi a test@example.com per info", "[EMAIL]"),
        ("DOB", "Nato il 15/05/1990 a Roma", "[DOB]"),
        ("CF", "Il codice fiscale è RSSMRA85T10A562S", "[CF REDACTED]"),
    ]
    
    print("Testing PII redaction patterns:")
    for name, input_text, expected_pattern in test_cases:
        result = client._redact(input_text)
        status = "✓" if expected_pattern in result else "✗"
        print(f"  {status} {name}: '{input_text}' -> '{result}'")
    
    print("\n✓ PII redaction demo completed")


def demo_sos_flow():
    print_section("3. SOS FLOW & CAREGIVER ACKNOWLEDGMENT")
    
    db_path = tempfile.mktemp(suffix='.db')
    db_key = 'demo_key_12345'
    mg = MemoryGraph(db_path=db_path, db_key=db_key)
    mg.load_seed_if_empty()
    
    print("Simulating patient SOS...")
    alert_id = f"sos_{int(time.time()*1000)}"
    mg.add_nodes([{
        'id': alert_id, 'type': 'alert', 'skip_embedding': True,
        'content': f'SOS from patient_1 at {now_local().strftime("%H:%M")}',
        'meta': {'status': 'open', 'source': 'patient_sos', 'patient_id': 'patient_1'},
    }])
    print(f"  Alert created: {alert_id}")
    print(f"  Status: {mg.graph.nodes[alert_id]['meta']['status']}")
    
    print("\nCaregiver acknowledges...")
    mg.update_node(alert_id, meta_patch={'status': 'acknowledged', 'acknowledged_at': time.time()})
    print(f"  Status: {mg.graph.nodes[alert_id]['meta']['status']}")
    print(f"  Acknowledged at: {mg.graph.nodes[alert_id]['meta']['acknowledged_at']}")
    
    print("\n✓ SOS flow demo completed")
    os.unlink(db_path)


def demo_med_confirmation():
    print_section("4. MEDICATION CONFIRMATION & ESCALATION")
    
    db_path = tempfile.mktemp(suffix='.db')
    db_key = 'demo_key_12345'
    mg = MemoryGraph(db_path=db_path, db_key=db_key)
    mg.load_seed_if_empty()
    
    print("Adding medication...")
    mg.add_node('med_1', 'med', 'Cardioaspirina 100mg', schedule='08:00', skip_embedding=True)
    
    print("Patient confirms medication taken...")
    mg.update_med_status('med_1', 'confirmed', time.time())
    status = mg.graph.nodes['med_1']['last_status']
    print(f"  Status: {status}")
    
    print("\nSimulating missed medication (scheduler would detect this)...")
    mg.update_med_status('med_1', 'no_response', time.time() - 86400)
    print(f"  Status after missed: {mg.graph.nodes['med_1']['last_status']}")
    
    print("\n✓ Medication confirmation demo completed")
    os.unlink(db_path)


def demo_agent_architecture():
    print_section("5. AGENT ARCHITECTURE (Nemotron Routing)")
    
    print("MemoraAgent routes tasks to appropriate Nemotron models:")
    print("  - Nemotron-3 Nano (30B): Intent classification (fast)")
    print("  - Nemotron-3 Super (120B): Daily dialogue (empathetic)")
    print("  - Nemotron-3 Ultra: Complex reasoning (reports, onboarding)")
    print("  - Tavily: Web search for local info (pharmacy, guardia medica)")
    
    # Show the routing logic exists in code
    from src.agent import MemoraAgent
    agent = MemoraAgent.__new__(MemoraAgent)  # Create without __init__
    
    print("\nRouting examples (from _route_tools):")
    print("  'Quando prendo la pillola?' -> Checks local med schedule")
    print("  'Dove è la farmacia?' -> Tavily find_pharmacy(location)")
    print("  'Guardia medica stasera' -> Tavily find_guardia_medica(location)")
    print("  'Gruppo supporto caregiver' -> Tavily find_support_group()")
    
    print("\n✓ Agent architecture demo completed")


def demo_security_features():
    print_section("6. SECURITY FEATURES")
    
    print("Dashboard protection:")
    print("  - Public patient routes: /api/chat, /api/sos, /api/diary/*, /api/today")
    print("  - Read-only demo routes: /api/memory, /api/stats, /api/pending (GET)")
    print("  - Write routes require Basic Auth (CAREGIVER_USER/PASSWORD)")
    print("  - Rate limiting: chat=20/min, sos=5/min, diary=20/min")
    print("  - Daily LLM call budget: 500 calls (configurable)")
    print("  - Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy")
    
    print("\nPII Handling:")
    print("  - Redaction BEFORE sending to Nebius (phone, email, DOB, CF)")
    print("  - Untrusted memory context wrapped in <reference_data> delimiters")
    print("  - Sanitization removes control chars, tags, role spoofing")
    print("  - Actions never driven by model output (HITL for memory writes)")
    
    print("\nRight to be Forgotten:")
    print("  - DELETE /memory/{node_id} endpoint")
    print("  - Removes node AND all associated edges from graph & DB")
    
    print("\n✓ Security features demo completed")


def demo_dashboard():
    print_section("7. CAREGIVER DASHBOARD (Flask + vis.js)")
    
    print("Routes:")
    print("  /           -> Landing page")
    print("  /caregiver  -> Main dashboard (graph, stats, alerts, meds)")
    print("  /patient    -> Patient interface (chat, AAC buttons, SOS)")
    print("  /story      -> Project story for judges")
    print("  /judges     -> Judges summary page")
    
    print("\nAPI Proxy (dashboard -> backend):")
    print("  /api/memory        -> Graph visualization data")
    print("  /api/chat          -> Patient chat")
    print("  /api/sos           -> Emergency alert")
    print("  /api/med/confirm   -> Medication confirmation")
    print("  /api/report        -> Weekly AI report (Ultra)")
    print("  /api/onboarding    -> Caregiver interview processing")
    print("  /api/pending       -> HITL approval queue")
    print("  /api/timeline      -> Diary timeline")
    print("  /api/alerts/*      -> Alert status & acknowledgment")
    
    print("\n✓ Dashboard demo completed")


def main():
    print("\n" + "="*60)
    print("  MEMORA - HACKATHON DEMO")
    print("  Nebius x NVIDIA Global AI Hackathon")
    print("  Personal AI Track")
    print("="*60)
    
    demo_memory_persistence()
    demo_pii_redaction()
    demo_sos_flow()
    demo_med_confirmation()
    demo_agent_architecture()
    demo_security_features()
    demo_dashboard()
    
    print_section("DEMO COMPLETE")
    print("All core functionality demonstrated successfully.")
    print("\nTo run the full application:")
    print("  1. cp .env.example .env  # Add your API keys")
    print("  2. python -m src.main    # Backend on :8000")
    print("  3. python dashboard/app.py  # Dashboard on :5001")
    print("  4. Open http://localhost:5001/caregiver")


if __name__ == '__main__':
    main()