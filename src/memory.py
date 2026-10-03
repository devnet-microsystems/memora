"""
Persistent Memory Module for Memora.
Handles local storage and retrieval of user data using NetworkX and SQLite.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
import networkx as nx
import numpy as np
import threading

logger = logging.getLogger("memora.memory")

try:
    from sqlcipher3 import dbapi2 as sqlite
    HAS_SQLCIPHER = True
    logger.info("SQLCipher import: True")
except ImportError:
    import sqlite3 as sqlite
    HAS_SQLCIPHER = False
    logger.warning("SQLCipher not found, falling back to standard sqlite3.")

from dotenv import load_dotenv
from src.nebius_client import NebiusClient

# Load environment variables
load_dotenv()


class MemoryGraph:
    """Graph-based persistent memory for Memora."""

    def __init__(self, db_path: Optional[str] = None, db_key: Optional[str] = None):
        """
        Initialize the Memory Graph and SQLite persistence.
        """
        self.db_path = db_path or os.getenv("DB_PATH", "./data/memora.db")
        self.db_path = os.path.abspath(self.db_path)
        self.db_key = db_key or os.getenv("DB_KEY", "")
        self.client = NebiusClient()
        self.graph = nx.DiGraph()
        self.lock = threading.Lock()
        
        # Logging moved to module level
            
        self._init_db()
        self._load_graph()

    def _get_connection(self):
        """Get a configured SQLite/SQLCipher connection."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite.connect(self.db_path)
        if HAS_SQLCIPHER and self.db_key:
            # Escape single quotes in key to prevent SQL injection in PRAGMA
            safe_key = self.db_key.replace("'", "''")
            conn.execute(f"PRAGMA key='{safe_key}'")
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 256000") # Upgraded for modern security standards
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    content TEXT,
                    timestamp REAL,
                    embedding TEXT
                )
            ''')
            try:
                cursor.execute("ALTER TABLE nodes ADD COLUMN schedule TEXT")
            except sqlite.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE nodes ADD COLUMN last_status TEXT")
            except sqlite.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE nodes ADD COLUMN last_confirmation REAL")
            except sqlite.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE nodes ADD COLUMN meta TEXT")
            except sqlite.OperationalError:
                pass
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    relation TEXT,
                    PRIMARY KEY (source, target, relation)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL,
                    kind TEXT,
                    data TEXT,
                    simulated INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

    def _load_graph(self) -> None:
        """Load the graph from SQLite into memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Load nodes
            cursor.execute("SELECT id, type, content, timestamp, embedding, schedule, last_status, last_confirmation, meta FROM nodes")
            for row in cursor.fetchall():
                node_id, n_type, content, ts, emb_json, schedule, last_status, last_confirmation, meta_json = row
                embedding = json.loads(emb_json) if emb_json else None
                meta = json.loads(meta_json) if meta_json else {}
                self.graph.add_node(
                    node_id, 
                    type=n_type, 
                    content=content, 
                    timestamp=ts, 
                    embedding=embedding,
                    schedule=schedule,
                    last_status=last_status,
                    last_confirmation=last_confirmation,
                    meta=meta
                )
                
            # Load edges
            cursor.execute("SELECT source, target, relation FROM edges")
            for row in cursor.fetchall():
                source, target, relation = row
                self.graph.add_edge(source, target, relation=relation)

    def load_seed_if_empty(self, path: str = "data/seed_demo.json") -> None:
        """
        Load nodes and edges from JSON directly into SQLite and graph if graph is empty
        (has no nodes other than 'interaction').
        """
        with self.lock:
            non_interaction_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') != 'interaction']
            if len(non_interaction_nodes) > 0:
                logger.info("Graph is not empty, skipping seed load.")
                return

            try:
                if not os.path.exists(path):
                    logger.warning(f"Seed file {path} not found.")
                    return

                with open(path, 'r') as f:
                    data = json.load(f)

                nodes = data.get("nodes", [])
                edges = data.get("edges", [])
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for node in nodes:
                        node_id = node["id"]
                        n_type = node.get("type", "fact")
                        content = node.get("content", "")
                        embedding = node.get("embedding")
                        schedule = node.get("schedule")
                        timestamp = time.time()
                        
                        self.graph.add_node(
                            node_id, 
                            type=n_type, 
                            content=content, 
                            timestamp=timestamp, 
                            embedding=embedding,
                            schedule=schedule,
                            last_status=None,
                            last_confirmation=None,
                            meta={}
                        )
                        emb_json = json.dumps(embedding) if embedding else None
                        cursor.execute('''
                            INSERT OR REPLACE INTO nodes (id, type, content, timestamp, embedding, schedule, last_status, last_confirmation, meta)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (node_id, n_type, content, timestamp, emb_json, schedule, None, None, "{}"))
                    
                    for edge in edges:
                        source = edge["source"]
                        target = edge["target"]
                        relation = edge.get("relation", "related_to")
                        self.graph.add_edge(source, target, relation=relation)
                        cursor.execute('''
                            INSERT OR IGNORE INTO edges (source, target, relation)
                            VALUES (?, ?, ?)
                        ''', (source, target, relation))
                        
                    events = data.get("events", [])
                    from src.timeutil import now_local
                    now_ts = now_local().timestamp()
                    for ev in events:
                        kind = ev.get("kind")
                        sim = ev.get("simulated", 1)
                        days_ago = ev.get("days_ago", 0)
                        ts = now_ts - (days_ago * 86400)
                        
                        cursor.execute('''
                            INSERT INTO events (ts, kind, simulated)
                            VALUES (?, ?, ?)
                        ''', (ts, kind, sim))
                        
                    conn.commit()
                logger.info(f"Loaded {len(nodes)} nodes and {len(edges)} edges from seed {path}.")
            except Exception as e:
                logger.error(f"Failed to load seed data: {e}")

    def add_node(self, node_id: str, type: str, content: str, schedule: Optional[str] = None, last_status: Optional[str] = None, last_confirmation: Optional[float] = None, embedding: Optional[List[float]] = None) -> None:
        """
        Args:
            node_id: Unique identifier for the node.
            type: Node type (e.g., person, place, event, habit, med).
            content: Raw text content of the memory.
            schedule: HH:MM schedule for meds.
        """
        logger.info(f"add_node: id={node_id}, type={type}, content={content[:50]}")
        timestamp = time.time()
        if embedding is None:
            embedding = self.client.embed(content)
        
        with self.lock:
            existing = self.graph.nodes.get(node_id, {})
            if schedule is None:
                schedule = existing.get('schedule')
            if last_status is None:
                last_status = existing.get('last_status')
            if last_confirmation is None:
                last_confirmation = existing.get('last_confirmation')
    
            self.graph.add_node(
                node_id, 
                type=type, 
                content=content, 
                timestamp=timestamp, 
                embedding=embedding,
                schedule=schedule,
                last_status=last_status,
                last_confirmation=last_confirmation,
                meta={}
            )
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                emb_json = json.dumps(embedding)
                cursor.execute('''
                    INSERT OR REPLACE INTO nodes (id, type, content, timestamp, embedding, schedule, last_status, last_confirmation, meta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (node_id, type, content, timestamp, emb_json, schedule, last_status, last_confirmation, "{}"))
                conn.commit()
            
        logger.info(f"add_node: nodo aggiunto, totale nodi={self.graph.number_of_nodes()}")
        logger.info(f"DB salvato in {self.db_path}")
        try:
            logger.info(f"Dimensione DB attuale: {os.path.getsize(self.db_path)} bytes")
        except OSError:
            logger.warning(f"Impossibile leggere dimensione DB in {self.db_path}")

    def update_med_status(self, node_id: str, status: str, confirmation_time: float) -> None:
        with self.lock:
            if self.graph.has_node(node_id):
                self.graph.nodes[node_id]['last_status'] = status
                self.graph.nodes[node_id]['last_confirmation'] = confirmation_time
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE nodes 
                        SET last_status = ?, last_confirmation = ?
                        WHERE id = ?
                    ''', (status, confirmation_time, node_id))
                    conn.commit()
                logger.info(f"Updated med status for {node_id} to {status}")

    def add_edge(self, source: str, target: str, relation: str) -> None:
        """
        Add a directed relationship between two nodes and persist it.
        """
        with self.lock:
            if not self.graph.has_node(source) or not self.graph.has_node(target):
                logger.warning(f"Cannot add edge: source {source} or target {target} does not exist.")
                return
    
            self.graph.add_edge(source, target, relation=relation)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO edges (source, target, relation)
                    VALUES (?, ?, ?)
                ''', (source, target, relation))
                conn.commit()
            logger.info(f"Added edge from {source} to {target} ({relation})")

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not v1 or not v2:
            return 0.0
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return float(np.dot(vec1, vec2) / norm) if norm > 0 else 0.0

    def search(self, query: str, top_k: int = 5, query_embedding: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        Search the graph for nodes semantically similar to the query.
        
        Args:
            query: The search text.
            top_k: Number of top results to return.
            query_embedding: Pre-calculated embedding for the query.
            
        Returns:
            List of nodes sorted by similarity score.
        """
        if query_embedding is None:
            query_embedding = self.client.embed(query)
        results = []
        
        for node_id, data in self.graph.nodes(data=True):
            if "embedding" in data and data["embedding"]:
                score = self._cosine_similarity(query_embedding, data["embedding"])
                results.append({
                    "id": node_id,
                    "type": data.get("type"),
                    "content": data.get("content"),
                    "score": score
                })
                
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def count_recent_similar_interactions(self, query: str, time_window_seconds: int = 3600, similarity_threshold: float = 0.85, query_embedding: Optional[List[float]] = None) -> int:
        """
        Count how many recent interactions are semantically similar to the query.
        """
        if query_embedding is None:
            query_embedding = self.client.embed(query)
        current_time = time.time()
        count = 0
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == "interaction" and (current_time - data.get("timestamp", 0)) <= time_window_seconds:
                if "embedding" in data and data["embedding"]:
                    score = self._cosine_similarity(query_embedding, data["embedding"])
                    if score >= similarity_threshold:
                        count += 1
        return count

    def get_context(self, entity_id: str) -> Dict[str, Any]:
        """
        Retrieve a node and its direct neighbors to form context.
        """
        if not self.graph.has_node(entity_id):
            return {}
            
        node_data = self.graph.nodes[entity_id].copy()
        # Remove embedding from output context to save space/privacy
        node_data.pop("embedding", None)
        
        neighbors_out = [
            {"id": n, "relation": self.graph[entity_id][n]["relation"]}
            for n in self.graph.successors(entity_id)
        ]
        neighbors_in = [
            {"id": n, "relation": self.graph[n][entity_id]["relation"]}
            for n in self.graph.predecessors(entity_id)
        ]
        
        return {
            "node": {"id": entity_id, **node_data},
            "outgoing_edges": neighbors_out,
            "incoming_edges": neighbors_in
        }

    def delete(self, node_id: str) -> None:
        """
        Right to be forgotten: delete a node and its associated edges from memory.
        """
        with self.lock:
            if not self.graph.has_node(node_id):
                return
                
            self.graph.remove_node(node_id)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
                cursor.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node_id, node_id))
                conn.commit()
            logger.info(f"Deleted node {node_id} (right to be forgotten)")

    def export_graph(self) -> Dict[str, Any]:
        """
        Export the graph structure for dashboard visualization.
        """
        logger.info(f"export_graph: {self.graph.number_of_nodes()} nodi, {self.graph.number_of_edges()} edges")
        nodes = []
        for n, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            if node_type in ("interaction", "flag"):
                continue  # Hide raw interaction logs and flags from the graph
                
            content = data.get("content", n)
            label = content[:40] + "..." if len(content) > 40 else content
            nodes.append({
                "id": n, 
                "label": label, 
                "group": data.get("type", "unknown")
            })
            
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "from": u, 
                "to": v, 
                "label": data.get("relation", "")
            })
            
        return {"nodes": nodes, "edges": edges}

    def add_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        if not nodes:
            return
            
        timestamp = time.time()
        to_embed = []
        for n in nodes:
            if "embedding" not in n or n["embedding"] is None:
                to_embed.append(n)
                
        if to_embed:
            texts = [n.get("content", "") for n in to_embed]
            embs = self.client.embed_many(texts)
            for i, n in enumerate(to_embed):
                n["embedding"] = embs[i]
                
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for n in nodes:
                    node_id = n["id"]
                    n_type = n.get("type", "fact")
                    content = n.get("content", "")
                    schedule = n.get("schedule")
                    meta = n.get("meta", {})
                    embedding = n.get("embedding")
                    
                    self.graph.add_node(
                        node_id, 
                        type=n_type, 
                        content=content, 
                        timestamp=timestamp, 
                        embedding=embedding,
                        schedule=schedule,
                        last_status=None,
                        last_confirmation=None,
                        meta=meta
                    )
                    
                    emb_json = json.dumps(embedding) if embedding else None
                    meta_json = json.dumps(meta) if meta else None
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO nodes (id, type, content, timestamp, embedding, schedule, last_status, last_confirmation, meta)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (node_id, n_type, content, timestamp, emb_json, schedule, None, None, meta_json))
                conn.commit()

    def update_node(self, node_id: str, type: Optional[str] = None, content: Optional[str] = None, meta_patch: Optional[Dict[str, Any]] = None) -> None:
        with self.lock:
            if not self.graph.has_node(node_id):
                return
            
            node = self.graph.nodes[node_id]
            updated = False
            
            if type is not None and node.get("type") != type:
                node["type"] = type
                updated = True
                
            if content is not None and node.get("content") != content:
                node["content"] = content
                node["embedding"] = self.client.embed(content)
                updated = True
                
            if meta_patch is not None:
                meta = node.get("meta", {})
                meta.update(meta_patch)
                node["meta"] = meta
                updated = True
                
            if updated:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    emb_json = json.dumps(node.get("embedding")) if node.get("embedding") else None
                    meta_json = json.dumps(node.get("meta")) if node.get("meta") else None
                    cursor.execute('''
                        UPDATE nodes
                        SET type = ?, content = ?, embedding = ?, meta = ?
                        WHERE id = ?
                    ''', (node.get("type"), node.get("content"), emb_json, meta_json, node_id))
                    conn.commit()

    def log_event(self, kind: str, data: Optional[Dict[str, Any]] = None, simulated: bool = False, ts: Optional[float] = None) -> None:
        if ts is None:
            ts = time.time()
            
        data_json = json.dumps(data) if data else None
        sim_int = 1 if simulated else 0
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (ts, kind, data, simulated)
                    VALUES (?, ?, ?, ?)
                ''', (ts, kind, data_json, sim_int))
                conn.commit()

    def get_stats(self, days: int) -> Dict[str, Any]:
        """Get aggregated stats for the last N days."""
        from src.timeutil import now_local
        import time, json
        from collections import defaultdict
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import os
        
        now = now_local()
        end_ts = now.timestamp()
        start_ts = end_ts - (days * 86400)
        prev_start_ts = start_ts - (days * 86400)
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ts, kind, simulated FROM events WHERE ts >= ? AND ts < ?', (prev_start_ts, end_ts))
                rows = cursor.fetchall()
                
        metrics = defaultdict(lambda: {"interactions": 0, "repeats": 0, "confusion": 0, "sos": 0, 
                                     "meds_confirmed": 0, "meds_missed": 0, "meds_unsure": 0, "diary_turns": 0})
        
        totals = {"interactions": 0, "repeats": 0, "confusion": 0, "sos": 0, 
                 "meds_confirmed": 0, "meds_missed": 0, "meds_unsure": 0, "diary_turns": 0}
        prev_totals = {"interactions": 0, "repeats": 0, "confusion": 0, "sos": 0, 
                      "meds_confirmed": 0, "meds_missed": 0, "meds_unsure": 0, "diary_turns": 0}
                      
        simulated = False
        tz = ZoneInfo(os.getenv("TZ_NAME", "Europe/Rome"))
        
        for ts, kind, sim in rows:
            if sim == 1 and ts >= start_ts:
                simulated = True
                
            is_current = (ts >= start_ts)
            
            # map event kinds
            map_kind = kind
            if kind == 'user_message' or kind == 'diary_turn':
                map_kind = 'interactions'
            
            if is_current:
                if map_kind in totals:
                    totals[map_kind] += 1
                if kind == 'diary_turn':
                    totals['diary_turns'] += 1
                
                dt = datetime.fromtimestamp(ts, tz)
                day_str = dt.strftime('%Y-%m-%d')
                if map_kind in metrics[day_str]:
                    metrics[day_str][map_kind] += 1
                if kind == 'diary_turn':
                    metrics[day_str]['diary_turns'] += 1
            else:
                if map_kind in prev_totals:
                    prev_totals[map_kind] += 1
                if kind == 'diary_turn':
                    prev_totals['diary_turns'] += 1
                    
        return {
            "days": days,
            "simulated": simulated,
            "metrics_per_day": dict(metrics),
            "totals": totals,
            "prev_totals": prev_totals
        }
