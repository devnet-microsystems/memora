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
        
        # Logging moved to module level
            
        self._init_db()
        self._load_graph()

    def _get_connection(self):
        """Get a configured SQLite/SQLCipher connection."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite.connect(self.db_path)
        if HAS_SQLCIPHER and self.db_key:
            conn.execute(f"PRAGMA key='{self.db_key}'")
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 64000")
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    relation TEXT,
                    PRIMARY KEY (source, target, relation)
                )
            ''')
            conn.commit()

    def _load_graph(self) -> None:
        """Load the graph from SQLite into memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Load nodes
            cursor.execute("SELECT id, type, content, timestamp, embedding FROM nodes")
            for row in cursor.fetchall():
                node_id, n_type, content, ts, emb_json = row
                embedding = json.loads(emb_json) if emb_json else None
                self.graph.add_node(
                    node_id, 
                    type=n_type, 
                    content=content, 
                    timestamp=ts, 
                    embedding=embedding
                )
                
            # Load edges
            cursor.execute("SELECT source, target, relation FROM edges")
            for row in cursor.fetchall():
                source, target, relation = row
                self.graph.add_edge(source, target, relation=relation)

    def add_node(self, node_id: str, type: str, content: str) -> None:
        """
        Add or update a node in the memory graph and persist it.
        
        Args:
            node_id: Unique identifier for the node.
            type: Node type (e.g., person, place, event, habit, med).
            content: Raw text content of the memory.
        """
        logger.info(f"add_node: id={node_id}, type={type}, content={content[:50]}")
        timestamp = time.time()
        embedding = self.client.embed(content)
        
        self.graph.add_node(
            node_id, 
            type=type, 
            content=content, 
            timestamp=timestamp, 
            embedding=embedding
        )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            emb_json = json.dumps(embedding)
            cursor.execute('''
                INSERT OR REPLACE INTO nodes (id, type, content, timestamp, embedding)
                VALUES (?, ?, ?, ?, ?)
            ''', (node_id, type, content, timestamp, emb_json))
            conn.commit()
            
        logger.info(f"add_node: nodo aggiunto, totale nodi={self.graph.number_of_nodes()}")
        logger.info(f"DB salvato in {self.db_path}")
        try:
            logger.info(f"Dimensione DB attuale: {os.path.getsize(self.db_path)} bytes")
        except OSError:
            logger.warning(f"Impossibile leggere dimensione DB in {self.db_path}")

    def add_edge(self, source: str, target: str, relation: str) -> None:
        """
        Add a directed relationship between two nodes and persist it.
        """
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

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the graph for nodes semantically similar to the query.
        
        Args:
            query: The search text.
            top_k: Number of top results to return.
            
        Returns:
            List of nodes sorted by similarity score.
        """
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
            nodes.append({
                "id": n, 
                "label": n, 
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
