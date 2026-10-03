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

@patch('src.agent.MemoraAgent._extract_pending_fact')
def test_respond(mock_extract, agent, mock_dependencies):
    """Test standard dialogue response."""
    mock_dependencies["memory"].search.return_value = [{"content": "Ricordo 1"}]
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["nebius"].chat.return_value = "Ciao, come stai?"
    
    response = agent.respond("Ciao")
    
    # Verify memory was searched for context
    mock_dependencies["memory"].search.assert_called_once()
    
    # Verify embed was called at most once
    assert mock_dependencies["nebius"].embed.call_count <= 1
    
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
    mock_dependencies["nebius"].chat.return_value = "YES, there is an anomaly"
    is_anomalous = agent.check_anomaly(["Dove sono?", "Dove sono?", "Chi sei?"])
    assert is_anomalous is True
    
    # Test negative anomaly
    mock_dependencies["nebius"].chat.return_value = "NO, everything is fine"
    is_anomalous = agent.check_anomaly(["Ciao", "Che ore sono?"])
    assert is_anomalous is False

def test_tools(agent, mock_dependencies):
    """Test that agent correctly exposes and delegates tool calls."""
    agent.memory_search("test")
    mock_dependencies["memory"].search.assert_called_with("test")
    
    agent.memory_add("id1", "person", "Mario")
    mock_dependencies["memory"].add_nodes.assert_called()
    
    agent.tavily_search("farmacia")
    mock_dependencies["tavily"].search.assert_called_with("farmacia")
    
    # notify_caregiver just logs, so we ensure it returns True
    assert agent.notify_caregiver("Aiuto") is True

@patch('src.agent.MemoraAgent._home_location', return_value="Milano")
@patch('src.agent.MemoraAgent._extract_pending_fact')
def test_respond_tavily_success(mock_extract, mock_home, agent, mock_dependencies):
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["tavily"].find_pharmacy.return_value = [{"title": "Farmacia Roma", "snippet": "Aperta", "url": "http"}]
    mock_dependencies["nebius"].chat.return_value = "Test response"
    mock_dependencies["nebius"].embed.return_value = [0.1]*8
    
    agent.respond("cerco una farmacia")
    
    mock_dependencies["tavily"].find_pharmacy.assert_called_with("Milano")
    
    args, kwargs = mock_dependencies["nebius"].chat.call_args
    user_prompt = kwargs["messages"][1]["content"]
    assert "VERIFIED WEB RESULTS" in user_prompt
    assert "Farmacia Roma" in user_prompt

@patch('src.agent.MemoraAgent._home_location', return_value="Milano")
@patch('src.agent.MemoraAgent._extract_pending_fact')
def test_respond_tavily_exception(mock_extract, mock_home, agent, mock_dependencies):
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["tavily"].find_pharmacy.side_effect = Exception("API Error")
    mock_dependencies["nebius"].chat.return_value = "Test response"
    mock_dependencies["nebius"].embed.return_value = [0.1]*8
    
    agent.respond("cerco una farmacia")
    
    args, kwargs = mock_dependencies["nebius"].chat.call_args
    user_prompt = kwargs["messages"][1]["content"]
    assert "WEB SEARCH UNAVAILABLE" in user_prompt

@patch('src.agent.MemoraAgent.notify_caregiver')
@patch('src.agent.MemoraAgent._extract_pending_fact')
def test_respond_confusion(mock_extract, mock_notify, agent, mock_dependencies):
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["nebius"].chat.return_value = "Test response"
    mock_dependencies["nebius"].embed.return_value = [0.1]*8
    agent.quick_intent = MagicMock(return_value="CONFUSION")
    
    agent.respond("dove sono?")
    
    # Verify flag node was added via memory.add_node
    add_node_calls = agent.memory.add_node.call_args_list
    flag_added = False
    for call in add_node_calls:
        args, kwargs = call
        if len(args) >= 3 and args[1] == "flag" and "Possible confusion detected: dove sono?" in args[2]:
            flag_added = True
            break
    assert flag_added, "Flag node not added to memory"
    
    mock_notify.assert_called_once()

def test_process_onboarding_interview(agent, mock_dependencies):
    """Test onboarding interview parsing with robust JSON extraction and mapping."""
    import json
    # Mock the LLM to return some markdown with JSON
    mock_response = '''
    Here is the requested data:
    ```json
    [
        {"type": "farmaco", "label": "Cardioaspirina", "description": "1 compressa", "schedule": "08:00"}
    ]
    ```
    '''
    mock_dependencies["nebius"].chat.return_value = mock_response
    
    agent.memory.graph.has_node.return_value = False
    
    result = agent.process_onboarding_interview("Cardioaspirina alle 08:00")
    
    assert result["status"] == "success"
    assert len(result["extracted"]) == 1
    assert result["extracted"][0]["type"] == "med"
    
    # Check if patient node was created
    agent.memory.add_node.assert_any_call("patient", "person", "Patient (Memora user)")
    
    # Check if med node was created in add_nodes
    add_nodes_calls = agent.memory.add_nodes.call_args_list
    med_created = False
    for call in add_nodes_calls:
        nodes = call[0][0]
        for node in nodes:
            if node.get("type") == "med" and "Cardioaspirina" in node.get("content", ""):
                assert node.get("schedule") == "08:00"
                med_created = True
                break
    assert med_created, "Med node not added"
    
    # Check if edge was created
    edge_calls = agent.memory.add_edge.call_args_list
    edge_created = False
    for call in edge_calls:
        args, kwargs = call
        if len(args) >= 3 and args[0] == "patient" and args[2] == "takes":
            edge_created = True
            break
    assert edge_created, "Edge from patient not added"
