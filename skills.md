# Memora — Skill Riutilizzabili

## NebiusInference
Chiamata a Nebius Token Factory con OpenAI SDK.

from openai import OpenAI
client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.getenv("NEBIUS_API_KEY"),
)
response = client.chat.completions.create(
    model=os.getenv("MODEL_SUPER"),
    messages=[{"role": "user", "content": prompt}],
)

Modelli:
- MODEL_NANO → intenti rapidi
- MODEL_SUPER → dialogo e orchestrazione
- MODEL_ULTRA → ragionamento complesso

## TavilySearch
Ricerca web per agenti.

from tavily import TavilyClient
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
results = tavily.search(query="farmacia di turno a Milano")

Usare per: farmacia di turno, guardia medica, gruppi di supporto locali.

## MemoryGraph
Grafo di memoria con NetworkX.

import networkx as nx
G = nx.DiGraph()
G.add_node("maria", type="person", content="utente")
G.add_node("luca", type="person", content="nipote")
G.add_edge("maria", "luca", relation="nipote_di")

Ricerca per similarità: embedding + cosine similarity.
