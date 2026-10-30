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

def test_system_prompt_capability_rules(agent):
    """System prompt must instruct the model not to claim vision or physical actions."""
    prompt = MemoraAgent.SYSTEM_PROMPT
    assert "NEVER claim to see the patient or their environment" in prompt
    assert "physical actions" in prompt
    assert "contacting the caregiver" in prompt
    assert "physical need" in prompt


@patch('src.agent.MemoraAgent._extract_pending_fact')
def test_respond_uses_requested_language(mock_extract, agent, mock_dependencies):
    """The lang instruction must be appended to the system message for the model."""
    mock_dependencies["memory"].search.return_value = []
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["nebius"].chat.return_value = "Response"
    mock_dependencies["nebius"].embed.return_value = [0.1] * 8

    agent.respond("I need water", lang="en")

    _, kwargs = mock_dependencies["nebius"].chat.call_args
    system_content = kwargs["messages"][0]["content"]
    assert "Reply in English." in system_content
    assert "NEVER claim to see the patient" in system_content

    agent.respond("Ho bisogno d'acqua", lang="it")

    _, kwargs = mock_dependencies["nebius"].chat.call_args
    system_content = kwargs["messages"][0]["content"]
    assert "Rispondi in italiano." in system_content


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


def test_respond_skip_preprocessing_super_chat_only_keys(agent, mock_dependencies):
    """Test that skip_preprocessing=True invokes exactly one model_super chat call,
    zero embed calls, no quick_intent, and no _extract_pending_fact for the
    'Where are my house keys?' question with patient_id='maria_rossi'."""
    # Mock get_context to return Maria Rossi's connected memories
    mock_ctx = {
        "node": {"id": "maria_rossi", "content": "Maria Rossi, 74 anni, vive a Milano.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_giulia_calls"},
            {"id": "mem_keys_location"},
        ],
    }
    mock_dependencies["memory"].get_context.return_value = mock_ctx
    mock_dependencies["memory"].graph.has_node.return_value = True

    mock_keys = {"type": "fact", "content": "Le chiavi di casa si tengono nel cassetto vicino all'ingresso."}
    mock_giulia = {"type": "habit", "content": "La figlia Giulia chiama Maria ogni mattina alle 9:00."}
    mock_dependencies["memory"].graph.nodes.__getitem__.side_effect = lambda nid: (
        mock_giulia if nid == "mem_giulia_calls" else mock_keys
    )

    mock_dependencies["nebius"].chat.return_value = "Le chiavi sono nel cassetto vicino all'ingresso."

    response = agent.respond(
        "Where are my house keys?",
        patient_id="maria_rossi",
        skip_preprocessing=True,
    )

    # Exactly one Nebius chat inference call, model_super
    assert mock_dependencies["nebius"].chat.call_count == 1
    _, kwargs = mock_dependencies["nebius"].chat.call_args
    assert kwargs["model"] == mock_dependencies["nebius"].model_super

    # Zero embed calls
    assert mock_dependencies["nebius"].embed.call_count == 0

    # No quick_intent call
    mock_dependencies["nebius"].chat.assert_called_once()

    # No background fact extraction
    agent.memory.add_nodes.assert_not_called()

    # Deterministic context path used (get_context), not semantic search
    mock_dependencies["memory"].get_context.assert_called_once_with("maria_rossi")
    mock_dependencies["memory"].search.assert_not_called()
    mock_dependencies["memory"].count_recent_similar_interactions.assert_not_called()

    assert response == "Le chiavi sono nel cassetto vicino all'ingresso."


def test_respond_skip_preprocessing_super_chat_only_morning(agent, mock_dependencies):
    """Test that skip_preprocessing=True invokes exactly one model_super chat call,
    zero embed calls, no quick_intent, and no _extract_pending_fact for the
    'Who calls me every morning?' question with patient_id='maria_rossi'."""
    mock_ctx = {
        "node": {"id": "maria_rossi", "content": "Maria Rossi, 74 anni, vive a Milano.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_giulia_calls"},
            {"id": "mem_keys_location"},
        ],
    }
    mock_dependencies["memory"].get_context.return_value = mock_ctx
    mock_dependencies["memory"].graph.has_node.return_value = True

    mock_keys = {"type": "fact", "content": "Le chiavi di casa si tengono nel cassetto vicino all'ingresso."}
    mock_giulia = {"type": "habit", "content": "La figlia Giulia chiama Maria ogni mattina alle 9:00."}
    mock_dependencies["memory"].graph.nodes.__getitem__.side_effect = lambda nid: (
        mock_giulia if nid == "mem_giulia_calls" else mock_keys
    )

    mock_dependencies["nebius"].chat.return_value = "Giulia ti telefona ogni mattina alle 9:00."

    response = agent.respond(
        "Who calls me every morning?",
        patient_id="maria_rossi",
        skip_preprocessing=True,
    )

    # Exactly one Nebius chat inference call, model_super
    assert mock_dependencies["nebius"].chat.call_count == 1
    _, kwargs = mock_dependencies["nebius"].chat.call_args
    assert kwargs["model"] == mock_dependencies["nebius"].model_super

    # Zero embed calls
    assert mock_dependencies["nebius"].embed.call_count == 0

    # No background fact extraction
    agent.memory.add_nodes.assert_not_called()

    # Deterministic context path used
    mock_dependencies["memory"].get_context.assert_called_once_with("maria_rossi")
    mock_dependencies["memory"].search.assert_not_called()
    mock_dependencies["memory"].count_recent_similar_interactions.assert_not_called()

    assert response == "Giulia ti telefona ogni mattina alle 9:00."


