"""Mistral LangChain adapter."""

from typing import Any

from app.core.config import Settings
from app.models.provider_base import ProviderModel


class MistralModel(ProviderModel):
	provider = "mistral"

	def __init__(self, *, client: Any | None = None, settings: Settings | None = None, max_attempts: int = 3) -> None:
		resolved = settings
		super().__init__(resolved.mistral_model if resolved else "mistral-small-latest", client=client, settings=resolved, max_attempts=max_attempts)

	def _create_client(self, settings: Settings) -> Any:
		if not settings.has_mistral_api_key:
			raise ValueError("MISTRAL_API_KEY is required for Mistral")
		from langchain_mistralai import ChatMistralAI

		return ChatMistralAI(model=self.model, api_key=settings._mistral_api_key)