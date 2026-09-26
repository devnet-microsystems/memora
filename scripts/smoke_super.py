from dotenv import load_dotenv
from src.nebius_client import NebiusClient
import time

load_dotenv()
client = NebiusClient()

t0 = time.time()
r = client.respond("Mi chiamo Maria e non ricordo dove ho messo le chiavi.")
t1 = time.time()

print("Risposta:")
print(r)
print()
print(f"Latenza: {t1 - t0:.2f}s")
print(client.get_usage())
