# sabik_agent/config.py
import os

OPENAI_BASE_URL_TEXT = os.environ.get("OPENAI_BASE_URL_TEXT", "https://text.pollinations.ai/openai")
OPENAI_IMAGE_BASE_URL_TEXT = os.environ.get("OPENAI_IMAGE_BASE_URL_TEXT", "https://image.pollinations.ai")
REFERRER_ID = os.environ.get("OPENAI_REFERRER", "sabik")
API_KEY = os.environ.get("OPENAI_API_KEY", "dummy-openai-key")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "agent_outputs_tool_mode")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)