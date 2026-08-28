from typing import Any, Dict, Optional, Tuple

from app.schemas.query import QueryRequest
from app.services.ai.deterministic_parser import DeterministicParser
from app.services.ai.llm_client import LLMClient


class FloatChatAIService:
    """
    Unified AI and Natural Language Query Service for FloatChatAI.
    Coordinates between optional LLM providers (OpenAI, Gemini, Anthropic, Ollama)
    and guaranteed offline deterministic semantic extraction.
    """

    @classmethod
    async def parse_query(
        cls,
        prompt: str,
        base_request: Optional[QueryRequest] = None,
    ) -> Tuple[QueryRequest, Dict[str, Any]]:
        """
        Convert a user natural language prompt into a validated QueryRequest filter object
        and structured ai_context metadata.
        """
        # 1. If LLM is configured, attempt LLM structured parsing
        llm_result = await LLMClient.parse_with_llm(prompt, base_request=base_request)
        if llm_result is not None:
            return llm_result

        # 2. Otherwise (or on LLM failure), use deterministic semantic parser
        return DeterministicParser.parse(prompt, base_request=base_request)
