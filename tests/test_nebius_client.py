"""
Tests for the Nebius Client.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.nebius_client import NebiusClient

@pytest.fixture
def mock_env():
    os.environ["NEBIUS_API_KEY"] = "test_key"
    yield
    # Cleanup not strictly needed if we just overwrite, but good practice
    del os.environ["NEBIUS_API_KEY"]

@pytest.fixture
def mock_openai():
    with patch("src.nebius_client.OpenAI") as mock_openai_class:
        yield mock_openai_class.return_value

@pytest.fixture
def client(mock_env, mock_openai):
    # To speed up tests, we can temporarily disable the wait on the retry decorator
    # However, since retry is applied at import time, we'll just let it run or patch sleep
    with patch("tenacity.nap.time.sleep"): 
        yield NebiusClient()

def test_redact(client):
    """Test PII redaction."""
    # Test phone
    assert client._redact("Il mio numero è +39 333 123456") == "Il mio numero è [PHONE]"
    assert client._redact("Chiama +39 333 123456") == "Chiama [PHONE]"
    # Test email
    assert client._redact("Scrivi a test.email@example.com per info") == "Scrivi a [EMAIL] per info"
    # Test DOB
    assert client._redact("Nato il 15/05/1990 in Italia") == "Nato il [DOB] in Italia"
    assert client._redact("Nata il 15-05-1990 oggi") == "Nata il [DOB] oggi"
    # Test CF
    assert client._redact("Il CF è RSSMRA85T10A562S") == "Il CF è [CF REDACTED]"

def test_chat(client, mock_openai):
    """Test standard chat completion with redaction."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Risposta mockata"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_openai.chat.completions.create.return_value = mock_response
    
    messages = [{"role": "user", "content": "Il mio numero è 333-1234567"}]
    response = client.chat(model="test_model", messages=messages)
    
    assert response == "Risposta mockata"
    mock_openai.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai.chat.completions.create.call_args
    # Verify the message was redacted before sending
    assert kwargs["messages"][0]["content"] == "Il mio numero è [PHONE]"

def test_chat_stream(client, mock_openai):
    """Test streaming chat completion with redaction."""
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Ciao "
    
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "mondo!"
    
    mock_openai.chat.completions.create.return_value = [chunk1, chunk2]
    
    messages = [{"role": "user", "content": "test@test.com"}]
    
    chunks = list(client.chat_stream(model="test_model", messages=messages))
    
    assert chunks == ["Ciao ", "mondo!"]
    args, kwargs = mock_openai.chat.completions.create.call_args
    assert kwargs["stream"] is True
    assert kwargs["messages"][0]["content"] == "[EMAIL]"

def test_quick_intent(client, mock_openai):
    """Test quick intent helper."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "SALUTO"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_openai.chat.completions.create.return_value = mock_response
    
    assert client.quick_intent("Ciao") == "SALUTO"

def test_respond(client, mock_openai):
    """Test respond helper."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Risposta"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_openai.chat.completions.create.return_value = mock_response
    
    assert client.respond("Domanda") == "Risposta"

def test_plan(client, mock_openai):
    """Test plan helper."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Piano"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_openai.chat.completions.create.return_value = mock_response
    
    assert client.plan("Organizza") == "Piano"

def test_embed(client, mock_openai):
    """Test embedding with redaction."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = [0.1, 0.2]
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_openai.embeddings.create.return_value = mock_response
    
    emb = client.embed("test.email@example.com")
    
    assert emb == [0.1, 0.2]
    args, kwargs = mock_openai.embeddings.create.call_args
    assert kwargs["input"] == "[EMAIL]"

def test_retry(client, mock_openai):
    """Test tenacity retry on chat."""
    # Fail twice, succeed third time
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Successo"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    
    mock_openai.chat.completions.create.side_effect = [
        Exception("API Error"),
        Exception("API Error"),
        mock_response
    ]
    
    response = client.chat(model="test", messages=[])
    assert response == "Successo"
    assert mock_openai.chat.completions.create.call_count == 3
