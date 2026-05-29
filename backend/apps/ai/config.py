from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIProviderSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    timeout: int
    max_retries: int


def get_ai_provider_settings() -> AIProviderSettings:
    return AIProviderSettings(
        provider=os.getenv("AI_PROVIDER", "mock").strip().lower(),
        model=os.getenv("AI_MODEL", "mock-gpt"),
        api_key=os.getenv("AI_API_KEY", ""),
        base_url=os.getenv("AI_BASE_URL", ""),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.2")),
        timeout=int(os.getenv("AI_TIMEOUT", "60")),
        max_retries=int(os.getenv("AI_MAX_RETRIES", "2")),
    )
