"""Google Gemini LangChain adapter."""

from typing import Any

from app.core.config import Settings
from app.models.provider_base import ProviderModel


class GeminiModel(ProviderModel):
	provider = "gemini"

	def __init__(self, *, client: Any | None = None, settings: Settings | None = None, max_attempts: int = 3) -> None:
		resolved = settings
		super().__init__(resolved.gemini_model if resolved else "gemini-2.0-flash", client=client, settings=resolved, max_attempts=max_attempts)

	def _create_client(self, settings: Settings) -> Any:
		if not settings.has_google_api_key:
			raise ValueError("GOOGLE_API_KEY is required for Gemini")
		from langchain_google_genai import ChatGoogleGenerativeAI

		return ChatGoogleGenerativeAI(model=self.model, google_api_key=settings._google_api_key)