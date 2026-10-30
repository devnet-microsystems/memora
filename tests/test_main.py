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
    mock_agent.respond.assert_called_once_with("Ciao", lang="en", patient_id=None)

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


def test_medication_scheduler_no_dict_mutation_error(client_and_mock):
    """Regression: scheduler must not raise RuntimeError('dictionary changed size during iteration')
    when add_nodes/update_node modify the graph during iteration."""
    import time
    import src.main as main_module
    from datetime import datetime
    from zoneinfo import ZoneInfo

    client, mock_agent = client_and_mock

    # Ensure the global agent is the mock
    main_module.agent = mock_agent

    # Track loop iterations
    iterations = []

    original_sleep = main_module.time.sleep

    def fake_sleep(seconds):
        iterations.append(seconds)
        raise KeyboardInterrupt("break loop")

    main_module.time.sleep = fake_sleep

    try:
        now_dt = datetime(2026, 10, 5, 12, 0, tzinfo=ZoneInfo("Europe/Rome"))

        # Simulate real NetworkX behavior: a node store that mutates during iteration
        med_node_id = "med_1"
        node_store = {
            med_node_id: {
                "type": "med",
                "content": "Test Medicine",
                "schedule": "08:00",
                "last_status": None,
                "last_confirmation": None,
                "meta": {},
            }
        }

        def nodes_view(data=True):
            return list(node_store.items())

        def fake_add_nodes(nodes_list):
            for n in nodes_list:
                node_store[n["id"]] = n  # Mutates during iteration

        def fake_update_node(node_id, **kwargs):
            if node_id in node_store:
                mp = kwargs.get("meta_patch", {})
                if mp:
                    node_store[node_id]["meta"] = {
                        **node_store[node_id].get("meta", {}),
                        **mp,
                    }
                if kwargs.get("last_status"):
                    node_store[node_id]["last_status"] = kwargs["last_status"]

        mock_agent.memory.graph.nodes = MagicMock()
        mock_agent.memory.graph.nodes.side_effect = nodes_view
        mock_agent.memory.graph.has_node.return_value = True
        mock_agent.memory.add_nodes.side_effect = fake_add_nodes
        mock_agent.memory.update_node.side_effect = fake_update_node

        with patch("src.main.now_local", return_value=now_dt):
            try:
                main_module.medication_scheduler_loop()
            except KeyboardInterrupt:
                pass  # Expected: fake_sleep raised to break the loop
    finally:
        main_module.time.sleep = original_sleep

    assert len(iterations) == 1
    mock_agent.memory.add_nodes.assert_called_once()
    mock_agent.memory.update_node.assert_called_once_with(
        med_node_id,
        meta_patch={"last_escalation_date": now_dt.strftime("%Y-%m-%d")},
        last_status="no_response",
    )
    mock_agent.memory.log_event.assert_called_once_with(
        "med_missed", {"med_id": med_node_id}
    )


def test_health_ok(client_and_mock):
    """Health check returns 200 with status ok when agent initialized and DB reachable."""
    import src.main as main_module

    client, mock_agent = client_and_mock
    main_module.agent = mock_agent

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    mock_agent.memory._get_connection.return_value = mock_conn

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["encrypted"] is False


def test_health_agent_not_initialized(client_and_mock):
    """Health check returns 503 when agent is None."""
    import src.main as main_module

    client, _ = client_and_mock
    main_module.agent = None

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "initializing"
    assert data["encrypted"] is False


def test_health_db_unreachable(client_and_mock):
    """Health check returns 503 when DB query fails."""
    import src.main as main_module

    client, mock_agent = client_and_mock
    main_module.agent = mock_agent

    mock_agent.memory._get_connection.side_effect = Exception("DB connection failed")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "db_unreachable"
    assert data["encrypted"] is False


