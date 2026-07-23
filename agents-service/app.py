import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

# Load .env for local development if present
load_dotenv()

# Use centralized env normalization and probes
try:
    from utils.env_check import ensure_required_envs, verify_provider_endpoints
except Exception:
    # Fallback: define no-op if import fails during early bootstrap
    def ensure_required_envs():
        return

    def verify_provider_endpoints(*args, **kwargs):
        return {"openai_base": False, "ollama_base": False}

# Ensure required envs are present early
ensure_required_envs()

# ======================================================================
# Health server: minimal HTTP endpoint using Python stdlib so no extra deps
# are required. Start it immediately so Railway detects a bound port.
# ======================================================================
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # suppress default logging to avoid noisy logs
        return


def start_health_server():
    port = int(os.getenv("PORT", "6185"))
    host = "0.0.0.0"
    try:
        server = HTTPServer((host, port), _HealthHandler)
    except Exception as e:
        print(f"[HEALTH] Failed to start health server on {host}:{port}: {e}")
        return

    def _serve():
        print(f"[HEALTH] Listening on http://{host}:{port}/health")
        try:
            server.serve_forever()
        except Exception:
            pass

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

# Start health server early so Railway sees a bound port immediately
start_health_server()

# ======================================================================
# Normalize provider base and model selection
# ======================================================================
# Prefer OPENAI_API_BASE if available; fall back to OLLAMA_API_BASE
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Compose a base URL that CrewAI expects (strip trailing /v1 for some adapters)
API_BASE = None
if OPENAI_API_BASE:
    API_BASE = OPENAI_API_BASE.rstrip("/")
elif OLLAMA_API_BASE:
    API_BASE = OLLAMA_API_BASE.rstrip("/")\nelse:
    # fallback to localhost (useful in dev containers)
    api_host = os.getenv("OLLAMA_HOST") or "127.0.0.1"
    api_port = os.getenv("PORT") or os.getenv("OLLAMA_PORT") or "11434"
    if api_host in ("0.0.0.0", "::"):
        api_host = "127.0.0.1"
    API_BASE = f"http://{api_host}:{api_port}"

# Expose OLLAMA_API_BASE for other libraries
os.environ.setdefault("OLLAMA_API_BASE", API_BASE)
os.environ.setdefault("OPENAI_API_BASE", API_BASE + "/v1")

print(f"[CONFIG] OLLAMA_API_BASE : {API_BASE}")
print(f"[CONFIG] Model Name      : {MODEL_NAME}")
print("[CONFIG] ...جارٍ تهيئة نظام الوكلاء...")

