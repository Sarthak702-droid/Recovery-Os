import math
import httpx
from app.core.config import get_settings


async def embed(text: str) -> list[float]:
    s = get_settings()
    async with httpx.AsyncClient(base_url=s.ollama_base_url, timeout=30) as client:
        response = await client.post("/api/embed", json={"model": s.ollama_embedding_model, "input": text})
        response.raise_for_status()
    return response.json()["embeddings"][0]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x*y for x,y in zip(a,b)) / max(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)), 1e-12)