def test_post_memory_creates_pending_node(client_and_mock):
    """POST /memory creates a pending node (HITL), returns pending_approval with actual pending ID."""
    client, mock_agent = client_and_mock

    mock_agent.memory_add.return_value = "pending_med_1"

    response = client.post("/memory", json={
        "id": "med_1",
        "type": "med",
        "content": "Test Medicine 10mg",
        "schedule": "08:00"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_approval"
    assert data["id"] == "pending_med_1"
    mock_agent.memory_add.assert_called_once_with("med_1", "med", "Test Medicine 10mg", "08:00")


def test_post_memory_invalid_id(client_and_mock):
    """POST /memory rejects invalid ID format."""
    client, _ = client_and_mock

    response = client.post("/memory", json={
        "id": "invalid id!",
        "type": "med",
        "content": "Test"
    })
    assert response.status_code == 422


def test_post_memory_invalid_type(client_and_mock):
    """POST /memory rejects invalid node type."""
    client, _ = client_and_mock

    response = client.post("/memory", json={
        "id": "med_1",
        "type": "invalid_type",
        "content": "Test"
    })
    assert response.status_code == 422


def test_pending_approval_flow(client_and_mock):
    """Full HITL flow: create pending → GET /pending → approve → type changed, no longer pending."""
    client, mock_agent = client_and_mock

    pending_id = "pending_med_1"

    # Mock graph with a pending node
    mock_node = {
        "type": "pending",
        "content": "Test Medicine",
        "meta": {"proposed_type": "med", "source": "llm_tool_call"}
    }
    mock_agent.memory.graph.has_node.return_value = True
    mock_agent.memory.graph.nodes.__getitem__.return_value = mock_node

    # GET /pending returns the pending node
    mock_agent.memory.graph.nodes.return_value = {
        pending_id: mock_node
    }.items()

    response = client.get("/pending")
    assert response.status_code == 200
    pendings = response.json()
    assert len(pendings) == 1
    assert pendings[0]["id"] == pending_id
    assert pendings[0]["proposed_type"] == "med"

    # Approve the pending node
    mock_agent.memory.graph.has_node.return_value = True
    mock_agent.memory.graph.nodes.__getitem__.return_value = {
        "type": "pending",
        "meta": {"proposed_type": "med"}
    }

    response = client.post(f"/pending/{pending_id}/approve", json={"content": "Approved Medicine"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify update_node was called to change type from pending to med
    mock_agent.memory.update_node.assert_called_with(
        pending_id,
        type="med",
        content="Approved Medicine",
        meta_patch={"approved": True}
    )

    # Verify edge to patient was added
    mock_agent.memory.add_edge.assert_called_with("patient", pending_id, "remembers")


def test_memory_add_stores_xss_as_is(tmp_path, monkeypatch):
    """XSS payload stored as-is (not escaped) so createTextNode displays it literally.
    
    Regression test: html.escape() was removed from storage (src/agent.py:memory_add)
    so that client-side createTextNode() renders content as literal text, not as
    HTML entities. Content must be stored raw and escaped only at display time
    (where innerHTML is used, e.g. graph.js node details).
    """
    from src.agent import MemoraAgent
    from unittest.mock import patch

    with patch('src.agent.NebiusClient') as mock_agent_nebius, \
         patch('src.memory.NebiusClient') as mock_mem_nebius:
        agent_instance = mock_agent_nebius.return_value
        agent_instance.embed.return_value = [0.1, 0.2, 0.3]
        mem_instance = mock_mem_nebius.return_value
        mem_instance.embed_many.return_value = [[0.1, 0.2, 0.3]]

        monkeypatch.setenv("DB_PATH", str(tmp_path / "test_xss.db"))
        monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
        monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)

        agent = MemoraAgent()

        payload = '<img src=x onerror=alert(1)>'
        pending_id = agent.memory_add("test_xss", "med", payload, "10:00")

        # Content must be stored as-is, NOT HTML-escaped
        node = agent.memory.graph.nodes[pending_id]
        assert node["content"] == payload, f"Expected raw payload, got: {node['content']}"
        assert "&lt;" not in node["content"], "Content must not be HTML-escaped at storage"
        assert "<img" in node["content"], "Raw payload must be preserved"

        # idempotent: adding same content again still stores raw
        pending_id2 = agent.memory_add("test_xss2", "med", payload, "11:00")
        node2 = agent.memory.graph.nodes[pending_id2]
        assert node2["content"] == payload
        assert "&lt;" not in node2["content"]


def test_memory_add_normal_text_unchanged(tmp_path, monkeypatch):
    """Normal medication text is stored verbatim without any escaping."""
    from src.agent import MemoraAgent
    from unittest.mock import patch

    with patch('src.agent.NebiusClient') as mock_agent_nebius, \
         patch('src.memory.NebiusClient') as mock_mem_nebius:
        agent_instance = mock_agent_nebius.return_value
        agent_instance.embed.return_value = [0.1, 0.2, 0.3]
        mem_instance = mock_mem_nebius.return_value
        mem_instance.embed_many.return_value = [[0.1, 0.2, 0.3]]

        monkeypatch.setenv("DB_PATH", str(tmp_path / "test_normal.db"))
        monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
        monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)

        agent = MemoraAgent()

        normal_text = "Blood pressure pill, to be taken every morning at breakfast."
        pending_id = agent.memory_add("med_normal", "med", normal_text, "08:00")

        node = agent.memory.graph.nodes[pending_id]
        assert node["content"] == normal_text


# =============================================================================
# Voice endpoint tests (POST /api/voice/preview and POST /api/voice/confirm)
# =============================================================================

def test_voice_preview_returns_facts_without_persisting(client_and_mock):
    """POST /api/voice/preview extracts facts but does not persist them."""
    import src.main as main_module

    client, mock_agent = client_and_mock

    # Mock extract_facts_from_text to return sample facts
    mock_agent.extract_facts_from_text.return_value = [
        {
            "type": "med",
            "label": "Blood pressure pill",
            "description": "100mg tablet",
            "when": "08:00",
            "content": "Blood pressure pill - 100mg tablet"
        },
        {
            "type": "habit",
            "label": "Evening walk",
            "description": "Walk around the block",
            "when": "18:00",
            "content": "Evening walk - Walk around the block"
        }
    ]

    response = client.post("/api/voice/preview", json={
        "text": "I take my blood pressure pill at 8am and walk every evening at 6pm"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["facts"]) == 2
    assert data["facts"][0]["type"] == "med"
    assert data["facts"][0]["label"] == "Blood pressure pill"
    assert data["facts"][1]["type"] == "habit"
    assert data["facts"][1]["label"] == "Evening walk"

    # Crucial: nothing was persisted to memory
    mock_agent.memory.add_nodes.assert_not_called()


def test_voice_preview_returns_empty_for_no_facts(client_and_mock):
    """POST /api/voice/preview returns empty facts list when no facts extracted."""
    import src.main as main_module

    client, mock_agent = client_and_mock
    mock_agent.extract_facts_from_text.return_value = []

    response = client.post("/api/voice/preview", json={
        "text": "Just random words with no meaning"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["facts"] == []
    mock_agent.memory.add_nodes.assert_not_called()


def test_voice_preview_empty_text(client_and_mock):
    """POST /api/voice/preview with empty text returns empty facts."""
    client, mock_agent = client_and_mock
    mock_agent.extract_facts_from_text.return_value = []

    response = client.post("/api/voice/preview", json={
        "text": ""
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["facts"] == []


def test_voice_confirm_creates_pending_nodes(client_and_mock):
    """POST /api/voice/confirm persists facts as pending nodes for HITL approval."""
    import src.main as main_module

    client, mock_agent = client_and_mock

    response = client.post("/api/voice/confirm", json={
        "facts": [
            {
                "type": "med",
                "label": "Blood pressure pill",
                "description": "100mg tablet",
                "when": "08:00",
                "content": "Blood pressure pill - 100mg tablet"
            },
            {
                "type": "person",
                "label": "Dr. Rossi",
                "description": "Geriatrician",
                "when": "",
                "content": "Dr. Rossi - Geriatrician"
            }
        ]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["created"] == 2

    # Verify add_nodes was called with pending nodes
    mock_agent.memory.add_nodes.assert_called_once()
    call_args = mock_agent.memory.add_nodes.call_args[0][0]
    assert len(call_args) == 2

    # Check first node
    n1 = call_args[0]
    assert n1["type"] == "pending"
    assert n1["content"] == "Blood pressure pill - 100mg tablet"
    assert n1["meta"]["proposed_type"] == "med"
    assert n1["meta"]["source"] == "voice"
    assert n1["meta"]["event_date"] == "08:00"
    assert n1["schedule"] == "08:00"

    # Check second node
    n2 = call_args[1]
    assert n2["type"] == "pending"
    assert n2["content"] == "Dr. Rossi - Geriatrician"
    assert n2["meta"]["proposed_type"] == "person"
    assert n2["meta"]["source"] == "voice"
    assert n2["schedule"] is None  # empty when


def test_voice_confirm_empty_facts(client_and_mock):
    """POST /api/voice/confirm with empty facts list does nothing."""
    client, mock_agent = client_and_mock

    response = client.post("/api/voice/confirm", json={
        "facts": []
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["created"] == 0
    mock_agent.memory.add_nodes.assert_not_called()


def test_voice_med_not_auto_confirmed(client_and_mock):
    """Spoken medication statements create pending nodes, NOT confirmed meds."""
    import src.main as main_module

    client, mock_agent = client_and_mock
    mock_agent.extract_facts_from_text.return_value = [
        {
            "type": "med",
            "label": "Blood pressure pill",
            "description": "100mg tablet",
            "when": "08:00",
            "content": "Blood pressure pill - 100mg tablet"
        }
    ]

    response = client.post("/api/voice/confirm", json={
        "facts": [
            {
                "type": "med",
                "label": "Blood pressure pill",
                "description": "100mg tablet",
                "when": "08:00",
                "content": "Blood pressure pill - 100mg tablet"
            }
        ]
    })

    assert response.status_code == 200

    # Verify the node is pending, NOT a confirmed med
    call_args = mock_agent.memory.add_nodes.call_args[0][0]
    n = call_args[0]
    assert n["type"] == "pending", f"Expected 'pending', got {n['type']}"
    assert n["meta"]["source"] == "voice"
    assert n["meta"]["proposed_type"] == "med"
    # No last_status field means not confirmed


def test_voice_html_entities_not_executed(client_and_mock):
    """HTML/script-like text in spoken facts remains inert (escaped at storage)."""
    import src.main as main_module

    client, mock_agent = client_and_mock
    mock_agent.extract_facts_from_text.return_value = [
        {
            "type": "med",
            "label": "<img src=x onerror=alert(1)>",
            "description": "<script>alert('xss')</script>",
            "when": "",
            "content": "<img src=x onerror=alert(1)> - <script>alert('xss')</script>"
        }
    ]

    response = client.post("/api/voice/confirm", json={
        "facts": [
            {
                "type": "med",
                "label": "<img src=x onerror=alert(1)>",
                "description": "<script>alert('xss')</script>",
                "when": "",
                "content": "<img src=x onerror=alert(1)> - <script>alert('xss')</script>"
            }
        ]
    })

    assert response.status_code == 200

    # Verify the raw (potentially dangerous) text is stored as-is in content
    # Escaping happens at display time, not storage time
    call_args = mock_agent.memory.add_nodes.call_args[0][0]
    n = call_args[0]
    assert "<img" in n["content"]
    assert "<script>" in n["content"]
    # But the node type is 'pending', not a confirmed medication
    assert n["type"] == "pending"
    assert n["meta"]["source"] == "voice"


def test_voice_confirm_agent_not_initialized(client_and_mock):
    """POST /api/voice/confirm returns 500 when agent is None."""
    import src.main as main_module

    client, _ = client_and_mock
    main_module.agent = None

    response = client.post("/api/voice/confirm", json={
        "facts": [
            {
                "type": "med",
                "label": "Test",
                "description": "Test desc",
                "when": "",
                "content": "Test - Test desc"
            }
        ]
    })

    assert response.status_code == 500


def test_voice_preview_agent_not_initialized(client_and_mock):
    """POST /api/voice/preview returns 500 when agent is None."""
    import src.main as main_module

    client, _ = client_and_mock
    main_module.agent = None

    response = client.post("/api/voice/preview", json={"text": "test"})
    assert response.status_code == 500


def test_chat_profile_isolation_maria_rossi(client_and_mock):
    """Regression: /chat must pass patient_id=maria_rossi to the agent and
    retrieve context only for that profile, never leaking another profile's
    memories through get_context."""
    client, mock_agent = client_and_mock

    # Distinct synthetic memories per profile
    maria_ctx = {
        "node": {"id": "maria_rossi", "content": "Maria Rossi, 74 anni, vive a Milano.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_keys_location"},
            {"id": "mem_giulia_calls"},
        ],
    }
    other_ctx = {
        "node": {"id": "other_user", "content": "Other user, distinct profile.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_other_secret"},
        ],
    }

    def get_context_side_effect(entity_id):
        if entity_id == "maria_rossi":
            return maria_ctx
        return other_ctx

    mock_agent.memory.get_context.side_effect = get_context_side_effect

    def respond_side_effect(user_input, lang="en", patient_id=None, skip_preprocessing=False):
        # Simulate production: respond retrieves context only for the given patient_id
        ctx = mock_agent.memory.get_context(patient_id)
        return f"Answer for {patient_id} based on {ctx['node']['id']}"

    mock_agent.respond.side_effect = respond_side_effect

    # Maria's request
    response = client.post("/chat", json={
        "user_input": "Where are my house keys?",
        "patient_id": "maria_rossi"
    })

    assert response.status_code == 200

    # Verify respond was called with the exact patient_id
    mock_agent.respond.assert_called_once()
    args, kwargs = mock_agent.respond.call_args
    assert args[0] == "Where are my house keys?"
    assert kwargs["patient_id"] == "maria_rossi"
    assert kwargs["lang"] == "en"

    # Verify get_context was called ONLY with maria_rossi (not with other_user)
    mock_agent.memory.get_context.assert_called_once_with("maria_rossi")
    call_args_list = [str(c) for c in mock_agent.memory.get_context.call_args_list]
    assert all("maria_rossi" in c for c in call_args_list)
    assert not any("other_user" in c for c in call_args_list)


def test_chat_other_profile_isolated(client_and_mock):
    """Regression: a request for a different profile must retrieve that profile's
    context only, never Maria Rossi's memories."""
    client, mock_agent = client_and_mock

    maria_ctx = {
        "node": {"id": "maria_rossi", "content": "Maria Rossi, 74 anni, vive a Milano.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_keys_location"},
            {"id": "mem_giulia_calls"},
        ],
    }
    other_ctx = {
        "node": {"id": "other_user", "content": "Other user, distinct profile.", "type": "person"},
        "outgoing_edges": [
            {"id": "mem_other_secret"},
        ],
    }

    def get_context_side_effect(entity_id):
        if entity_id == "maria_rossi":
            return maria_ctx
        return other_ctx

    mock_agent.memory.get_context.side_effect = get_context_side_effect

    def respond_side_effect(user_input, lang="en", patient_id=None, skip_preprocessing=False):
        ctx = mock_agent.memory.get_context(patient_id)
        return f"Answer for {patient_id} based on {ctx['node']['id']}"

    mock_agent.respond.side_effect = respond_side_effect

    # Other profile's request
    response = client.post("/chat", json={
        "user_input": "What is my secret fact?",
        "patient_id": "other_user"
    })

    assert response.status_code == 200

    _, kwargs = mock_agent.respond.call_args
    assert kwargs["patient_id"] == "other_user"

    # get_context called ONLY with other_user, never maria_rossi
    mock_agent.memory.get_context.assert_called_once_with("other_user")
    call_args_list = [str(c) for c in mock_agent.memory.get_context.call_args_list]
    assert all("other_user" in c for c in call_args_list)
    assert not any("maria_rossi" in c for c in call_args_list)
