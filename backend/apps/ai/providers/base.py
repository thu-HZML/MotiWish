from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.ai.config import AIProviderSettings


class BaseModelProvider(ABC):
    def __init__(self, settings: AIProviderSettings):
        self.settings = settings

    @property
    def provider_name(self) -> str:
        return self.settings.provider

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.settings.provider,
            "model": self.settings.model,
            "base_url": self.settings.base_url or None,
            "temperature": self.settings.temperature,
            "timeout": self.settings.timeout,
            "max_retries": self.settings.max_retries,
        }

    @abstractmethod
    def generate_text(self, *, system_prompt: str, user_prompt: str, metadata: dict[str, Any] | None = None) -> str:
        raise NotImplementedError
