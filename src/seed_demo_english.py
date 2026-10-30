#!/usr/bin/env python3
"""
Idempotent seed script for a clean English-only Memora demonstration dataset.

Creates a SEPARATE temporary SQLite database (data/memora_demo_english.db)
with the same schema as src/memory.py. Does NOT touch data/memora.db or any
backup. All content is fictional demo data in English, clearly marked demo.

Run: python src/seed_demo_english.py
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Resolve paths relative to this script's location (src/) and project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEMO_DB_PATH = os.path.join(DATA_DIR, "memora_demo_english.db")

# Ensure src package is importable (for timeutil, used only for TZ)
sys.path.insert(0, PROJECT_ROOT)
from src.timeutil import now_local  # noqa: E402

ALLOWED_NODE_TYPES = {
    "person", "place", "event", "habit", "med", "preference",
    "patologia", "routine", "caa_button", "interaction", "pending", "alert",
}

# Schema must match src/memory.py _init_db() exactly
SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT,
    content TEXT,
    timestamp REAL,
    embedding TEXT
);
ALTER TABLE nodes ADD COLUMN schedule TEXT;
ALTER TABLE nodes ADD COLUMN last_status TEXT;
ALTER TABLE nodes ADD COLUMN last_confirmation REAL;
ALTER TABLE nodes ADD COLUMN meta TEXT;
CREATE TABLE IF NOT EXISTS edges (
    source TEXT,
    target TEXT,
    relation TEXT,
    PRIMARY KEY (source, target, relation)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    kind TEXT,
    data TEXT,
    simulated INTEGER DEFAULT 0
);
"""

# ---------------------------------------------------------------------------
# Demo dataset (all fictional, all English, all marked demo: true)
# ---------------------------------------------------------------------------

DEMO_META_BASE = {"demo": True, "fictional": True}

