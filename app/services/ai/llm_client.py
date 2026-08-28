import json
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.core.config import settings
from app.schemas.query import QueryRequest

logger = logging.getLogger("argo_ai_service")

SYSTEM_PROMPT = """You are FloatChatAI, an expert oceanographic query parser for the ARGO Float platform dataset.
Your task is to convert the user's natural language question into a STRICT JSON object representing query filters for the ARGO database.

Allowed Output Fields (only include relevant non-null fields):
- "float_ids": array of string platform IDs (e.g. ["ARGO_001"])
- "bounding_box": object with "min_lat" (-90 to 90), "max_lat" (-90 to 90), "min_lon" (-180 to 180), "max_lon" (-180 to 180)
- "depth_range": object with "min" (meters) and/or "max" (meters)
- "parameters": array of canonical parameter names from:
  ["temperature_C", "salinity", "pressure_dbar", "density_kg_m3", "dissolved_oxygen_umol_kg", "oxygen_saturation_pct", "chlorophyll_mg_m3", "nitrate_umol_kg", "pH", "PAR_umol_m2_s"]
- "start_date": ISO datetime string (e.g. "2026-08-01T00:00:00")
- "end_date": ISO datetime string (e.g. "2026-08-05T23:59:59")

IMPORTANT RULES:
1. Return ONLY the raw JSON object. No Markdown code fences, no commentary.
2. NEVER generate SQL queries or database commands.
3. If the user asks something completely outside oceanography, return: {"status": "unsupported"}
"""


class LLMClient:
    """
    Configurable LLM client for translating natural language queries to structured QueryRequest schemas.
    Supports OpenAI, Gemini, Anthropic, and local Ollama instances.
    """

    @classmethod
    async def parse_with_llm(
        cls,
        prompt: str,
        base_request: Optional[QueryRequest] = None,
    ) -> Optional[Tuple[QueryRequest, Dict[str, Any]]]:
        """
        Attempt to parse user natural language query using the configured LLM provider.
        Returns (QueryRequest, ai_context) or None if provider is unconfigured or failed.
        """
        provider = settings.AI_PROVIDER.lower()

        # Determine effective provider
        if provider == "auto":
            if settings.OPENAI_API_KEY:
                provider = "openai"
            elif settings.GEMINI_API_KEY:
                provider = "gemini"
            elif settings.ANTHROPIC_API_KEY:
                provider = "anthropic"
            else:
                return None  # Fallback to deterministic parser

        try:
            raw_json_str = None
            parser_name = provider

            if provider == "openai" and settings.OPENAI_API_KEY:
                raw_json_str = await cls._call_openai(prompt)
            elif provider == "gemini" and settings.GEMINI_API_KEY:
                raw_json_str = await cls._call_gemini(prompt)
            elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                raw_json_str = await cls._call_anthropic(prompt)
            elif provider == "ollama":
                raw_json_str = await cls._call_ollama(prompt)
            else:
                return None

            if not raw_json_str:
                return None

            # Clean and parse JSON response
            cleaned_json = raw_json_str.strip()
            if cleaned_json.startswith("```"):
                cleaned_json = cleaned_json.split("\n", 1)[-1]
            if cleaned_json.endswith("```"):
                cleaned_json = cleaned_json.rsplit("\n", 1)[0]
            cleaned_json = cleaned_json.strip()

            parsed_dict = json.loads(cleaned_json)

            if parsed_dict.get("status") == "unsupported":
                query_req = base_request or QueryRequest(natural_language_prompt=prompt)
                ai_ctx = {
                    "received_prompt": prompt,
                    "parsed_intent": {},
                    "parser_used": f"llm_{parser_name}",
                    "status": "ambiguous_or_unsupported",
                    "explanation": "Query was identified as outside the scope of ARGO oceanographic measurements.",
                }
                return query_req, ai_ctx

            # Validate against Pydantic QueryRequest
            parsed_dict["natural_language_prompt"] = prompt
            if base_request:
                if base_request.limit is not None:
                    parsed_dict["limit"] = base_request.limit
                if base_request.offset is not None:
                    parsed_dict["offset"] = base_request.offset

            query_req = QueryRequest.model_validate(parsed_dict)

            ai_ctx = {
                "received_prompt": prompt,
                "parsed_intent": {
                    "float_ids": query_req.float_ids,
                    "bounding_box": query_req.bounding_box.model_dump() if query_req.bounding_box else None,
                    "depth_range": query_req.depth_range,
                    "parameters": query_req.parameters,
                    "start_date": query_req.start_date.isoformat() if query_req.start_date else None,
                    "end_date": query_req.end_date.isoformat() if query_req.end_date else None,
                },
                "parser_used": f"llm_{parser_name}",
                "status": "success",
                "explanation": f"Successfully parsed intent via {parser_name.capitalize()} LLM.",
            }

            return query_req, ai_ctx

        except Exception as e:
            logger.warning(f"LLM parsing failed ({provider}): {e}. Falling back to deterministic parser.")
            return None

    @classmethod
    async def _call_openai(cls, prompt: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        return None

    @classmethod
    async def _call_gemini(cls, prompt: str) -> Optional[str]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.LLM_MODEL or 'gemini-1.5-flash'}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nUser Question: {prompt}"}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        return None

    @classmethod
    async def _call_anthropic(cls, prompt: str) -> Optional[str]:
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL or "claude-3-5-haiku-20241022",
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
        return None

    @classmethod
    async def _call_ollama(cls, prompt: str) -> Optional[str]:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        payload = {
            "model": settings.LLM_MODEL or "llama3.2",
            "prompt": f"{SYSTEM_PROMPT}\n\nUser Question: {prompt}",
            "stream": False,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["response"]
        return None
