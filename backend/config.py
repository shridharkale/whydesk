import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip() or None
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "whydesk-prod-bank").strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip() or None
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b").strip()
GROQ_FALLBACK_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
]

BANK_NAME = "WhyDesk Institutional Memory Bank"
BANK_MISSION = (
    "institutional memory for a metric-investigation agent; track confirmed root causes "
    "by region and product, record ruled-out hypotheses, flag unreliable pipelines, "
    "remember each stakeholder's preferred format."
)
BANK_DISPOSITION = {
    "skepticism": 4,
    "literalism": 4,
    "empathy": 2,
}