NODES = [
    # ---- Persons ----
    {
        "id": "patient_alex",
        "type": "person",
        "content": "Alex Morgan, 72 years old, lives in Portland, Oregon. Fictional demo patient for the Memora demonstration.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Alex Morgan", "age": 72, "city": "Portland", "state": "OR", "role": "patient"},
    },
    {
        "id": "caregiver_sarah",
        "type": "person",
        "content": "Sarah Morgan, 45 years old, adult daughter and primary caregiver for Alex Morgan. Fictional demo data.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Sarah Morgan", "age": 45, "city": "Portland", "state": "OR", "role": "caregiver", "relationship": "daughter"},
    },
    {
        "id": "provider_dr_chen",
        "type": "person",
        "content": "Dr. Lisa Chen, geriatrician at Northwest Geriatric Clinic. Fictional demo healthcare provider.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Dr. Lisa Chen", "specialty": "geriatrics", "clinic": "Northwest Geriatric Clinic", "role": "provider"},
    },
    {
        "id": "pharmacist_mike",
        "type": "person",
        "content": "Mike Rodriguez, pharmacist at Riverside Community Pharmacy. Fictional demo data.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Mike Rodriguez", "role": "pharmacist", "pharmacy": "Riverside Community Pharmacy"},
    },

    # ---- Places ----
    {
        "id": "place_home",
        "type": "place",
        "content": "Alex Morgan's home in Portland, Oregon. Fictional demo residence.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Alex Morgan's Home", "city": "Portland", "state": "OR", "type": "residence"},
    },
    {
        "id": "place_pharmacy",
        "type": "place",
        "content": "Riverside Community Pharmacy, Portland, Oregon. Fictional demo pharmacy.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Riverside Community Pharmacy", "city": "Portland", "state": "OR", "type": "pharmacy"},
    },
    {
        "id": "place_clinic",
        "type": "place",
        "content": "Northwest Geriatric Clinic, Portland, Oregon. Fictional demo clinic.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "name": "Northwest Geriatric Clinic", "city": "Portland", "state": "OR", "type": "clinic"},
    },

    # ---- Medicines (FICTIONAL test data - NOT prescriptions or medical advice) ----
    {
        "id": "med_lisinopril",
        "type": "med",
        "content": "FICTIONAL TEST DATA - NOT A PRESCRIPTION: Lisinopril 10 mg, one tablet once daily in the morning. Demo data only, not medical advice.",
        "schedule": "08:00",
        "meta": {**DEMO_META_BASE, "name": "Lisinopril", "dosage": "10 mg", "frequency": "once daily", "time": "08:00"},
    },
    {
        "id": "med_atorvastatin",
        "type": "med",
        "content": "FICTIONAL TEST DATA - NOT A PRESCRIPTION: Atorvastatin 20 mg, one tablet once daily in the evening. Demo data only, not medical advice.",
        "schedule": "20:00",
        "meta": {**DEMO_META_BASE, "name": "Atorvastatin", "dosage": "20 mg", "frequency": "once daily", "time": "20:00"},
    },
    {
        "id": "med_donepezil",
        "type": "med",
        "content": "FICTIONAL TEST DATA - NOT A PRESCRIPTION: Donepezil 5 mg, one tablet once daily in the evening. Demo data only, not medical advice.",
        "schedule": "20:00",
        "meta": {**DEMO_META_BASE, "name": "Donepezil", "dosage": "5 mg", "frequency": "once daily", "time": "20:00"},
    },

    # ---- Appointments (events) ----
    {
        "id": "event_cardiology_appt",
        "type": "event",
        "content": "Cardiology follow-up appointment. Fictional demo appointment.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "kind": "appointment", "specialty": "cardiology", "location": "Northwest Geriatric Clinic"},
    },
    {
        "id": "event_memory_assessment",
        "type": "event",
        "content": "Memory assessment follow-up appointment. Fictional demo appointment.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "kind": "appointment", "specialty": "neurology", "location": "Northwest Geriatric Clinic"},
    },

    # ---- Reminders / habits ----
    {
        "id": "habit_morning_walk",
        "type": "habit",
        "content": "Morning walk around the neighborhood, 30 minutes. Fictional demo reminder.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "kind": "reminder", "time": "morning", "duration": "30 minutes"},
    },
    {
        "id": "habit_call_daughter",
        "type": "habit",
        "content": "Weekly video call with daughter Sarah Morgan. Fictional demo reminder.",
        "schedule": None,
        "meta": {**DEMO_META_BASE, "kind": "reminder", "frequency": "weekly", "contact": "Sarah Morgan"},
    },
]

EDGES = [
    # Patient <-> places
    ("patient_alex", "place_home", "lives_at"),
    ("patient_alex", "place_pharmacy", "fills_prescriptions_at"),
    ("patient_alex", "place_clinic", "receives_care_at"),
    # Patient <-> people
    ("patient_alex", "caregiver_sarah", "cared_for_by"),
    ("patient_alex", "provider_dr_chen", "sees"),
    # Patient <-> medicines
    ("patient_alex", "med_lisinopril", "takes"),
    ("patient_alex", "med_atorvastatin", "takes"),
    ("patient_alex", "med_donepezil", "takes"),
    # Provider <-> medicines
    ("provider_dr_chen", "med_lisinopril", "prescribes"),
    ("provider_dr_chen", "med_atorvastatin", "prescribes"),
    ("provider_dr_chen", "med_donepezil", "prescribes"),
    # Pharmacy <-> medicines
    ("place_pharmacy", "med_lisinopril", "stocks"),
    ("place_pharmacy", "med_atorvastatin", "stocks"),
    ("place_pharmacy", "med_donepezil", "stocks"),
    # Patient <-> habits / appointments
    ("patient_alex", "habit_morning_walk", "does"),
    ("patient_alex", "habit_call_daughter", "does"),
    ("patient_alex", "event_cardiology_appt", "has_appointment"),
    ("patient_alex", "event_memory_assessment", "has_appointment"),
]

