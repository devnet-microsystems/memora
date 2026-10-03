"""
Nebius Token Factory API Client.
Handles communication with Nebius OpenAI-compatible endpoints using NVIDIA Nemotron models.
Ensures prompts are redacted for privacy before sending.
"""

import os
import re
import logging
from typing import List, Dict, Iterator, Any
def load_dotenv(): pass
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

# Setup logging configuration
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
logger = logging.getLogger("memora.nebius")


class NebiusClient:
    """Client for interacting with Nebius Token Factory APIs."""

    def __init__(self) -> None:
        """Initialize the OpenAI SDK with Nebius configuration."""
        self.api_key = os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            logger.warning("NEBIUS_API_KEY is not set. API calls will fail.")

        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=self.api_key or "dummy_key_to_prevent_startup_crash",
        )

        self.model_nano = os.getenv("MODEL_NANO", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
        self.model_super = os.getenv("MODEL_SUPER", "nvidia/nemotron-3-super-120b-a12b")
        self.model_ultra = os.getenv("MODEL_ULTRA", "nvidia/Nemotron-3-Ultra-550b-a55b")
        # Default embedding model if not specified in .env
        self.model_embed = os.getenv("MODEL_EMBEDDING", "Qwen/Qwen3-Embedding-8B")
        
        # Track usage statistics for current session
        self._usage = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "latency_by_model": {}
        }
        self._embed_cache = {}
        self._cache_max_size = 256
        
    def _update_latency(self, model: str, duration_ms: float):
        if model not in self._usage["latency_by_model"]:
            self._usage["latency_by_model"][model] = {"calls": 0, "total_ms": 0, "last_ms": 0, "avg_ms": 0}
            
        m_stat = self._usage["latency_by_model"][model]
        m_stat["calls"] += 1
        m_stat["total_ms"] += duration_ms
        m_stat["last_ms"] = duration_ms
        m_stat["avg_ms"] = m_stat["total_ms"] / m_stat["calls"]

    def _redact(self, text: str) -> str:
        """
        Redact PII from text before sending to Nebius.
        Very basic regex-based version for now.
        
        Args:
            text: The original text.
            
        Returns:
            The redacted text.
        """
        # Phone numbers: basic pattern
        text = re.sub(r'\+?\d{2,3}[\s-]?\d{3}[\s-]?\d{4,6}', '[PHONE]', text)
        # Email addresses
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
        # Fiscal codes (Codice Fiscale)
        text = re.sub(r'[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]', '[CF REDACTED]', text, flags=re.IGNORECASE)
        # Dates of birth (DD/MM/YYYY)
        text = re.sub(r'\b(0[1-9]|[12][0-9]|3[01])[-/.](0[1-9]|1[012])[-/.](19|20)\d\d\b', '[DOB]', text)
        
        return text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Send a chat completion request to the specified model.
        
        Args:
            model: The model ID to use.
            messages: List of message dictionaries.
            temperature: Sampling temperature.
            
        Returns:
            The text response from the model.
        """
        logger.info(f"Sending chat request to {model}")
        redacted_messages = [
            {**msg, "content": self._redact(msg["content"])} if "content" in msg else msg
            for msg in messages
        ]
        
        import time
        start_time = time.time()
        response = self.client.chat.completions.create(
            model=model,
            messages=redacted_messages,
            temperature=temperature
        )
        duration_ms = (time.time() - start_time) * 1000
        self._update_latency(model, duration_ms)
        
        # Track usage
        self._usage["calls"] += 1
        if hasattr(response, 'usage') and response.usage:
            in_tok = response.usage.prompt_tokens
            out_tok = response.usage.completion_tokens
            self._usage["input_tokens"] += in_tok
            self._usage["output_tokens"] += out_tok
            # Rough estimation (e.g. $1 per 1M input tokens, $2 per 1M output tokens)
            cost = (in_tok * 0.000001) + (out_tok * 0.000002)
            self._usage["estimated_cost_usd"] += cost
            logger.info(f"TOKEN_USAGE | model={model} | in={in_tok} | out={out_tok} | cost=${cost:.6f}")

        return response.choices[0].message.content or ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat_stream(self, model: str, messages: List[Dict[str, str]]) -> Iterator[str]:
        """
        Stream a chat completion response from the specified model.
        
        Args:
            model: The model ID to use.
            messages: List of message dictionaries.
            
        Yields:
            Chunks of text from the stream.
        """
        logger.info(f"Starting chat stream from {model}")
        redacted_messages = [
            {**msg, "content": self._redact(msg["content"])} if "content" in msg else msg
            for msg in messages
        ]
        
        response = self.client.chat.completions.create(
            model=model,
            messages=redacted_messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def quick_intent(self, user_input: str) -> str:
        """
        Process a quick intent using the Nano model.
        
        Args:
            user_input: The user's input text.
            
        Returns:
            The intent analysis response.
        """
        messages = [{"role": "user", "content": user_input}]
        return self.chat(model=self.model_nano, messages=messages)

    def respond(self, user_input: str) -> str:
        """
        Generate a dialogue response using the Super model.
        
        Args:
            user_input: The user's input text.
            
        Returns:
            The generated dialogue response.
        """
        messages = [{"role": "user", "content": user_input}]
        return self.chat(model=self.model_super, messages=messages)

    def plan(self, task: str) -> str:
        """
        Create a complex plan using the Ultra model.
        
        Args:
            task: The complex task to plan.
            
        Returns:
            The detailed plan from the model.
        """
        messages = [{"role": "user", "content": task}]
        return self.chat(model=self.model_ultra, messages=messages)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text.
        
        Args:
            text: The text to embed.
            
        Returns:
            The embedding vector.
        """
        logger.info("Generating embedding")
        redacted_text = self._redact(text)
        if redacted_text in self._embed_cache:
            return self._embed_cache[redacted_text]

        import time
        start_time = time.time()
        response = self.client.embeddings.create(
            model=self.model_embed,
            input=redacted_text
        )
        duration_ms = (time.time() - start_time) * 1000
        self._update_latency(self.model_embed, duration_ms)
        
        # Track usage
        self._usage["calls"] += 1
        if hasattr(response, 'usage') and response.usage:
            in_tok = response.usage.prompt_tokens
            cost = (in_tok * 0.0000001)
            self._usage["input_tokens"] += in_tok
            self._usage["estimated_cost_usd"] += cost
            logger.info(f"TOKEN_USAGE | model={self.model_embed} | in={in_tok} | out=0 | cost=${cost:.6f}")
            
        emb = response.data[0].embedding
        if len(self._embed_cache) >= self._cache_max_size:
            self._embed_cache.pop(next(iter(self._embed_cache)))
        self._embed_cache[redacted_text] = emb
        return emb

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        Uses chunks of 16. Fallbacks to parallel single embed on failure.
        """
        if not texts:
            return []
            
        redacted_texts = [self._redact(t) for t in texts]
        results = [None] * len(texts)
        missing_indices = []
        missing_texts = []
        
        for i, text in enumerate(redacted_texts):
            if text in self._embed_cache:
                results[i] = self._embed_cache[text]
            else:
                missing_indices.append(i)
                missing_texts.append(text)
                
        if not missing_texts:
            return results
            
        chunk_size = 16
        for i in range(0, len(missing_texts), chunk_size):
            chunk = missing_texts[i:i + chunk_size]
            chunk_indices = missing_indices[i:i + chunk_size]
            
            try:
                logger.info(f"Generating embeddings for chunk of {len(chunk)}")
                import time
                start_time = time.time()
                response = self.client.embeddings.create(
                    model=self.model_embed,
                    input=chunk
                )
                duration_ms = (time.time() - start_time) * 1000
                self._update_latency(self.model_embed, duration_ms)
                
                # Track usage
                self._usage["calls"] += 1
                if hasattr(response, 'usage') and response.usage:
                    in_tok = response.usage.prompt_tokens
                    cost = (in_tok * 0.0000001)
                    self._usage["input_tokens"] += in_tok
                    self._usage["estimated_cost_usd"] += cost
                    
                for j, data in enumerate(response.data):
                    emb = data.embedding
                    text = chunk[j]
                    if len(self._embed_cache) >= self._cache_max_size:
                        self._embed_cache.pop(next(iter(self._embed_cache)))
                    self._embed_cache[text] = emb
                    results[chunk_indices[j]] = emb
                    
            except Exception as e:
                logger.warning(f"Batch embedding failed: {e}. Falling back to single embeds.")
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(self.embed, text) for text in chunk]
                    for j, future in enumerate(futures):
                        results[chunk_indices[j]] = future.result()
                        
        return results

    def get_usage(self) -> Dict[str, Any]:
        """
        Return the usage statistics for this client instance.
        """
        return self._usage
