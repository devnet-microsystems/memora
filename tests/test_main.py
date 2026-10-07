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
    old_memora = os.environ.pop("MEMORA_API_KEY", None)
    yield
    if old_memora:
        os.environ["MEMORA_API_KEY"] = old_memora
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
        mock_instance.memory.get_stats.return_value = {
            "days": 7,
            "simulated": False,
            "metrics_per_day": {},
            "totals": {},
            "prev_totals": {}
        }
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
    assert response.json()["status"] == "ok"
    assert "encrypted" in response.json()

def test_chat(client_and_mock):
    """Test chat endpoint."""
    client, mock_agent = client_and_mock
    response = client.post("/chat", json={"user_input": "Ciao"})
    
    assert response.status_code == 200
    assert response.json() == {"response": "Mocked response"}
    mock_agent.respond.assert_called_once_with("Ciao", lang="en")

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
    response = client.delete("/memory/test_node", headers={"Authorization": "Bearer memora-secure-token"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "node_id": "test_node"}
    mock_agent.memory.delete.assert_called_once_with("test_node")

def test_generate_report(client_and_mock):
    """Test report generation endpoint."""
    client, mock_agent = client_and_mock
    response = client.post("/report", headers={"Authorization": "Bearer memora-secure-token"})
    
    assert response.status_code == 200
    assert response.json()["report"] == "Mocked Report"
    assert "stats" in response.json()
    mock_agent.nebius.chat.assert_called_once()
    args, kwargs = mock_agent.nebius.chat.call_args
    assert kwargs["model"] == "ultra"
    assert "caregiver report" in kwargs["messages"][0]["content"].lower()

def test_handle_sos(client_and_mock):
    client, mock_agent = client_and_mock
    response = client.post("/sos", json={"patient_id": "maria", "type": "medical"})

    assert response.status_code == 200
    alert_id = response.json()["alert_id"]
    # The SOS is written directly as an *open alert*, with no embedding call and no approval queue.
    (nodes,), _ = mock_agent.memory.add_nodes.call_args
    assert nodes[0]["id"] == alert_id
    assert nodes[0]["type"] == "alert"
    assert nodes[0]["skip_embedding"] is True
    assert nodes[0]["meta"]["status"] == "open"
    mock_agent.memory.log_event.assert_any_call("sos", data={"patient_id": "maria", "type": "medical"})

def test_usage(client_and_mock):
    client, mock_agent = client_and_mock
    mock_agent.nebius.get_usage.return_value = {
        "calls": 5,
        "input_tokens": 100,
        "output_tokens": 50,
        "estimated_cost_usd": 0.001,
        "latency_by_model": {}
    }
    
    response = client.get("/usage", headers={"Authorization": "Bearer memora-secure-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["calls"] == 5
    mock_agent.nebius.get_usage.assert_called_once()

from datetime import datetime, timezone

def test_today_endpoint(client_and_mock):
    client, mock_agent = client_and_mock
    
    # Mocking graph data
    mock_agent.memory.graph.nodes = MagicMock()
    
    # Let's say today is 2026-10-05 (Monday)
    now_dt = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
    # yesterday confirmation
    yest_ts = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc).timestamp()
    
    def mock_nodes_iter(data=True):
        return [
            ("med_1", {"type": "med", "content": "Med 1", "schedule": "08:00", "last_status": "confirmed", "last_confirmation": yest_ts}),
            ("med_2", {"type": "med", "content": "Med 2", "schedule": "11:00", "last_status": "confirmed", "last_confirmation": now_dt.timestamp()}),
            ("event_1", {"type": "event", "content": "Visita", "schedule": "2026-10-05 14:00"}),
            ("habit_1", {"type": "habit", "content": "Passeggiata", "schedule": "MON,WED 10:30"})
        ]
    mock_agent.memory.graph.nodes.side_effect = mock_nodes_iter
    
    mock_agent.memory.graph.has_node.return_value = True
    # Mock property for patient node
    type(mock_agent.memory.graph).nodes = MagicMock(return_value={"patient": {"type": "person", "content": "Mario Rossi", "meta": {"name": "Mario"}}})
    
    # Need to properly mock both dict access for `nodes["patient"]` and method call for `nodes(data=True)`
    nodes_mock = MagicMock()
    nodes_mock.side_effect = mock_nodes_iter
    nodes_mock.__getitem__.return_value = {"type": "person", "content": "Mario Rossi", "meta": {"name": "Mario"}}
    mock_agent.memory.graph.nodes = nodes_mock

    with patch("src.main.now_local", return_value=now_dt):
        response = client.get("/today?lang=it")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["patient_name"] == "Mario"
        assert data["weekday"] == "Lunedì"
        assert len(data["items"]) == 4
        
        items = data["items"]
        assert items[0]["time"] == "08:00"
        assert items[0]["status"] == "none"  # confirmed yesterday
        assert items[1]["time"] == "10:30"
        assert items[1]["kind"] == "habit"
        assert items[2]["time"] == "11:00"
        assert items[2]["status"] == "confirmed" # confirmed today
        assert items[3]["time"] == "14:00"
        assert items[3]["kind"] == "event"
