from app.router.fallback import execute_with_fallback


def test_retry_then_mistral_fallback() -> None:
	calls: list[str] = []
	initial_model = "gemini"
	fallback_model = "mistral"

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		if model == initial_model:
			raise TimeoutError("temporary")
		return {"content": "fallback", "success": True}

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model=initial_model,
	)

	assert response["content"] == "fallback"
	assert model == fallback_model
	assert retries == 1
	assert fallback is True
	assert calls == [initial_model, initial_model, fallback_model]


def test_success_does_not_fallback_or_loop() -> None:
	calls: list[str] = []
	initial_model = "gemini"

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		return {"content": "ok", "success": True}

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model=initial_model,
	)

	assert response["success"] is True
	assert model == initial_model
	assert retries == 0
	assert fallback is False
	assert calls == [initial_model]


def test_mistral_failure_does_not_create_infinite_fallback() -> None:
	calls: list[str] = []
	initial_model = "mistral"

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		raise RuntimeError("down")

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model=initial_model,
	)

	assert response["success"] is False
	assert model == initial_model
	assert retries == 1
	assert fallback is False
	assert calls == [initial_model, initial_model]