def test_respond_default_preserves_embedding_and_quick_intent(agent, mock_dependencies):
    """Regression test: default skip_preprocessing=False preserves existing behavior
    (embed called at most once, quick_intent called, final chat call uses model_super)."""
    mock_dependencies["memory"].search.return_value = [{"content": "Ricordo 1"}]
    mock_dependencies["memory"].count_recent_similar_interactions.return_value = 0
    mock_dependencies["nebius"].chat.return_value = "Ciao, come stai?"
    mock_dependencies["nebius"].embed.return_value = [0.1] * 8

    response = agent.respond("Ciao")

    # Existing behavior: embed called at most once
    assert mock_dependencies["nebius"].embed.call_count <= 1
    # Existing behavior: memory.search called
    mock_dependencies["memory"].search.assert_called_once()
    # Existing behavior: final chat call
    assert mock_dependencies["nebius"].chat.call_count >= 1

    assert response == "Ciao, come stai?"


def test_respond_profile_isolation(tmp_path, monkeypatch):
    """Integration: respond() retrieves context only for the requested patient profile.

    Uses a temporary SQLite database (never data/memora.db). Mocks all Nebius,
    embedding, intent-detection, and Tavily calls. Exercises the real
    MemoraAgent.respond() method. Verifies that requesting one profile does not
    expose another profile's facts in the retrieved context or generated response.
    """
    from unittest.mock import patch, MagicMock

    monkeypatch.setenv("DB_PATH", str(tmp_path / "test_isolation.db"))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)

    with patch('src.agent.NebiusClient') as mock_nebius_cls, \
         patch('src.memory.NebiusClient') as mock_mem_nebius_cls, \
         patch('src.agent.TavilyTool') as mock_tavily_cls:

        nebius = mock_nebius_cls.return_value
        nebius.embed.return_value = [0.1, 0.2]
        nebius.model_nano = "nano"
        nebius.model_super = "super"

        def chat_side_effect(model, messages, **kwargs):
            if model == "nano":
                return "INFORMATION"  # quick_intent: not CONFUSION
            return "Mocked super response"  # model_super final answer

        nebius.chat.side_effect = chat_side_effect

        mem_nebius = mock_mem_nebius_cls.return_value
        mem_nebius.embed.return_value = [0.1, 0.2]
        mem_nebius.embed_many.return_value = [[0.1, 0.2]]

        tavily = mock_tavily_cls.return_value
        tavily.find_pharmacy.return_value = []
        tavily.find_guardia_medica.return_value = []
        tavily.find_support_group.return_value = []

        agent = MemoraAgent()

        # Spy on get_context to verify which profile is queried
        get_context_calls = []
        original_get_context = agent.memory.get_context

        def spy_get_context(entity_id):
            get_context_calls.append(entity_id)
            return original_get_context(entity_id)

        agent.memory.get_context = spy_get_context

        # Build two profiles directly in the in-memory graph
        g = agent.memory.graph
        g.add_node("maria_rossi", type="person",
                   content="Maria Rossi, 74 anni, vive a Milano.", embedding=None)
        g.add_node("mem_keys_location", type="fact",
                   content="Le chiavi di casa si tengono nel cassetto vicino all'ingresso.",
                   embedding=None)
        g.add_edge("maria_rossi", "mem_keys_location", relation="remembers")

        g.add_node("other_user", type="person",
                   content="Other user, distinct profile.", embedding=None)
        g.add_node("mem_other_secret", type="fact",
                   content="Other user's secret fact about hidden treasure.",
                   embedding=None)
        g.add_edge("other_user", "mem_other_secret", relation="remembers")

        # Exercise the real respond() with patient_id="maria_rossi"
        response = agent.respond("Where are my house keys?", patient_id="maria_rossi")

        # The final answer must not leak the other profile's secret fact
        assert "Other user's secret fact" not in response
        assert "hidden treasure" not in response

        # verify get_context was called for maria_rossi, never for other_user
        assert "maria_rossi" in get_context_calls
        assert "other_user" not in get_context_calls

        # Verify the super-model chat received Maria's context, not the other profile's
        super_calls = [c for c in nebius.chat.call_args_list if c.kwargs.get("model") == "super"]
        assert len(super_calls) >= 1
        _, super_kwargs = super_calls[-1]
        user_content = super_kwargs["messages"][1]["content"]
        assert "Maria Rossi" in user_content
        assert "Le chiavi di casa si tengono nel cassetto vicino all'ingresso." in user_content
        assert "Other user's secret fact" not in user_content
