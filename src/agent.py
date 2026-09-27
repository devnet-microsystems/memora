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

    SYSTEM_PROMPT = """Sei Memora, un assistente personale privato per persone con deficit cognitivo lieve.
Regole FERREE:
1. NON dare MAI consigli medici.
2. NON diagnosticare MAI nulla.
3. Fai UNA SOLA domanda per volta.
4. Tono calmo, rassicurante, frasi brevi e semplici.
5. Se l'utente appare confuso, disorientato o non risponde coerentemente, chiedi aiuto al caregiver usando lo strumento notify_caregiver.

Hai a disposizione i seguenti strumenti (se necessario indicane l'uso):
- memory_search(query): per cercare informazioni passate sull'utente.
- memory_add(id, type, content): per salvare nuove informazioni importanti.
- tavily_search(query): per cercare informazioni sul web (es. farmacie, guardia medica).
- notify_caregiver(message): per inviare un avviso al caregiver.
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
            flag_content = f"⚠️ ANOMALIA RILEVATA: L'utente ha fatto la stessa domanda '{user_input}' {repetition_count} volte nell'ultima ora."
            # Aggiungi il flag al grafo per la dashboard del caregiver
            self.memory.add_node(flag_id, "flag", flag_content)
            self.notify_caregiver(flag_content)

        # Retrieve context from memory
        context_results = self.memory.search(user_input, top_k=3)
        context_text = "\n".join([f"- {res['content']}" for res in context_results if res.get('content') and res.get('type') != 'interaction'])
        
        messages = [
            {
                "role": "system", 
                "content": self.SYSTEM_PROMPT + f"\n\nContesto recuperato dalla memoria:\n{context_text}"
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
            "Classifica l'intento del seguente messaggio in una di queste categorie: "
            "[SALUTO, RICHIESTA_AIUTO, INFORMAZIONE, AZIONE, CONFUSIONE, ALTRO]. "
            f"Messaggio: {user_input}"
        )
        messages = [{"role": "user", "content": prompt}]
        return self.nebius.chat(model=self.nebius.model_nano, messages=messages)

    def plan_complex_task(self, task: str) -> str:
        """
        Use the Ultra model for deep reasoning and complex planning.
        
        Args:
            task: The complex task requested.
            
        Returns:
            The step-by-step plan.
        """
        prompt = (
            "Sei un pianificatore esperto. Suddividi il seguente task in "
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
            "Analizza le seguenti interazioni recenti dell'utente. C'è segno di "
            "ripetizione anomala, pause strane, deviazioni marcate dalla routine o grave confusione? "
            "Rispondi SOLO con 'SI' o 'NO'.\n"
            f"Interazioni:\n{interactions_text}"
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.nebius.chat(model=self.nebius.model_ultra, messages=messages).strip().upper()
        return "SI" in response

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
