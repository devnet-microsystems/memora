"""
Tests for the Core AI Agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.agent import MemoraAgent

@pytest.fixture
def mock_dependencies():
    with patch('src.agent.NebiusClient') as mock_nebius, \
         patch('src.agent.MemoryGraph') as mock_memory, \
         patch('src.agent.TavilyTool') as mock_tavily:
        
        # Setup Nebius mock
        nebius_instance = mock_nebius.return_value
        nebius_instance.model_nano = "nano"
        nebius_instance.model_super = "super"
        nebius_instance.model_ultra = "ultra"
        
        yield {
            "nebius": nebius_instance,
            "memory": mock_memory.return_value,
            "tavily": mock_tavily.return_value
        }

@pytest.fixture
def agent(mock_dependencies):
    return MemoraAgent()

def test_respond(agent, mock_dependencies):
    """Test standard dialogue response."""
    mock_dependencies["memory"].search.return_value = [{"content": "Ricordo 1"}]
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["nebius"].chat.return_value = "Ciao, come stai?"
    
    response = agent.respond("Ciao")
    
    # Verify memory was searched for context
    mock_dependencies["memory"].search.assert_called_once_with("Ciao", top_k=3)
    # Verify Nebius was called
    mock_dependencies["nebius"].chat.assert_called_once()
    assert response == "Ciao, come stai?"

def test_quick_intent(agent, mock_dependencies):
    """Test intent classification uses Nano model."""
    mock_dependencies["nebius"].chat.return_value = "SALUTO"
    
    intent = agent.quick_intent("Buongiorno")
    
    mock_dependencies["nebius"].chat.assert_called_once()
    args, kwargs = mock_dependencies["nebius"].chat.call_args
    assert kwargs["model"] == "nano"
    assert intent == "SALUTO"

def test_plan_complex_task(agent, mock_dependencies):
    """Test task planning uses Ultra model."""
    mock_dependencies["nebius"].chat.return_value = "1. Fai X\n2. Fai Y"
    
    plan = agent.plan_complex_task("Organizza la giornata")
    
    mock_dependencies["nebius"].chat.assert_called_once()
    args, kwargs = mock_dependencies["nebius"].chat.call_args
    assert kwargs["model"] == "ultra"
    assert "1. Fai X" in plan

def test_check_anomaly(agent, mock_dependencies):
    """Test anomaly detection logic."""
    # Test positive anomaly
    mock_dependencies["nebius"].chat.return_value = "SI, c'è un'anomalia"
    is_anomalous = agent.check_anomaly(["Dove sono?", "Dove sono?", "Chi sei?"])
    assert is_anomalous is True
    
    # Test negative anomaly
    mock_dependencies["nebius"].chat.return_value = "NO, tutto regolare"
    is_anomalous = agent.check_anomaly(["Ciao", "Che ore sono?"])
    assert is_anomalous is False

def test_tools(agent, mock_dependencies):
    """Test that agent correctly exposes and delegates tool calls."""
    agent.memory_search("test")
    mock_dependencies["memory"].search.assert_called_with("test")
    
    agent.memory_add("id1", "person", "Mario")
    mock_dependencies["memory"].add_node.assert_called_with("id1", "person", "Mario")
    
    agent.tavily_search("farmacia")
    mock_dependencies["tavily"].search.assert_called_with("farmacia")
    
    # notify_caregiver just logs, so we ensure it returns True
    assert agent.notify_caregiver("Aiuto") is True
