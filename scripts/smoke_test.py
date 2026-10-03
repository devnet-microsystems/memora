"""
Smoke test minimo per Memora.
Esegui SOLO con crediti attivi. Costo stimato: meno di $0.05.
"""
import os
import time
from dotenv import load_dotenv
from src.nebius_client import NebiusClient
from src.tavily_tool import TavilyTool

load_dotenv()


def main():
    client = NebiusClient()
    tavily = TavilyTool()

    # Test 1: Nano (economico)
    print("\n=== Test 1: Nano (quick_intent) ===")
    t0 = time.time()
    r = client.quick_intent("Ciao, come stai?")
    print(f"Risposta: {r[:150]}")
    print(f"Latenza: {time.time() - t0:.2f}s")

    # Test 2: Super (dialogo)
    print("\n=== Test 2: Super (respond) ===")
    t0 = time.time()
    r = client.respond("Mi chiamo Maria e non ricordo dove ho messo le chiavi.")
    print(f"Risposta: {r[:300]}")
    print(f"Latenza: {time.time() - t0:.2f}s")

    # Test 3: Embedding
    print("\n=== Test 3: Embedding ===")
    t0 = time.time()
    v = client.embed("Maria è mia nonna")
    print(f"Dimensioni vettore: {len(v)}")
    print(f"Latenza: {time.time() - t0:.2f}s")

    # Test 4: Tavily
    print("\n=== Test 4: Tavily ===")
    t0 = time.time()
    try:
        results = tavily.find_pharmacy("Milano")
        print(f"Risultati: {len(results)}")
        if results:
            print(f"Primo: {results[0]}")
    except Exception as e:
        print(f"Errore Tavily: {e}")
    print(f"Latenza: {time.time() - t0:.2f}s")

    # Report finale
    print("\n" + "=" * 50)
    usage = client.get_usage()
    print(f"Chiamate totali: {usage['calls']}")
    print(f"Token input: {usage['input_tokens']}")
    print(f"Token output: {usage['output_tokens']}")
    print(f"Costo stimato: ${usage['estimated_cost_usd']:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
