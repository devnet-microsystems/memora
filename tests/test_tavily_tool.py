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

