from dotenv import load_dotenv
from src.nebius_client import NebiusClient

load_dotenv()
client = NebiusClient()
r = client.quick_intent("Rispondi solo con: OK")
print(r)
print(client.get_usage())
