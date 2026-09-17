"""
Tests for the Tavily Web Search Tool.
"""

import os
import pytest
import concurrent.futures
from unittest.mock import patch
from src.tavily_tool import TavilyTool

@pytest.fixture
def mock_tavily_client():
    with patch('src.tavily_tool.TavilyClient') as mock_client_class:
        mock_instance = mock_client_class.return_value
        
        # Mock search response
        mock_instance.search.return_value = {
            "query": "test query",
            "results": [
                {
                    "title": "Test Title 1",
                    "url": "https://example.com/1",
                    "content": "Test content 1"
                },
                {
                    "title": "Test Title 2",
                    "url": "https://example.com/2",
                    "content": "Test content 2"
                }
            ]
        }
        yield mock_instance

@pytest.fixture
def tool(mock_tavily_client):
    # Ensure api key is set for the test
    os.environ["TAVILY_API_KEY"] = "test_key"
    return TavilyTool()

def test_search(tool, mock_tavily_client):
    """Test standard search returns mapped results."""
    results = tool.search("alzheimer symptoms", max_results=2)
    
    mock_tavily_client.search.assert_called_once()
    assert len(results) == 2
    assert results[0]["title"] == "Test Title 1"
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["snippet"] == "Test content 1"

def test_find_pharmacy(tool, mock_tavily_client):
    """Test pharmacy search generates correct query."""
    tool.find_pharmacy("Milano")
    
    mock_tavily_client.search.assert_called_once()
    args, kwargs = mock_tavily_client.search.call_args
    assert kwargs["query"] == "farmacia di turno vicino a Milano"

def test_find_guardia_medica(tool, mock_tavily_client):
    """Test guardia medica search generates correct query."""
    tool.find_guardia_medica("Roma")
    
    mock_tavily_client.search.assert_called_once()
    args, kwargs = mock_tavily_client.search.call_args
    assert "guardia medica" in kwargs["query"].lower()
    assert "Roma" in kwargs["query"]

def test_find_support_group(tool, mock_tavily_client):
    """Test support group search generates correct query."""
    tool.find_support_group("Alzheimer", "Napoli")
    
    mock_tavily_client.search.assert_called_once()
    args, kwargs = mock_tavily_client.search.call_args
    assert "gruppi di supporto" in kwargs["query"].lower()
    assert "Alzheimer" in kwargs["query"]
    assert "Napoli" in kwargs["query"]

def test_search_retry_on_timeout(tool, mock_tavily_client):
    """Test that the tenacity retry mechanism triggers on timeout."""
    import tenacity
    
    # Simulate a timeout by raising concurrent.futures.TimeoutError when client.search is called
    mock_tavily_client.search.side_effect = concurrent.futures.TimeoutError("Timeout!")
    
    with pytest.raises(tenacity.RetryError):
        tool.search("test", max_results=1)
        
    # Tenacity should retry up to the configured limit (3 attempts total)
    assert mock_tavily_client.search.call_count == 3
