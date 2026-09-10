"""Phase 1 application bootstrap."""

from app.core.config import load_settings
from app.core.logging_config import configure_logging


def main() -> None:
	"""Verify that the foundation loads without making external requests."""

	settings = load_settings()
	logger = configure_logging(settings.log_level)
	logger.info("Application foundation loaded successfully")
	logger.info("Configuration validated for model routing")


if __name__ == "__main__":
	main()
