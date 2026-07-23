import os
from dotenv import load_dotenv
import httpx
import time

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


def _test_http_get(url: str, headers: dict | None = None, timeout: float = 3.0) -> bool:
    try:
        # ensure URL has scheme
        if url and not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        with httpx.Client(timeout=timeout, verify=True) as client:
            r = client.get(url)
            # Consider any 2xx or 3xx a success
            return 200 <= r.status_code < 400
    except Exception:
        return False


def ensure_required_envs():
    """Ensure all required environment variables exist. If not, inject safe defaults.

    This function is safe to run in production. It will not overwrite existing values.
    For missing keys it injects non-sensitive fake placeholders to avoid crashes during
    startup when libraries validate presence of keys. It also auto-configures
    OPENAI_API_BASE / OLLAMA_API_BASE when possible and sets a DATABASE_URL
    SQLite fallback when DATABASE_URL is missing.
    """
    # Load dotenv again in case callers didn't call it early
    try:
        load_dotenv()
    except Exception:
        pass

    for key in REQUIRED_KEYS:
        if not os.getenv(key):
            # Inject benign placeholder for optional keys to avoid library crashes
            os.environ[key] = f"fake-local-secret-{key.lower()}-123"
            print(f"[ENV] Injected safe default for missing env: {key}")

    # If a local Ollama host is configured, prefer building OPENAI_API_BASE from it
    ollama_host = os.getenv("OLLAMA_HOST")
    port = os.getenv("PORT") or os.getenv("OLLAMA_PORT") or "11434"

    # Map bind addresses (0.0.0.0) to loopback for client connections
    resolved_host = None
    if ollama_host:
        host_clean = ollama_host.strip()
        if host_clean in ("0.0.0.0", "::", ""):
            # 0.0.0.0 is a listen address; for outbound client requests use localhost
            resolved_host = "127.0.0.1"
        else:
            resolved_host = host_clean

    # If OLLAMA_API_BASE is set explicitly, normalize it
    ollama_api_base = os.getenv("OLLAMA_API_BASE")
    if ollama_api_base:
        normalized = ollama_api_base.rstrip("/")
        # ensure scheme
        if not normalized.startswith("http://") and not normalized.startswith("https://"):
            normalized = "http://" + normalized
        os.environ.setdefault("OLLAMA_API_BASE", normalized)
        os.environ.setdefault("OPENAI_API_BASE", normalized + "/v1")
        print("[ENV] Using provided OLLAMA_API_BASE and setting OPENAI_API_BASE accordingly")
    elif resolved_host:
        # assemble base url and prefer it for local LiteLLM/Ollama routing
        host = resolved_host
        if host.startswith("http://") or host.startswith("https://"):
            base = host.rstrip("/")
        else:
            base = f"http://{host}:{port}"
        os.environ.setdefault("OLLAMA_API_BASE", base)
        os.environ.setdefault("OPENAI_API_BASE", base + "/v1")
        print(f"[ENV] Constructed OLLAMA_API_BASE={base} and OPENAI_API_BASE={base}/v1 from OLLAMA_HOST")

    # If OPENAI_API_BASE set but not normalized, normalize it
    openai_api_base = os.getenv("OPENAI_API_BASE")
    if openai_api_base:
        normalized = openai_api_base.rstrip("/")
        if not normalized.startswith("http://") and not normalized.startswith("https://"):
            normalized = "http://" + normalized
        os.environ.setdefault("OPENAI_API_BASE", normalized)

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


def verify_provider_endpoints(retries: int = 2, delay: float = 1.0) -> dict:
    """Check reachability of configured provider endpoints.

    Returns a dict with keys 'openai_base', 'ollama_base', each mapping to True/False.
    """
    results = {
        "openai_base": False,
        "ollama_base": False,
    }

    openai_base = os.getenv("OPENAI_API_BASE")
    ollama_base = os.getenv("OLLAMA_API_BASE") or os.getenv("OPENAI_API_BASE")

    # Try OpenAI base
    if openai_base:
        endpoints = [openai_base, openai_base.rstrip("/") + "/v1", openai_base.rstrip("/") + "/v1/models"]
        for _ in range(retries + 1):
            for ep in endpoints:
                if _test_http_get(ep):
                    results["openai_base"] = True
                    break
            if results["openai_base"]:
                break
            time.sleep(delay)

    # Try Ollama base
    if ollama_base:
        endpoints = [ollama_base, ollama_base.rstrip("/") + "/v1", ollama_base.rstrip("/") + "/v1/models"]
        for _ in range(retries + 1):
            for ep in endpoints:
                if _test_http_get(ep):
                    results["ollama_base"] = True
                    break
            if results["ollama_base"]:
                break
            time.sleep(delay)

    return results


if __name__ == "__main__":
    ensure_required_envs()
    print("Provider endpoints:", verify_provider_endpoints())
