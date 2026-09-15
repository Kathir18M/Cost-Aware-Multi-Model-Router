"""Centralized values shared by the application foundation."""

TASK_CLASSIFICATION = "classification"
TASK_EXTRACTION = "extraction"
TASK_SUMMARIZATION = "summarization"
TASK_QA = "qa"

COMPLEXITY_LOW = "low"
COMPLEXITY_MEDIUM = "medium"
COMPLEXITY_HIGH = "high"

MODEL_GEMINI = "gemini"
MODEL_MISTRAL = "mistral"
MODEL_HAIKU = MODEL_GEMINI
MODEL_SONNET = MODEL_MISTRAL

STATUS_ACCEPTED = "accepted"
STATUS_ESCALATED = "escalated"
STATUS_FALLBACK = "fallback"
STATUS_FAILED = "failed"
