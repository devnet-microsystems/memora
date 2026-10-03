import sys
sys.path.append('/workspace/NvidiaHackaton')
from src.tavily_tool import TavilyTool
tavily = TavilyTool()
print(tavily.extract("http://localtest.me"))
