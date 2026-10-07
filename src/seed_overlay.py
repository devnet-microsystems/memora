"""Clean-up applied to the pre-computed demo seed (data/seed_demo.json) when it is loaded.

The seed file contains expensive pre-computed embeddings that can only be regenerated with a live API key,
so fixes to its *content* are applied here instead:
  * drop leftover test nodes and the duplicate patient node,
  * give the demo medication / habit a schedule so the patient "Today" card and the med scheduler have something to show,
  * attach one simulated week of activity (flagged simulated=1) so the weekly report and charts are never empty.
"""
from typing import Any, Dict

from src.demo_events import demo_events

DROP_NODES = {"med_test"}
RENAME_NODES = {"maria_utente": "patient"}          # the seed had two patient nodes
NODE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "pillola_pressione": {"schedule": "08:00"},
    "passeggiata_parco": {"schedule": "10:30"},
    "patient": {"meta": {"name": "Maria"}},
}


def apply_overlay(seed: Dict[str, Any]) -> Dict[str, Any]:
    nodes = {}
    for node in seed.get("nodes", []):
        node = dict(node)
        node_id = RENAME_NODES.get(node["id"], node["id"])
        if node["id"] in DROP_NODES or node_id in DROP_NODES:
            continue
        if node_id in nodes:                           # duplicate after renaming: keep the first (the real "patient")
            continue
        node["id"] = node_id
        node.update(NODE_OVERRIDES.get(node_id, {}))
        nodes[node_id] = node

    edges, seen = [], set()
    for edge in seed.get("edges", []):
        edge = dict(edge)
        edge["source"] = RENAME_NODES.get(edge["source"], edge["source"])
        edge["target"] = RENAME_NODES.get(edge["target"], edge["target"])
        if edge["source"] not in nodes or edge["target"] not in nodes:
            continue
        key = (edge["source"], edge["target"], edge["relation"])
        if key not in seen:
            seen.add(key)
            edges.append(edge)

    out = dict(seed)
    out["nodes"], out["edges"] = list(nodes.values()), edges
    if "patient" in nodes and not out.get("events"):   # only the Maria demo seed gets the simulated week
        out["events"] = demo_events()
    return out
