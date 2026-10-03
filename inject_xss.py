import sqlite3
import json
conn = sqlite3.connect('/workspace/NvidiaHackaton/data/memora.db')
cursor = conn.cursor()
cursor.execute("INSERT INTO nodes (id, type, content, schedule) VALUES (?, ?, ?, ?)", 
    ('med_xss', 'med', '<img src=x onerror=alert(1)>', '10:00'))

meta_data = json.dumps({"source": "diary", "event_date": "2024-01-01"})
cursor.execute("INSERT INTO nodes (id, type, content, meta) VALUES (?, ?, ?, ?)", 
    ('timeline_xss', 'event', '<img src=x onerror=alert(2)>', meta_data))

conn.commit()
conn.close()
print("Injected XSS payloads into DB.")
