import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load .env for local development if present
load_dotenv()

# ======================================================================
# Ensure the internal Railway/OpenAI base is injected and available for LiteLLM
# LiteLLM may ignore OPENAI_API_BASE when reading certain model strings, so
# we expose OLLAMA_API_BASE and normalize the value (strip trailing /v1)
# ======================================================================
API_BASE = os.getenv("OPENAI_API_BASE", "http://railway.internal").replace("/v1", "")
API_KEY = os.getenv("OPENAI_API_KEY", "fake-railway-key")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")

# Use the ollama_chat prefix to select the chat-capable Ollama backend
OLLAMA_MODEL = f"ollama_chat/{MODEL_NAME}"

# Inject into environment so LiteLLM / CrewAI pick it up reliably
os.environ["OLLAMA_API_BASE"] = API_BASE

# Health server: minimal HTTP endpoint using Python stdlib so no extra deps are required
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
        # suppress default logging to avoid leaking secrets or noisy logs
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

print(f"[CONFIG] OLLAMA_API_BASE : {API_BASE}")
print(f"[CONFIG] Model Name      : {MODEL_NAME}")
print("[CONFIG] ...جارٍ تهيئة نظام الوكلاء...")

# ======================================================================
# تعريف الوكلاء
# ======================================================================
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
    api_key=API_KEY,
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
    api_key=API_KEY,
    verbose=True,
    allow_delegation=False,
)

# ======================================================================
# تعريف المهام
# ======================================================================
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

# ======================================================================
# إقلاع نظام الوكلاء
# ======================================================================
crew = Crew(
    agents=[researcher, writer],
    tasks=[task_research, task_write],
    verbose=True,
)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SHAHEEN-AI — نظام الوكلاء الذكي (CrewAI + Ollama)")
    print("=" * 60 + "\n")

    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("  النتيجة النهائية للوكلاء:")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")
