import pytest
from unittest.mock import patch, MagicMock
from src.agent import MemoraAgent

@patch('src.agent.NebiusClient')
@patch('src.agent.MemoryGraph')
@patch('src.agent.TavilyTool')
def test_diary_flow(mock_tavily, mock_memory, mock_nebius):
    agent = MemoraAgent()
    
    mock_nebius.return_value.chat.return_value = "Che bella storia."
    
    # Session starts
    reply = agent.diary_turn("sess1", "Oggi sono andato al mare.", lang="it")
    assert reply == "Che bella storia."
    assert "sess1" in agent.diary_sessions
    assert len(agent.diary_sessions["sess1"]["turns"]) == 2
    
    # Test disagio
    reply2 = agent.diary_turn("sess1", "Aiuto, ho paura del buio.", lang="it")
    assert "Facciamo una pausa" in reply2
    
    # Session ended by disagio
    assert "sess1" not in agent.diary_sessions

@patch('src.agent.NebiusClient')
@patch('src.agent.MemoryGraph')
@patch('src.agent.TavilyTool')
def test_extract_diary_facts(mock_tavily, mock_memory, mock_nebius):
    agent = MemoraAgent()
    
    # Mock LLM to return JSON
    agent.nebius.chat.return_value = '''
    [
        {"type": "event", "label": "Gita", "description": "Sono andato al mare", "when": "Oggi"}
    ]
    '''
    agent.nebius.embed.return_value = [0.1]*8
    agent.memory.lock = MagicMock()
    agent.memory.lock.__enter__ = MagicMock()
    agent.memory.lock.__exit__ = MagicMock()
    
    agent.memory.graph.nodes = MagicMock(return_value=[])
    
    agent._extract_diary_facts("Oggi sono andato al mare")
    
    agent.memory.add_nodes.assert_called_once()
    added_nodes = agent.memory.add_nodes.call_args[0][0]
    assert len(added_nodes) == 1
    assert added_nodes[0]["type"] == "pending"
    assert added_nodes[0]["meta"]["proposed_type"] == "event"
