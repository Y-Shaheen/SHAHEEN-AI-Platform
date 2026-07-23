import os
from crewai import Agent, Task, Crew

# قائمة بكافة المفاتيح البيئية المطلوبة للتأكد من وجودها وحقنها برمجياً
required_keys = [
    "OPENROUTER_API_KEY", "SLACK_BOT_TOKEN", "TAVILY_API_KEY", "XAI_API_KEY",
    "OPENAI_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY",
    "GEMINI_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY", "ELEVENLABS_API_KEY",
    "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"
]

print("[SYSTEM] جاري فحص وتأمين حقن المتغيرات البيئية الخادعة والمفاتيح المطلوبة...")
for key in required_keys:
    if not os.getenv(key):
        # حقن قيمة وهمية آمنة في بيئة النظام إذا كان المفتاح فارغاً لضمان عدم الانهيار
        os.environ[key] = f"fake-local-secret-{key.lower()}-123"
        print(f"[ENV] تم حقن متغير افتراضي آمن لـ: {key}")

# جلب الإعدادات الأساسية للاتصال بمحرك الاستضافة الداخلي لـ Railway
API_BASE = os.getenv("OPENAI_API_BASE")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")

# صياغة اسم النموذج المتوافقة مع نظام LiteLLM المدمج في CrewAI
OLLAMA_MODEL = f"openai/{MODEL_NAME}"

print(f"[CONFIG] Base URL : {API_BASE}")
print(f"[CONFIG] Model Name: {MODEL_NAME}")
print("[CONFIG] ...جارٍ تهيئة نظام الوكلاء الخارق")

# تعريف الوكيل الأول (الباحث) مع حقن الإعدادات والرابط الداخلي والـ API Key مباشرة
researcher = Agent(
    role='خبير برمجيات وأنظمة',
    goal='تحليل متطلبات النظم وتطوير حلول برمجية مستقلة وآمنة محلياً بنسبة 100%',
    backstory='أنت مهندس أنظمة ذكي تعمل داخل بيئة معزولة ومستقرة، ميزتك الكبرى هي تقديم حلول برمجية عبقرية ونظيفة.',
    llm=OLLAMA_MODEL,
    base_url=API_BASE,
    api_key=API_KEY,
    verbose=True
)

# تعريف الوكيل الثاني (الكاتب) مع حقن الإعدادات والرابط الداخلي والـ API Key مباشرة
writer = Agent(
    role='محرر تقني محترف',
    goal='صياغة التقارير الفنية وشرح البنى التحتية بأسلوب واضح ومفهوم',
    backstory='أنت خبير في تبسيط المفاهيم المعقدة وشرح الأنظمة الموزعة للمطورين.',
    llm=OLLAMA_MODEL,
    base_url=API_BASE,
    api_key=API_KEY,
    verbose=True
)

# تعريف المهام (Tasks) البرمجية للتشغيل التلقائي
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

# إقلاع الـ Crew لبدء التنفيذ الصارم للمشروع على السيرفر المحلي
crew = Crew(
    agents=[researcher, writer], 
    tasks=[task1, task2], 
    verbose=True
)

print("[START] تفعيل الوكلاء وبدء الاتصال الداخلي بمحرك Ollama...")
result = crew.kickoff()
print("\n### النتيجة النهائية للوكلاء: ###\n", result)
