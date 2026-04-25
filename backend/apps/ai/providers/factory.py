from __future__ import annotations

from functools import lru_cache

from apps.ai.config import get_ai_provider_settings
from apps.ai.providers.base import BaseModelProvider
from apps.ai.providers.mock import MockModelProvider
from apps.ai.providers.openai_compatible import OpenAICompatibleProvider


@lru_cache(maxsize=1)
def get_model_provider() -> BaseModelProvider:
    settings = get_ai_provider_settings()
    if settings.provider in {"mock", "test", "echo"}:
        return MockModelProvider(settings)
    if settings.provider in {"openai", "openai-compatible", "compatible"}:
        return OpenAICompatibleProvider(settings)
    raise ValueError(f"不支持的 AI_PROVIDER: {settings.provider}")
