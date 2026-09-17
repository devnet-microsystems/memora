"""
Tavily Web Search Tool for Memora.
Provides the agent with web search capabilities.
"""

import os
import logging
import concurrent.futures
from typing import List, Dict
from dotenv import load_dotenv
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

# Setup logger
logger = logging.getLogger("memora.tavily")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )

class TavilyTool:
    """Web search capabilities using Tavily API."""

    def __init__(self) -> None:
        """Initialize the TavilyClient."""
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY is not set. Web searches will fail.")
        
        self.client = TavilyClient(api_key=self.api_key) if self.api_key else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Execute a web search using Tavily with a strict 10s timeout.
        
        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries with 'title', 'url', and 'snippet'.
        """
        if not self.client:
            logger.error("TavilyClient is not initialized. Cannot perform search.")
            return []

        logger.info(f"Searching web for: {query}")
        try:
            # Enforce 10 seconds timeout via ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self.client.search, 
                    query=query, 
                    max_results=max_results,
                    search_depth="basic"
                )
                response = future.result(timeout=10.0)
            
            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", "")
                })
            return results
        except concurrent.futures.TimeoutError:
            logger.error(f"Search timed out after 10 seconds for query '{query}'")
            raise
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

    def find_pharmacy(self, location: str) -> List[Dict[str, str]]:
        """
        Find an open pharmacy near the specified location.
        """
        query = f"farmacia di turno vicino a {location}"
        return self.search(query, max_results=3)

    def find_guardia_medica(self, location: str) -> List[Dict[str, str]]:
        """
        Find local guardia medica (emergency medical service) contacts.
        """
        query = f"guardia medica contatti e orari a {location}"
        return self.search(query, max_results=3)

    def find_support_group(self, topic: str, location: str) -> List[Dict[str, str]]:
        """
        Find local support groups for a specific topic (e.g., Alzheimer, caregiver).
        """
        query = f"gruppi di supporto {topic} a {location}"
        return self.search(query, max_results=4)
