"""
Regression tests for bugs found during the repository review.

These tests use a REAL MemoryGraph (only the embedding network call is mocked): the previous
suite mocked the whole agent, which is why these bugs went unnoticed.
"""
import os
import time
import json
import pytest
from unittest.mock import patch

from src.memory import MemoryGraph


@pytest.fixture
def graph(tmp_path):
    with patch("src.memory.NebiusClient") as mock_client:
        inst = mock_client.return_value
        inst.embed.return_value = [0.1, 0.2, 0.3]
        inst.embed_many.side_effect = lambda texts: [[0.1, 0.2, 0.3] for _ in texts]
        g = MemoryGraph(db_path=str(tmp_path / "t.db"), db_key="k" * 32)
        g._embed_mock = inst
        yield g


# ---------------------------------------------------------------- update_node
def test_update_node_rejects_non_string_type(graph):
    """update_node(id, {...}) used to put a dict into node['type'] and corrupt the med."""
    graph.add_node("med1", "med", "Memantina 20mg", schedule="08:00")
    with pytest.raises(TypeError):
        graph.update_node("med1", {"meta": {"x": 1}})
    assert graph.graph.nodes["med1"]["type"] == "med"


def test_update_node_meta_patch_and_status_persist(graph):
    graph.add_node("med1", "med", "Memantina 20mg", schedule="08:00")
    graph.update_node("med1", meta_patch={"last_escalation_date": "2026-10-06"}, last_status="no_response")
    node = graph.graph.nodes["med1"]
    assert node["type"] == "med"
    assert node["meta"]["last_escalation_date"] == "2026-10-06"
    assert node["last_status"] == "no_response"

    # reload from disk: everything must have been persisted
    with patch("src.memory.NebiusClient"):
        g2 = MemoryGraph(db_path=graph.db_path, db_key="k" * 32)
    reloaded = g2.graph.nodes["med1"]
    assert reloaded["type"] == "med"
    assert reloaded["meta"]["last_escalation_date"] == "2026-10-06"
    assert reloaded["last_status"] == "no_response"


def test_approve_pending_changes_type(graph):
    graph.add_nodes([{"id": "p1", "type": "pending", "content": "Luca e il nipote",
                      "meta": {"proposed_type": "person"}}])
    graph.update_node("p1", type="person", content="Luca e il nipote", meta_patch={"approved": True})
    assert graph.graph.nodes["p1"]["type"] == "person"
    assert graph.graph.nodes["p1"]["meta"]["proposed_type"] == "person"  # old meta kept


def test_add_node_preserves_meta(graph):
    graph.add_node("patient", "person", "Maria", meta={"name": "Maria"})
    graph.add_node("patient", "person", "Maria, 68 anni")
    assert graph.graph.nodes["patient"]["meta"] == {"name": "Maria"}


# ---------------------------------------------------------------- alerts
def test_alert_nodes_skip_embedding_and_stay_out_of_search(graph):
    graph._embed_mock.embed_many.reset_mock()
    graph.add_nodes([{"id": "sos_1", "type": "alert", "content": "SOS from maria", "skip_embedding": True,
                      "meta": {"status": "open"}}])
    graph._embed_mock.embed_many.assert_not_called()
    graph.add_node("fact1", "fact", "Maria vive a Milano")
    ids = [r["id"] for r in graph.search("SOS", top_k=10, query_embedding=[0.1, 0.2, 0.3])]
    assert "sos_1" not in ids and "fact1" in ids


def test_export_graph_exposes_alert_status(graph):
    graph.add_nodes([{"id": "sos_1", "type": "alert", "content": "SOS", "skip_embedding": True,
                      "meta": {"status": "open"}}])
    node = next(n for n in graph.export_graph()["nodes"] if n["id"] == "sos_1")
    assert node["status"] == "open" and "timestamp" in node


# ---------------------------------------------------------------- stats
def test_stats_count_the_events_that_the_app_really_logs(graph):
    for kind in ["interaction", "interaction", "repeat_flag", "confusion_flag", "sos",
                 "med_confirmed", "med_missed", "med_denied", "med_unsure", "diary_turn"]:
        graph.log_event(kind)
    totals = graph.get_stats(7)["totals"]
    assert totals["interactions"] == 2
    assert totals["repeats"] == 1
    assert totals["confusion"] == 1
    assert totals["sos"] == 1
    assert totals["meds_confirmed"] == 1
    assert totals["meds_missed"] == 2      # missed + denied
    assert totals["meds_unsure"] == 1
    assert totals["diary_turns"] == 1


def test_demo_seed_ships_simulated_history_and_no_test_leftovers():
    from src.seed_overlay import apply_overlay
    raw = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "seed_demo.json")))
    seed = apply_overlay(raw)
    ids = [n["id"] for n in seed["nodes"]]
    assert seed["events"], "the demo seed must include simulated history, otherwise the report charts are empty"
    assert all(e.get("simulated") == 1 for e in seed["events"])
    assert "med_test" not in ids and "maria_utente" not in ids and ids.count("patient") == 1
    node = {n["id"]: n for n in seed["nodes"]}
    assert node["patient"]["meta"]["name"] == "Maria"
    assert node["pillola_pressione"]["schedule"] == "08:00"
    assert all(e["source"] in ids and e["target"] in ids for e in seed["edges"])
    for n in seed["nodes"]:
        assert n.get("embedding"), f"seed node {n['id']} has no embedding"
