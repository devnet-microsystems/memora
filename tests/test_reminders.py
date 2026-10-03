import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.agent import MemoraAgent

def test_med_state_transitions():
    from src.schedule import med_state
    now = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
    
    node = {
        "schedule": "10:00",
        "last_status": "none",
        "meta": {}
    }
    
    # 09:59 -> upcoming
    assert med_state(node, now - timedelta(minutes=1)) == "upcoming"
    
    # 10:00 -> due
    assert med_state(node, now) == "due"
    
    # 10:29 -> due
    assert med_state(node, now + timedelta(minutes=29)) == "due"
    
    # 10:30 -> missed
    assert med_state(node, now + timedelta(minutes=30)) == "missed"
    
    # snooze test
    node["meta"]["snoozed_until"] = (now + timedelta(minutes=10)).timestamp()
    assert med_state(node, now) == "snoozed"
    
    # past snooze -> due or missed
    assert med_state(node, now + timedelta(minutes=11)) == "due"
    
    # confirmation today
    node["last_status"] = "confirmed"
    node["last_confirmation"] = now.timestamp()
    assert med_state(node, now) == "confirmed"
    
    # confirmation yesterday
    node["last_confirmation"] = (now - timedelta(days=1)).timestamp()
    assert med_state(node, now + timedelta(minutes=11)) == "due"


@patch('src.agent.NebiusClient')
@patch('src.agent.MemoryGraph')
@patch('src.agent.TavilyTool')
def test_deterministic_med_answer(mock_tavily, mock_memory, mock_nebius):
    agent = MemoraAgent()
    
    now_dt = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
    
    node_data = {
        "type": "med",
        "content": "Aspirina",
        "schedule": "10:00",
        "last_status": "none"
    }
    
    agent.memory.graph.nodes = MagicMock(return_value=[("med1", node_data)])
    agent.memory.lock = MagicMock()
    agent.memory.lock.__enter__ = MagicMock()
    agent.memory.lock.__exit__ = MagicMock()
    agent.memory.count_recent_similar_interactions.return_value = 0
    
    # Mock LLM to fail if called to prove it's deterministic
    agent.nebius.chat.side_effect = Exception("LLM SHOULD NOT BE CALLED")
    
    with patch("src.timeutil.now_local", return_value=now_dt):
        # 09:59 -> upcoming
        with patch("src.timeutil.now_local", return_value=now_dt - timedelta(minutes=1)):
            resp = agent.respond("ho preso la pillola?")
            assert "Aspirina è previsto per le 10:00" in resp or "Aspirina is planned for 10:00" in resp
        
        # 10:00 -> due -> "I have no confirmation"
        with patch("src.timeutil.now_local", return_value=now_dt):
            resp = agent.respond("ho preso la medicina?")
            assert "Ho chiesto al tuo caregiver" in resp or "I've asked your caregiver" in resp
            
        # 10:00 confirmed
        node_data["last_status"] = "confirmed"
        node_data["last_confirmation"] = now_dt.timestamp()
        with patch("src.timeutil.now_local", return_value=now_dt):
            resp = agent.respond("did I take my pill?")
            assert "hai confermato" in resp or "you confirmed" in resp

def test_snooze_limit():
    from src.main import app, confirm_med
    from src.main import MedConfirmRequest
    from fastapi.testclient import TestClient
    
    now_dt = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
    
    with patch("src.main.agent") as mock_agent:
        node_data = {
            "type": "med",
            "content": "Aspirina",
            "schedule": "10:00",
            "meta": {"snooze_count": 2, "snooze_count_date": "2026-10-05"}
        }
        mock_agent.memory.graph.has_node.return_value = True
        mock_agent.memory.graph.nodes.__getitem__.return_value = node_data
        
        client = TestClient(app)
        
        with patch("src.main.now_local", return_value=now_dt), patch.dict(os.environ, clear=True, values={k:v for k,v in os.environ.items() if k != "MEMORA_API_KEY"}):
            if "MEMORA_API_KEY" in os.environ:
                del os.environ["MEMORA_API_KEY"]
            response = client.post("/med/confirm", json={"med_id": "med1", "status": "snoozed"})
            assert response.status_code == 200
            assert response.json()["status"] == "error"
            assert response.json()["message"] == "Max snoozes reached"

def test_unsure_escalation():
    from src.main import app, confirm_med
    from src.main import MedConfirmRequest
    from fastapi.testclient import TestClient
    
    now_dt = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
    
    with patch("src.main.agent") as mock_agent:
        node_data = {
            "type": "med",
            "content": "Aspirina",
            "schedule": "10:00",
            "meta": {}
        }
        mock_agent.memory.graph.has_node.return_value = True
        mock_agent.memory.graph.nodes.__getitem__.return_value = node_data
        
        client = TestClient(app)
        
        with patch("src.main.now_local", return_value=now_dt), patch.dict(os.environ, clear=True, values={k:v for k,v in os.environ.items() if k != "MEMORA_API_KEY"}):
            if "MEMORA_API_KEY" in os.environ:
                del os.environ["MEMORA_API_KEY"]
            response = client.post("/med/confirm", json={"med_id": "med1", "status": "unsure"})
            assert response.status_code == 200
            mock_agent.notify_caregiver.assert_called_once()
            
            # Second call should not notify again today
            mock_agent.notify_caregiver.reset_mock()
            # Note: since it's a mock, we need to manually update node_data if we want to simulate state change,
            # but the endpoint calls update_node. Let's just check if it was called once on the first time.
