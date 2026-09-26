from dotenv import load_dotenv
from src.agent import MemoraAgent
from src.memory import MemoryGraph
from src.nebius_client import NebiusClient
from src.tavily_tool import TavilyTool
import time

load_dotenv()

agent = MemoraAgent()
# To get usage, we can access agent.nebius
client = agent.nebius

# Test 1: dialogo semplice con system prompt
print("=== Test A: dialogo confuso ===")
t0 = time.time()
r = agent.respond("Mi chiamo Maria e non ricordo dove ho messo le chiavi.")
t1 = time.time()
print(r)
print(f"Latenza A: {t1 - t0:.2f}s\n")

# Test 2: intento rapido
print("=== Test B: quick_intent ===")
t0 = time.time()
intent = agent.quick_intent("Ciao, come stai?")
t1 = time.time()
print(intent)
print(f"Latenza B: {t1 - t0:.2f}s\n")

print("=== Usage ===")
print(client.get_usage())
