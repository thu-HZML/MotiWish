from __future__ import annotations

from apps.ai.providers.base import BaseModelProvider


class MockModelProvider(BaseModelProvider):
    def generate_text(self, *, system_prompt: str, user_prompt: str, metadata: dict | None = None) -> str:
        metadata = metadata or {}
        goal = metadata.get("goal", "未命名目标")
        return (
            f"[MOCK PROVIDER]\n"
            f"provider={self.settings.provider}\n"
            f"model={self.settings.model}\n"
            f"goal={goal}\n"
            f"system_prompt={system_prompt[:60]}\n"
            f"user_prompt={user_prompt[:120]}"
        )
