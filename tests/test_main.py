"""
Tests for the FastAPI main application.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import app to test
from src.main import app

@pytest.fixture
def mock_env():
    # Ensure environment variables are set so clients don't fail initialization
    os.environ["NEBIUS_API_KEY"] = "test_nebius"
    os.environ["TAVILY_API_KEY"] = "test_tavily"
    yield
    # Cleanup (optional)
    del os.environ["NEBIUS_API_KEY"]
    del os.environ["TAVILY_API_KEY"]

@pytest.fixture
def client_and_mock(mock_env):
    """
    Mocks the MemoraAgent inside main.py to avoid real API calls.
    Yields the TestClient and the mock instance.
    """
    with patch("src.main.MemoraAgent") as mock_class:
        mock_instance = mock_class.return_value
        
        # Setup mocks on instance
        mock_instance.memory.export_graph.return_value = {"nodes": [], "edges": []}
        mock_instance.nebius.model_ultra = "ultra"
        mock_instance.nebius.chat.return_value = "Mocked Report"
        mock_instance.respond.return_value = "Mocked response"
        
        # Using context manager automatically triggers startup/shutdown events
        with TestClient(app) as test_client:
            yield test_client, mock_instance

def test_health(client_and_mock):
    """Test health endpoint."""
    client, _ = client_and_mock
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat(client_and_mock):
    """Test chat endpoint."""
    client, mock_agent = client_and_mock
    response = client.post("/chat", json={"user_input": "Ciao"})
    
    assert response.status_code == 200
    assert response.json() == {"response": "Mocked response"}
    mock_agent.respond.assert_called_once_with("Ciao")

def test_get_memory(client_and_mock):
    """Test memory export endpoint."""
    client, mock_agent = client_and_mock
    response = client.get("/memory")
    
    assert response.status_code == 200
    assert "nodes" in response.json()
    assert "edges" in response.json()
    mock_agent.memory.export_graph.assert_called_once()

def test_delete_memory(client_and_mock):
    """Test memory node deletion."""
    client, mock_agent = client_and_mock
    response = client.delete("/memory/test_node")
    
    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "node_id": "test_node"}
    mock_agent.memory.delete.assert_called_once_with("test_node")

def test_generate_report(client_and_mock):
    """Test report generation endpoint."""
    client, mock_agent = client_and_mock
    response = client.post("/report")
    
    assert response.status_code == 200
    assert response.json() == {"report": "Mocked Report"}
    mock_agent.nebius.chat.assert_called_once()
    args, kwargs = mock_agent.nebius.chat.call_args
    assert kwargs["model"] == "ultra"
    assert "report settimanale" in kwargs["messages"][0]["content"].lower()
