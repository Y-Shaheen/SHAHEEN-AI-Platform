import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

# Load .env for local development if present
load_dotenv()

# قائمة بجميع المتغيرات البيئية المطلوبة والخاصة بالخدمات المختلفة
required_keys = [
    # مفاتيح ومزودات الذكاء الاصطناعي والأدوات المساعدة (16)
    "OPENROUTER_API_KEY", "SLACK_BOT_TOKEN", "TAVILY_API_KEY", "XAI_API_KEY",
    "OPENAI_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY",
    "GEMINI_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY", "ELEVENLABS_API_KEY",
    "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID",
    # متغيرات خدمات الوكلاء والويب والتليجرام والـ Ollama
    "TELEGRAM_BOT_TOKEN", "WEB_WEBUI_USERNAME", "WEB_WEBUI_PASSWORD",
    "OPENAI_API_BASE", "MODEL_NAME", "OLLAMA_HOST", "PORT"
]

print("[SYSTEM] جاري فحص وتأمين حقن المتغيرات البيئية الخادعة والمفاتيح المطلوبة...")
for key in required_keys:
    if not os.getenv(key):
        # حقن قيمة افتراضية آمنة؛ لبعض المتغيرات نضع قيمة منطقية بدلاً من fake-secret
        if key == "PORT":
            os.environ[key] = "11434"
        elif key == "OLLAMA_HOST":
            # وفق توصيتك للسماح بالاتصالات الخارجية (bind) نضع 0.0.0.0 كقيمة افتراضية
            os.environ[key] = "0.0.0.0"
        elif key == "MODEL_NAME":
            os.environ[key] = "llama3:8b"
        elif key == "OPENAI_API_BASE":
            # إذا لم يحدد OPENAI_API_BASE نكوّن الرابط من OLLAMA_HOST و PORT
            host = os.getenv("OLLAMA_HOST") or "localhost"
            port = os.getenv("PORT") or "11434"
            os.environ[key] = f"http://{host}:{port}/v1"
        elif key in ("WEB_WEBUI_USERNAME", "WEB_WEBUI_PASSWORD"):
            # قيم افتراضية للولوج إلى واجهة الويب
            os.environ[key] = f"admin-{key.lower()}"
        else:
            os.environ[key] = f"fake-local-secret-{key.lower()}-123"
        print(f"[ENV] تم حقن متغير افتراضي آمن لـ: {key}")

# الآن نقرأ المتغيرات البيئية التي يحتاجها تطبيق الوكلاء والواجهة
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
PORT = os.getenv("PORT")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_WEBUI_USERNAME = os.getenv("WEB_WEBUI_USERNAME")
WEB_WEBUI_PASSWORD = os.getenv("WEB_WEBUI_PASSWORD")

# إعداد اسم نموذج LiteLLM/OLLAMA كما طلبت
OLLAMA_MODEL = f"openai/{MODEL_NAME}"

print(f"[CONFIG] OLLAMA_HOST          : {OLLAMA_HOST}")
print(f"[CONFIG] PORT                 : {PORT}")
print(f"[CONFIG] OPENAI_API_BASE      : {OPENAI_API_BASE}")
print(f"[CONFIG] Model Name           : {MODEL_NAME}")
print(f"[CONFIG] Web UI Username      : {WEB_WEBUI_USERNAME}")
print("[CONFIG] ...جارٍ تهيئة نظام الوكلاء والواجهات")

# تعريف الوكلاء باستخدام الصيغة النصية للـ llm مع حقن الـ base_url والـ api_key
researcher = Agent(
    role='خبير برمجيات وأنظمة',
    goal='تحليل متطلبات النظم وتطوير حلول برمجية مستقلة وآمنة محلياً بنسبة 100%',
    backstory='أنت مهندس أنظمة ذكي تعمل داخل بيئة معزولة ومستقرة، ميزتك الكبرى هي تقديم حلول برمجية عبقرية ونظيفة.',
    llm=OLLAMA_MODEL,
    base_url=OPENAI_API_BASE,
    api_key=OPENAI_API_KEY,
    verbose=True
)

writer = Agent(
    role='محرر تقني محترف',
    goal='صياغة التقارير الفنية وشرح البنى التحتية بأسلوب واضح ومفهوم',
    backstory='أنت خبير في تبسيط المفاهيم المعقدة وشرح الأنظمة الموزعة للمطورين.',
    llm=OLLAMA_MODEL,
    base_url=OPENAI_API_BASE,
    api_key=OPENAI_API_KEY,
    verbose=True
)

# تعريف المهام
task1 = Task(
    description="قم بتحليل ميزات استخدام النماذج المحلية مفتوحة المصدر مقارنة بالـ APIs المدفوعة وعمل مقارنة هيكلية.", 
    agent=researcher, 
    expected_output="تقرير فني منقح وجاهز للصياغة."
)

task2 = Task(
    description="اكتب مقالاً تقنياً بناءً على تحليل الباحث يبرز كفاءة الاستضافة المستقلة على منصات السحاب محلياً.", 
    agent=writer, 
    expected_output="مقال نهائي احترافي جاهز للنشر الفوري."
)

# إقلاع الـ Crew
crew = Crew(
    agents=[researcher, writer], 
    tasks=[task1, task2], 
    verbose=True
)

if __name__ == "__main__":
    print("[START] تفعيل الوكلاء وبدء الاتصال الداخلي بمحرك Ollama...")
    # تشغيل الوكلاء (kickoff) — يمكن أن يكون طويل الأمد حسب إعدادات Crew
    result = crew.kickoff()
    print("\n### النتيجة النهائية للوكلاء: ###\n", result)
