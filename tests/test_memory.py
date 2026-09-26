"""
Tests for the Persistent Memory Module.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.memory import MemoryGraph

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_memora.db")

@pytest.fixture
def mock_nebius_client():
    with patch('src.memory.NebiusClient') as mock_client:
        instance = mock_client.return_value
        # Mock embedding return: vector of 3 floats
        instance.embed.return_value = [0.1, 0.2, 0.3]
        yield instance

@pytest.fixture
def memory(temp_db_path, mock_nebius_client):
    return MemoryGraph(db_path=temp_db_path, db_key="test_key")

def test_add_node(memory, mock_nebius_client):
    """Test adding a node calculates embedding and saves to DB."""
    memory.add_node("mario", "person", "Mio figlio Mario")
    
    mock_nebius_client.embed.assert_called_once_with("Mio figlio Mario")
    assert memory.graph.has_node("mario")
    node = memory.graph.nodes["mario"]
    assert node["type"] == "person"
    assert node["content"] == "Mio figlio Mario"
    assert node["embedding"] == [0.1, 0.2, 0.3]

def test_add_edge(memory):
    """Test adding relations between nodes."""
    memory.add_node("maria", "person", "Utente principale")
    memory.add_node("luca", "person", "Nipote di Maria")
    memory.add_edge("maria", "luca", "nonna_di")
    
    assert memory.graph.has_edge("maria", "luca")
    assert memory.graph["maria"]["luca"]["relation"] == "nonna_di"

def test_delete_node(memory):
    """Test right to be forgotten: deleting node removes edges too."""
    memory.add_node("maria", "person", "Utente principale")
    memory.add_node("pillola", "med", "Pillola per la pressione")
    memory.add_edge("maria", "pillola", "deve_prendere")
    
    assert memory.graph.has_node("pillola")
    assert memory.graph.has_edge("maria", "pillola")
    
    memory.delete("pillola")
    
    assert not memory.graph.has_node("pillola")
    assert not memory.graph.has_edge("maria", "pillola")

def test_search(memory, mock_nebius_client):
    """Test semantic search over nodes."""
    memory.add_node("node1", "event", "Visita medica")
    memory.add_node("node2", "event", "Spesa al supermercato")
    
    # Same mocked embedding will yield score 1.0 for both
    results = memory.search("medico", top_k=2)
    assert len(results) == 2
    assert results[0]["score"] > 0
    assert "node" in results[0]["id"]

def test_get_context(memory):
    """Test context retrieval for an entity."""
    memory.add_node("maria", "person", "Utente")
    memory.add_node("luca", "person", "Nipote")
    memory.add_edge("maria", "luca", "nonna_di")
    
    ctx = memory.get_context("maria")
    assert ctx["node"]["id"] == "maria"
    assert len(ctx["outgoing_edges"]) == 1
    assert ctx["outgoing_edges"][0]["id"] == "luca"

def test_export_graph(memory):
    """Test exporting graph for dashboard."""
    memory.add_node("maria", "person", "Utente")
    memory.add_node("casa", "place", "Casa di Maria")
    memory.add_edge("maria", "casa", "vive_in")
    
    export = memory.export_graph()
    assert len(export["nodes"]) == 2
    assert len(export["edges"]) == 1
    assert export["nodes"][0]["label"] == "Utente"
