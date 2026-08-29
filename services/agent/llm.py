"""Local Ollama/Qwen client. It receives curated facts only, never credentials or tools."""
import json
import httpx
from app.core.config import get_settings
from domain.schemas import AgentRecommendationPayload
from services.agent.service import SYSTEM_PROMPT


class OllamaStructuredAgent:
    async def recommend(self, facts: dict) -> AgentRecommendationPayload:
        settings = get_settings()
        payload = {"model": settings.ollama_model, "stream": False, "format": AgentRecommendationPayload.model_json_schema(), "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(facts)}], "options": {"temperature": 0}}
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=45) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
        return AgentRecommendationPayload.model_validate_json(response.json()["message"]["content"])