# ======================================================================
# Delay agent creation until providers are reachable. This avoids crashes
# during import when network or config is not yet ready (e.g., in Railway).
# ======================================================================
def init_agents_with_retry(max_retries=5, delay=3.0):
    """Initialize CrewAI agents with retries. Runs in background thread."""
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        print(f"[AGENTS] Initialization attempt {attempt}/{max_retries}")
        probes = verify_provider_endpoints(retries=1, delay=0.5)
        if probes.get("openai_base") or probes.get("ollama_base"):
            try:
                # Define agents now that provider is reachable
                OLLAMA_MODEL = f"ollama_chat/{MODEL_NAME}"

                researcher = Agent(
                    role="خبير برمجيات وأنظمة",
                    goal=(
                        "تحليل متطلبات النظم وتطوير حلول برمجية مستقلة وآمنة محلياً بنسبة 100%، "
                        "مع التركيز على الأداء والكفاءة في بيئات الحاويات الموزعة."
                    ),
                    backstory=(
                        "أنت مهندس أنظمة ذكي تعمل داخل بيئة معزولة ومستقرة تعتمد على نماذج مفتوحة المصدر. "
                        "ميزتك الكبرى هي تقديم حلول برمجية عبقرية ونظيفة دون الاعتماد على خدمات سحابية مدفوعة."
                    ),
                    llm=OLLAMA_MODEL,
                    base_url=API_BASE,
                    api_key=OPENAI_API_KEY,
                    verbose=True,
                    allow_delegation=False,
                )

                writer = Agent(
                    role="محرر تقني محترف",
                    goal=(
                        "صياغة التقارير الفنية وشرح البنى التحتية بأسلوب واضح ومفهوم "
                        "يستهدف المطورين وصانعي القرار في آنٍ واحد."
                    ),
                    backstory=(
                        "أنت خبير في تبسيط المفاهيم المعقدة وشرح الأنظمة الموزعة. "
                        "تحوّل التقارير التقنية الجافة إلى محتوى جذاب ومقنع دون فقدان الدقة والعمق."
                    ),
                    llm=OLLAMA_MODEL,
                    base_url=API_BASE,
                    api_key=OPENAI_API_KEY,
                    verbose=True,
                    allow_delegation=False,
                )

                task_research = Task(
                    description=(
                        "قم بإجراء تحليل فني شامل لمقارنة استخدام النماذج المحلية مفتوحة المصدر "
                        "(مثل llama3, mistral, phi3) مقابل الاعتماد على APIs السحابية المدفوعة "
                        "(مثل OpenAI GPT-4, Anthropic Claude). "
                        "يجب أن يغطي التحليل: التكلفة التشغيلية، الخصوصية والأمان، "
                        "الكمون (Latency)، قابلية التوسع، وجودة الاستجابة."
                    ),
                    agent=researcher,
                    expected_output=(
                        "تقرير فني منقح من 400 إلى 600 كلمة يتضمن جدول مقارنة واضح "
                        "وتوصية نهائية مدعومة بالأرقام والحجج التقنية."
                    ),
                )

                task_write = Task(
                    description=(
                        "بناءً على تقرير الباحث، اكتب مقالاً تقنياً احترافياً يبرز كفاءة وفوائد "
                        "الاستضافة الذاتية للنماذج الذكية. يجب أن يكون المقال جذاباً للمطورين "
                        "والشركات الناشئة التي تبحث عن حلول ذكاء اصطناعي اقتصادية وآمنة. "
                        "أضف عنواناً رئيسياً قوياً وخاتمة تدعو القارئ للتجربة الفعلية."
                    ),
                    agent=writer,
                    expected_output=(
                        "مقال تقني نهائي من 500 إلى 800 كلمة، جاهز للنشر، يتضمن عنواناً، "
                        "مقدمة، أقساماً واضحة، وخاتمة مع دعوة للعمل (Call to Action)."
                    ),
                )

                crew = Crew(agents=[researcher, writer], tasks=[task_research, task_write], verbose=True)

                def kickoff_and_log():
                    try:
                        print("[AGENTS] Starting crew kickoff...")
                        res = crew.kickoff()
                        print("[AGENTS] Crew kickoff finished:", res)
                    except Exception as e:
                        print("[AGENTS] Crew kickoff error:", e)

                # Run kickoff in background so main process remains responsive
                t = threading.Thread(target=kickoff_and_log, daemon=True)
                t.start()

                print("[AGENTS] Initialization completed successfully.")
                return True

            except Exception as e:
                print(f"[AGENTS] Failed to initialize agents on attempt {attempt}: {e}")
        else:
            print(f"[AGENTS] Provider endpoints not reachable yet (attempt {attempt}). Probes: {probes}")

        time.sleep(delay)

    print("[AGENTS] All initialization attempts failed. Agents will keep retrying in background.")
    return False


# Kick off agent initialization in background so health remains green
_background_thread = threading.Thread(target=init_agents_with_retry, kwargs={"max_retries": 10, "delay": 5}, daemon=True)
_background_thread.start()

if __name__ == "__main__":
    # Useful for local testing
    print("Agents service main invoked. Health server running.")
    # Wait for background thread (demo only)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down")
