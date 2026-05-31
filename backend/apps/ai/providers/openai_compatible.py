from __future__ import annotations

from apps.ai.providers.base import BaseModelProvider


class OpenAICompatibleProvider(BaseModelProvider):
    def __init__(self, settings):
        super().__init__(settings)
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "未安装 langchain-openai，无法使用 openai-compatible provider。"
            ) from exc
        self._client = ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url or None,
            temperature=settings.temperature,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )

    def generate_text(self, *, system_prompt: str, user_prompt: str, metadata: dict | None = None) -> str:
        response = self._client.invoke(
            [
                ("system", system_prompt),
                ("user", user_prompt),
            ]
        )
        return getattr(response, "content", str(response))
