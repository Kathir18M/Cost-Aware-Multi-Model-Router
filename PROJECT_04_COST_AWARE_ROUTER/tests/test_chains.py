import pytest
from pydantic import ValidationError

from app.chains.base import ChainOutputError
from app.chains.classification_chain import ClassificationChain
from app.chains.extraction_chain import ExtractionChain
from app.chains.qa_chain import QAChain
from app.chains.summarization_chain import SummarizationChain
from app.schemas.request import TaskRequest
from app.schemas.response import (
    ClassificationResponse,
    ExtractionResponse,
    QAResponse,
    SummarizationResponse,
)


class FakeModel:
    def __init__(self, response: object) -> None:
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return self.response


@pytest.mark.parametrize(
    ("chain_class", "response_type", "payload"),
    [
        (
            ClassificationChain,
            ClassificationResponse,
            {"label": "billing", "confidence": 0.9, "reason": "invoice language"},
        ),
        (
            ExtractionChain,
            ExtractionResponse,
            {"fields": {"name": "Ada"}, "confidence": 0.8},
        ),
        (
            SummarizationChain,
            SummarizationResponse,
            {"summary": "A short summary.", "confidence": 0.75},
        ),
        (
            QAChain,
            QAResponse,
            {"answer": "Paris", "confidence": 0.95},
        ),
    ],
)
def test_chain_construction_and_structured_parsing(
    chain_class: type, response_type: type, payload: dict
) -> None:
    model = FakeModel(payload)
    chain = chain_class(model)

    result = chain.invoke(TaskRequest(text="test input"))

    assert isinstance(result, response_type)
    assert result.model_dump() == payload
    assert len(model.prompts) == 1
    assert "test input" in model.prompts[0]


def test_chain_parses_json_content_from_model_message() -> None:
    model = FakeModel(
        type("Message", (), {"content": '{"answer":"42","confidence":0.9}'})
    )

    result = QAChain(model).invoke("What is the answer?")

    assert result.answer == "42"


def test_chain_accepts_fenced_json() -> None:
    model = FakeModel(
        "```json\n{\"summary\": \"Brief\", \"confidence\": 0.7}\n```"
    )

    result = SummarizationChain(model).invoke("Long text")

    assert result.summary == "Brief"


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        {"answer": "missing confidence"},
        {"answer": "invalid confidence", "confidence": 2},
    ],
)
def test_invalid_outputs_raise_chain_output_error(payload: object) -> None:
    with pytest.raises(ChainOutputError):
        QAChain(FakeModel(payload)).invoke("Question")


def test_request_schema_rejects_empty_input() -> None:
    with pytest.raises(ValidationError):
        TaskRequest(text="")
