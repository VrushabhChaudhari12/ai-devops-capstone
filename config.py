import os

# LLM settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "400"))

# Sub-agent retry / timeout settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
LOOP_DETECTION_THRESHOLD = int(os.getenv("LOOP_DETECTION_THRESHOLD", "3"))

# Orchestrator settings
ORCHESTRATOR_TIMEOUT = int(os.getenv("ORCHESTRATOR_TIMEOUT", "300"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Slack
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#devops-alerts")
