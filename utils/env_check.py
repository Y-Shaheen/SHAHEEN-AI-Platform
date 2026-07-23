import os
from dotenv import load_dotenv

# Load local .env if present for local development
load_dotenv()

# List of required environment variables to validate and (if missing) inject defaults
REQUIRED_KEYS = [
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "XAI_API_KEY",
    "OPENAI_API_KEY",
    "MISTRAL_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "EXA_API_KEY",
    "FIRECRAWL_API_KEY",
    "ELEVENLABS_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "SLACK_BOT_TOKEN",
    "GOOGLE_SEARCH_API_KEY",
    "GOOGLE_SEARCH_ENGINE_ID",
    "GOOGLE_API_KEY",
]


def ensure_required_envs():
    """Ensure all required environment variables exist. If not, inject safe defaults.

    This function is safe to run in production. It will not overwrite existing values.
    For missing keys it injects non-sensitive fake placeholders to avoid crashes during
    startup when libraries validate presence of keys. It also sets a DATABASE_URL
    SQLite fallback when DATABASE_URL is missing.
    """
    # Load dotenv again in case callers didn't call it early
    try:
        load_dotenv()
    except Exception:
        pass

    for key in REQUIRED_KEYS:
        if not os.getenv(key):
            os.environ[key] = f"fake-local-secret-{key.lower()}-123"
            print(f"[ENV] Injected safe default for missing env: {key}")

    # Normalize OLLAMA base if provided via OPENAI_API_BASE
    openai_api_base = os.getenv("OPENAI_API_BASE")
    if openai_api_base:
        # remove trailing /v1 if present
        normalized = openai_api_base.replace("/v1", "")
        os.environ.setdefault("OLLAMA_API_BASE", normalized)
        print("[ENV] Normalized OLLAMA_API_BASE from OPENAI_API_BASE")

    # Ensure DATABASE_URL exists; if not, create SQLite fallback
    if not os.getenv("DATABASE_URL"):
        data_dir = os.path.join(os.getcwd(), "data")
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            pass
        sqlite_path = os.path.join(data_dir, "sqlite.db")
        sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"
        os.environ["DATABASE_URL"] = sqlite_url
        print(f"[ENV] DATABASE_URL not found. Injected SQLite fallback: {sqlite_url}")


if __name__ == "__main__":
    ensure_required_envs()
