from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.models.claude_haiku import ClaudeHaiku
from app.models.claude_sonnet import ClaudeSonnet
from app.models.model_registry import ModelRegistry
from app.schemas.response import ModelResponse
from app.utils.retry import retry_call


def make_settings() -> Settings:
	return Settings(
		haiku_model="test-haiku",
		sonnet_model="test-sonnet",
		haiku_input_price=1.0,
		haiku_output_price=1.0,
		sonnet_input_price=1.0,
		sonnet_output_price=1.0,
		confidence_threshold=0.7,
		complexity_threshold=0.7,
		log_level="INFO",
	)


def make_client(response: object) -> Mock:
	client = Mock()
	client.messages.create.return_value = response
	return client


def test_registry_returns_cached_common_model_interface() -> None:
	registry = ModelRegistry(settings=make_settings(), client=Mock())

	haiku = registry.get_model("HAIKU")
	sonnet = registry.get_model("sonnet")

	assert isinstance(haiku, ClaudeHaiku)
	assert isinstance(sonnet, ClaudeSonnet)
	assert registry.get_model("haiku") is haiku


def test_registry_rejects_invalid_model() -> None:
	registry = ModelRegistry(settings=make_settings(), client=Mock())

	with pytest.raises(ValueError, match="Unsupported model"):
		registry.get_model("opus")


def test_successful_response_is_normalized_with_usage() -> None:
	response = SimpleNamespace(
		content=[SimpleNamespace(text="hello"), SimpleNamespace(text=" world")],
		model="test-haiku",
		usage=SimpleNamespace(input_tokens=12, output_tokens=4),
	)
	client = make_client(response)

	result = ClaudeHaiku(
		settings=make_settings(), client=client, max_attempts=1
	).invoke("Say hello")

	assert isinstance(result, ModelResponse)
	assert result.content == "hello world"
	assert result.model == "test-haiku"
	assert result.input_tokens == 12
	assert result.output_tokens == 4
	assert result.success is True
	assert result.error is None
	client.messages.create.assert_called_once_with(
		model="test-haiku",
		max_tokens=1024,
		messages=[{"role": "user", "content": "Say hello"}],
	)


def test_api_error_is_normalized_without_secret() -> None:
	client = Mock()
	client.messages.create.side_effect = RuntimeError(
		"ANTHROPIC_API_KEY=" + "sk-ant-" + "secret-value"
	)

	result = ClaudeSonnet(
		settings=make_settings(), client=client, max_attempts=1
	).invoke([{"role": "user", "content": "hello"}])

	assert result.success is False
	assert result.content == ""
	assert result.error is not None
	assert "sk-ant-" + "secret-value" not in result.error
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
