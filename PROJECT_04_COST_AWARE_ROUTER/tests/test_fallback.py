from app.router.fallback import execute_with_fallback


def test_retry_then_sonnet_fallback() -> None:
	calls: list[str] = []

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		if model == "haiku":
			raise TimeoutError("temporary")
		return {"content": "fallback", "success": True}

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model="haiku",
	)

	assert response["content"] == "fallback"
	assert model == "sonnet"
	assert retries == 1
	assert fallback is True
	assert calls == ["haiku", "haiku", "sonnet"]


def test_success_does_not_fallback_or_loop() -> None:
	calls: list[str] = []

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		return {"content": "ok", "success": True}

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model="haiku",
	)

	assert response["success"] is True
	assert model == "haiku"
	assert retries == 0
	assert fallback is False
	assert calls == ["haiku"]


def test_sonnet_failure_does_not_create_infinite_fallback() -> None:
	calls: list[str] = []

	def executor(model: str, _task: str, _input: str) -> dict:
		calls.append(model)
		raise RuntimeError("down")

	response, model, retries, fallback = execute_with_fallback(
		executor,
		task_type="qa",
		user_input="Question?",
		initial_model="sonnet",
	)

	assert response["success"] is False
	assert model == "sonnet"
	assert retries == 1
	assert fallback is False
	assert calls == ["sonnet", "sonnet"]
