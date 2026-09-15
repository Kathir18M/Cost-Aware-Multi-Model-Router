from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings, load_settings
from app.models.gemini import GeminiModel
from app.models.mistral import MistralModel
from app.models.model_registry import ModelRegistry
from app.schemas.response import ModelResponse
from app.utils.retry import retry_call


def make_settings() -> Settings:
    settings = load_settings()
    return Settings(
        haiku_model=settings.gemini_model,
        sonnet_model=settings.mistral_model,
        haiku_input_price=settings.gemini_input_price,
        haiku_output_price=settings.gemini_output_price,
        sonnet_input_price=settings.mistral_input_price,
        sonnet_output_price=settings.mistral_output_price,
        confidence_threshold=0.7,
        complexity_threshold=0.7,
        log_level="INFO",
        gemini_model=settings.gemini_model,
        mistral_model=settings.mistral_model,
        gemini_input_price=settings.gemini_input_price,
        gemini_output_price=settings.gemini_output_price,
        mistral_input_price=settings.mistral_input_price,
        mistral_output_price=settings.mistral_output_price,
    )


def make_client(response: object) -> Mock:
    client = Mock()
    client.invoke.return_value = response
    client.messages.create.return_value = response
    return client


def test_registry_returns_cached_common_model_interface() -> None:
    registry = ModelRegistry(settings=make_settings(), client=Mock())
    gemini = registry.get_model("gemini")
    mistral = registry.get_model("mistral")

    assert gemini.provider == "gemini"
    assert mistral.provider == "mistral"
    assert registry.get_model("GEMINI") is gemini
    assert registry.get_model("MISTRAL") is mistral


def test_registry_rejects_invalid_model() -> None:
    registry = ModelRegistry(settings=make_settings(), client=Mock())

    with pytest.raises(ValueError, match="Unsupported model"):
        registry.get_model("opus")


def test_successful_response_is_normalized_with_usage() -> None:
    settings = make_settings()
    response = SimpleNamespace(
        content=[SimpleNamespace(text="hello"), SimpleNamespace(text=" world")],
        model=settings.gemini_model,
        usage=SimpleNamespace(input_tokens=12, output_tokens=4),
    )
    client = make_client(response)

    result = GeminiModel(
        settings=settings, client=client, max_attempts=1
    ).invoke("Say hello")

    assert isinstance(result, ModelResponse)
    assert result.content == "hello world"
    assert result.model == settings.gemini_model
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert result.success is True
    assert result.error is None
    client.invoke.assert_called_once_with("Say hello")


def test_api_error_is_normalized_without_secret() -> None:
    settings = make_settings()
    client = Mock()
    client.invoke.side_effect = RuntimeError("GOOGLE_API_KEY=secret-value")

    result = MistralModel(
        settings=settings, client=client, max_attempts=1
    ).invoke([{"role": "user", "content": "hello"}])

    assert result.success is False
    assert result.content == ""
    assert result.error is not None
    assert "secret-value" not in result.error
    assert "[REDACTED]" in result.error


def test_retry_is_bounded_for_retryable_failures() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("temporary")

    with pytest.raises(TimeoutError):
        retry_call(
            operation,
            max_attempts=3,
            is_retryable=lambda error: isinstance(error, TimeoutError),
            backoff_seconds=0,
            sleep=lambda _delay: None,
        )

    assert attempts == 3


@pytest.mark.parametrize(
    ("model_class", "model_name"),
    [(GeminiModel, "test-gemini"), (MistralModel, "test-mistral")],
)
def test_new_provider_adapters_normalize_langchain_messages(
    model_class: type, model_name: str
) -> None:
    message = SimpleNamespace(
        content="provider response",
        usage_metadata={"input_tokens": 8, "output_tokens": 3},
        response_metadata={"model_name": model_name},
    )
    client = Mock()
    client.invoke.return_value = message

    settings = make_settings()
    settings = settings.__class__(
        **{**settings.__dict__, "gemini_model": "test-gemini", "mistral_model": "test-mistral"}
    )
    result = model_class(client=client, settings=settings, max_attempts=1).invoke("hello")

    assert result.success is True
    assert result.content == "provider response"
    assert result.model == model_name
    assert result.input_tokens == 8
    assert result.output_tokens == 3
    client.invoke.assert_called_once_with("hello")


def test_registry_exposes_gemini_and_mistral() -> None:
    registry = ModelRegistry(settings=make_settings(), client=Mock())

    assert registry.get_model("gemini").provider == "gemini"
    assert registry.get_model("mistral").provider == "mistral"
    assert registry.get_model("GEMINI") is registry.get_model("gemini")
    assert registry.get_model("MISTRAL") is registry.get_model("mistral")
