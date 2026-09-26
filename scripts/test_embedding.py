from dotenv import load_dotenv
from src.nebius_client import NebiusClient
import time

load_dotenv()
client = NebiusClient()

frasi = [
    "Maria è mia nonna",
    "Luca è mio nipote",
    "La farmacia è aperta fino alle 20",
]

t0 = time.time()
for f in frasi:
    v = client.embed(f)
    print(f"{f} -> dim={len(v)}")

t1 = time.time()
print(f"Latenza totale: {t1 - t0:.2f}s")
print()
print(client.get_usage())
