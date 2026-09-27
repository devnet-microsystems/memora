"""
Core AI Agent for Memora.
Orchestrates the interaction between the LLM, memory, and tools.
"""

import logging
from typing import List, Dict, Any
from src.nebius_client import NebiusClient
from src.memory import MemoryGraph
from src.tavily_tool import TavilyTool

logger = logging.getLogger("memora.agent")

class MemoraAgent:
    """
    Main agent coordinating dialogue, memory, and external tools.
    """

    SYSTEM_PROMPT = """You are Memora, a private personal assistant for people with mild cognitive impairment.
STRICT Rules:
1. NEVER give medical advice.
2. NEVER diagnose anything.
3. Ask ONLY ONE question at a time.
4. Keep a calm, reassuring tone, with short and simple sentences.
5. If the user seems confused, disoriented, or responds incoherently, ask the caregiver for help using the notify_caregiver tool.

You have the following tools available (indicate their use if necessary):
- memory_search(query): to search past information about the user.
- memory_add(id, type, content): to save new important information.
- tavily_search(query): to search information on the web (e.g. pharmacies, medical guards).
- notify_caregiver(message): to send an alert to the caregiver.
"""

    def __init__(self) -> None:
        """Initialize the agent with its dependencies."""
        self.nebius = NebiusClient()
        self.memory = MemoryGraph()
        self.tavily = TavilyTool()

    def respond(self, user_input: str) -> str:
        """
        Process user input and generate a dialogue response using the Super model.
        Retrieves context from memory before responding.
        
        Args:
            user_input: The text spoken/typed by the user.
            
        Returns:
            The agent's text response.
        """
        import time
        # 1. Log interaction
        interaction_id = f"interaction_{int(time.time()*1000)}"
        self.memory.add_node(interaction_id, "interaction", user_input)
        
        # 2. Check for anomaly (repetitive questions)
        repetition_count = self.memory.count_recent_similar_interactions(user_input, time_window_seconds=3600, similarity_threshold=0.85)
        if repetition_count >= 3:
            flag_id = f"flag_{int(time.time()*1000)}"
            flag_content = f"⚠️ ANOMALY DETECTED: The user asked the same question '{user_input}' {repetition_count} times in the last hour."
            # Aggiungi il flag al grafo per la dashboard del caregiver
            self.memory.add_node(flag_id, "flag", flag_content)
            self.notify_caregiver(flag_content)

        # 3. Extract potential new facts as 'pending' using Nano
        self._extract_pending_fact(user_input)

        # Retrieve context from memory
        context_results = self.memory.search(user_input, top_k=3)
        context_text = "\n".join([f"- {res['content']}" for res in context_results if res.get('content') and res.get('type') not in ['interaction', 'pending']])
        
        messages = [
            {
                "role": "system", 
                "content": self.SYSTEM_PROMPT + f"\n\nContext retrieved from memory:\n{context_text}"
            },
            {"role": "user", "content": user_input}
        ]
        
        # PII is automatically redacted inside NebiusClient
        response = self.nebius.chat(model=self.nebius.model_super, messages=messages)
        
        # Note: A full tool-calling implementation would parse the response here 
        # to execute functions like memory_search or notify_caregiver automatically.
        return response

    def quick_intent(self, user_input: str) -> str:
        """
        Classify the user's intent quickly using the Nano model.
        
        Args:
            user_input: The user's input.
            
        Returns:
            The classified intent as a string.
        """
        prompt = (
            "Classify the intent of the following message into one of these categories: "
            "[GREETING, HELP_REQUEST, INFORMATION, ACTION, CONFUSION, OTHER]. "
            f"Message: {user_input}"
        )
        messages = [{"role": "user", "content": prompt}]
        return self.nebius.chat(model=self.nebius.model_nano, messages=messages)

    def _extract_pending_fact(self, user_input: str) -> None:
        """
        Extracts new factual information from the user input.
        If a new fact is found, saves it as a 'pending' node for caregiver approval.
        """
        import time
        prompt = (
            "If the following sentence contains personal information or a fact to remember "
            "(e.g., I have a new pain, my nephew is named Marco, I changed my schedule), "
            "extract a single synthetic fact. If it does not contain new or relevant facts (e.g. greetings, "
            "routine questions, thanks), answer EXACTLY with 'NONE'.\n"
            f"Sentence: {user_input}"
        )
        try:
            messages = [{"role": "user", "content": prompt}]
            fact = self.nebius.chat(model=self.nebius.model_nano, messages=messages).strip()
            if fact and "NONE" not in fact.upper() and len(fact) > 5:
                fact_id = f"pending_{int(time.time()*1000)}"
                self.memory.add_node(fact_id, "pending", fact)
        except Exception as e:
            logger.error(f"Error extracting fact: {e}")

    def plan_complex_task(self, task: str) -> str:
        """
        Use the Ultra model for deep reasoning and complex planning.
        
        Args:
            task: The complex task requested.
            
        Returns:
            The step-by-step plan.
        """
        prompt = (
            "You are an expert planner. Break down the following task into "
            f"sotto-obiettivi semplici e sicuri per l'utente.\nTask: {task}"
        )
        messages = [{"role": "user", "content": prompt}]
        return self.nebius.chat(model=self.nebius.model_ultra, messages=messages)

    def check_anomaly(self, recent_interactions: List[str]) -> bool:
        """
        Detect anomalous patterns in recent interactions (e.g. repetitions, confusion).
        
        Args:
            recent_interactions: List of recent user messages.
            
        Returns:
            True if an anomaly is detected, False otherwise.
        """
        if not recent_interactions:
            return False
            
        interactions_text = "\n".join(recent_interactions)
        prompt = (
            "Analyze the following recent interactions of the user. Is there a sign of "
            "anomalous repetition, strange pauses, marked deviations from the routine or severe confusion? "
            "Answer ONLY with 'YES' or 'NO'.\n"
            f"Interactions:\n{interactions_text}"
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.nebius.chat(model=self.nebius.model_ultra, messages=messages).strip().upper()
        return "YES" in response

    # --- Tool Implementations for Function Calling ---

    def memory_search(self, query: str) -> List[Dict[str, Any]]:
        """Tool: Search the memory graph."""
        return self.memory.search(query)

    def memory_add(self, node_id: str, node_type: str, content: str) -> bool:
        """Tool: Add a new node to the memory graph."""
        self.memory.add_node(node_id, node_type, content)
        return True

    def tavily_search(self, query: str) -> List[Dict[str, str]]:
        """Tool: Search the web via Tavily."""
        return self.tavily.search(query)

    def notify_caregiver(self, message: str) -> bool:
        """Tool: Notify the caregiver."""
        logger.warning(f"*** CAREGIVER NOTIFIED: {message} ***")
        return True
