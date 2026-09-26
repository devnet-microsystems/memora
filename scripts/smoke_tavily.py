from dotenv import load_dotenv
from src.tavily_tool import TavilyTool
import time

load_dotenv()
tavily = TavilyTool()

t0 = time.time()
results = tavily.find_pharmacy("Milano")
t1 = time.time()

print(f"Risultati: {len(results)}")
for r in results[:3]:
    print(f"- {r.get('title')}")
    print(f"  {r.get('url')}")
    print(f"  {r.get('snippet', '')[:120]}")
    print()

print(f"Latenza: {t1 - t0:.2f}s")