# Simulated activity events (English labels, simulated=1, matching demo_events kinds)
# day offset (0 = today) -> {kind: count}
DEMO_EVENTS = {
    6: {"interaction": 6, "med_confirmed": 1},
    5: {"interaction": 7, "repeat_flag": 1, "med_confirmed": 1, "diary_turn": 2},
    4: {"interaction": 6, "repeat_flag": 1, "med_confirmed": 1},
    3: {"interaction": 8, "repeat_flag": 2, "med_confirmed": 1, "diary_turn": 3},
    2: {"interaction": 9, "repeat_flag": 3, "med_confirmed": 1, "confusion_flag": 1},
    1: {"interaction": 10, "repeat_flag": 4, "med_missed": 1, "confusion_flag": 1, "diary_turn": 2},
    0: {"interaction": 6, "repeat_flag": 2, "med_confirmed": 1},
}


def build_database(db_path: str) -> None:
    """Create a fresh demo SQLite database at db_path (idempotent)."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Remove existing file for a clean rebuild (idempotent)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Apply schema (columns added via ALTER TABLE; ignore "duplicate column" errors)
    for statement in SCHEMA.strip().split(";"):
        statement = statement.strip()
        if statement:
            try:
                cur.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc):
                    raise

    import time  # noqa: F401  (timestamp supplied by now_local)

    # ---- Insert nodes ----
    for node in NODES:
        nid = node["id"]
        ntype = node["type"]
        content = node["content"]
        schedule = node.get("schedule")
        meta = node.get("meta") or {}
        cur.execute(
            """
            INSERT INTO nodes (id, type, content, timestamp, embedding, schedule, last_status, last_confirmation, meta)
            VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, ?)
            """,
            (nid, ntype, content, now_local().timestamp(), schedule, json.dumps(meta)),
        )

    # ---- Insert edges ----
    for source, target, relation in EDGES:
        cur.execute(
            "INSERT OR IGNORE INTO edges (source, target, relation) VALUES (?, ?, ?)",
            (source, target, relation),
        )

    # ---- Insert simulated events ----
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(os.getenv("TZ_NAME", "Europe/Rome"))
    for days_ago, kinds in DEMO_EVENTS.items():
        event_date = (datetime.now(tz) - timedelta(days=days_ago)).timestamp()
        for kind, count in kinds.items():
            for _ in range(count):
                cur.execute(
                    "INSERT INTO events (ts, kind, data, simulated) VALUES (?, ?, ?, 1)",
                    (event_date, kind, json.dumps({"demo": True})),
                )

    conn.commit()
    conn.close()
    print(f"Created demo database at {db_path}")


def validate(db_path: str) -> list[str]:
    """Validate the demo database. Returns a list of failure messages (empty = all pass)."""
    failures: list[str] = []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. SQLite integrity
    cur.execute("PRAGMA integrity_check")
    integrity = cur.fetchone()[0]
    if integrity != "ok":
        failures.append(f"SQLite integrity check failed: {integrity}")

    # 2. Required tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    for required in ("nodes", "edges", "events"):
        if required not in tables:
            failures.append(f"Missing table: {required}")

    # 3. Node fields
    cur.execute("SELECT id, type, content, timestamp, schedule, meta FROM nodes")
    all_nodes = cur.fetchall()
    node_ids: set[str] = set()
    for row in all_nodes:
        nid, ntype, content, ts, schedule, meta_json = row
        # ID format (matches add_memory regex)
        import re
        if not re.match(r"^[A-Za-z0-9_-]{1,64}$", nid or ""):
            failures.append(f"Invalid node id: {nid!r}")
        node_ids.add(nid)
        # Type in allowed set
        if ntype not in ALLOWED_NODE_TYPES:
            failures.append(f"Disallowed node type {ntype!r} for node {nid}")
        # Content present
        if not content:
            failures.append(f"Empty content for node {nid}")
        # Timestamp present
        if ts is None:
            failures.append(f"Missing timestamp for node {nid}")
        # Meta is valid JSON and marked demo
        try:
            meta = json.loads(meta_json) if meta_json else {}
        except json.JSONDecodeError:
            failures.append(f"Invalid meta JSON for node {nid}")
            meta = {}
        if not meta.get("demo"):
            failures.append(f"Node {nid} not marked demo")

    # 4. Edge references (no orphans)
    cur.execute("SELECT source, target, relation FROM edges")
    edges = cur.fetchall()
    for source, target, relation in edges:
        if source not in node_ids:
            failures.append(f"Edge source {source!r} not found in nodes")
        if target not in node_ids:
            failures.append(f"Edge target {target!r} not found in nodes")
        if not relation:
            failures.append(f"Empty relation on edge {source} -> {target}")

    # 5. Duplicate edges
    cur.execute("SELECT source, target, relation, COUNT(*) as c FROM edges GROUP BY source, target, relation HAVING c > 1")
    dupes = cur.fetchall()
    if dupes:
        failures.append(f"Duplicate edges found: {len(dupes)}")

    # 6. Events reference valid kinds
    cur.execute("SELECT kind, simulated FROM events")
    event_kinds = cur.fetchall()
    valid_kinds = {
        "interaction", "repeat_flag", "confusion_flag", "sos",
        "med_confirmed", "med_missed", "med_denied", "med_unsure", "diary_turn",
    }
    for kind, simulated in event_kinds:
        if kind not in valid_kinds:
            failures.append(f"Unknown event kind: {kind!r}")
        if simulated != 1:
            failures.append(f"Event {kind!r} not marked simulated")

    # 7. English-language consistency: no non-ASCII in content/labels
    cur.execute("SELECT id, content FROM nodes")
    for nid, content in cur.fetchall():
        try:
            content.encode("ascii")
        except UnicodeEncodeError:
            failures.append(f"Non-ASCII content in node {nid}: {content[:60]!r}")

    # 8. Medicine nodes explicitly mention fictional/not medical advice
    cur.execute("SELECT id, content FROM nodes WHERE type = 'med'")
    med_nodes = cur.fetchall()
    if len(med_nodes) == 0:
        failures.append("No medicine nodes found")
    for nid, content in med_nodes:
        lower = content.lower()
        if "fictional" not in lower or "not medical advice" not in lower:
            failures.append(f"Medicine node {nid} missing fictional/not-medical-advice disclaimer")

    # 9. Every node type present (coverage check)
    cur.execute("SELECT DISTINCT type FROM nodes")
    present_types = {row[0] for row in cur.fetchall()}
    expected_types = {"person", "place", "event", "habit", "med"}
    missing = expected_types - present_types
    if missing:
        failures.append(f"Missing node types: {missing}")

    # 10. Event counts
    cur.execute("SELECT COUNT(*) FROM events")
    event_count = cur.fetchone()[0]

    conn.close()

    failures.append(f"--- COUNTS ---")
    failures.append(f"Nodes: {len(all_nodes)}")
    failures.append(f"Edges: {len(edges)}")
    failures.append(f"Events: {event_count}")
    failures.append(f"Node types: {sorted(present_types)}")
    return failures


def main() -> None:
    build_database(DEMO_DB_PATH)
    print("\n--- Validation ---")
    failures = validate(DEMO_DB_PATH)
    # Separate informational count lines from actual failures
    info_lines = [f for f in failures if f.startswith("---") or f.startswith(("Nodes:", "Edges:", "Events:", "Node types:"))]
    real_failures = [f for f in failures if not (f.startswith("---") or f.startswith(("Nodes:", "Edges:", "Events:", "Node types:")))]
    for line in info_lines:
        print(line)
    if real_failures:
        print(f"\nVALIDATION FAILED ({len(real_failures)} issues):")
        for f in real_failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\nAll validation checks passed.")


if __name__ == "__main__":
    main()
