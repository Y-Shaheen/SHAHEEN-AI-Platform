# 🚀 SHAHEEN-AI Platform — Railway Deployment Guide

نظام وكلاء ذكاء اصطناعي مستقل وجاهز للإنتاج، يعمل بنماذج مفتوحة المصدر بدون أي مفاتيح مدفوعة.

---

## 🏗️ معمارية النظام

```
┌─────────────────────────────────────────────────────┐
│                  Railway Project                      │
│                                                       │
│  ┌──────────────────┐      ┌──────────────────────┐  │
│  │  ollama-service  │◄─────│   agents-service     │  │
│  │                  │      │                      │  │
│  │  Ollama + LLM    │      │  CrewAI + LangChain  │  │
│  │  Port: 11434     │      │  (Python App)        │  │
│  │                  │      │                      │  │
│  └──────────────────┘      └──────────────────────┘  │
│         ▲                           │                 │
│         └──── Private Network ──────┘                 │
│         http://ollama-service.railway.internal:11434  │
└─────────────────────────────────────────────────────┘
```

- **ollama-service**: محرك الاستدلال — يشغّل نموذج `llama3:8b` محلياً داخل الحاوية.
- **agents-service**: تطبيق الوكلاء — يتصل بـ Ollama عبر الشبكة الداخلية لـ Railway.

---

## ✅ المتطلبات الأساسية

- حساب Railway مفعّل: [railway.app](https://railway.app)
- Git CLI أو GitHub متصل بـ Railway
- المستودع (هذا المشروع) مرفوع على GitHub

---

## 📦 هيكل المشروع

```
SHAHEEN-AI-Platform/
├── ollama-service/
│   ├── Dockerfile         ← حاوية Ollama مع curl
│   └── entrypoint.sh      ← سكربت إقلاع ذكي مع health check
├── agents-service/
│   ├── Dockerfile         ← حاوية Python + CrewAI
│   ├── app.py             ← نظام الوكلاء الكامل
│   └── requirements.txt   ← الاعتماديات
├── .env.example           ← نموذج متغيرات البيئة
└── RAILWAY_DEPLOY_README.md
```

---

## 🛠️ خطوات النشر على Railway

### الخطوة 1 — إنشاء مشروع Railway جديد

1. اذهب إلى [railway.app/new](https://railway.app/new)
2. اختر **"Deploy from GitHub repo"**
3. حدد هذا المستودع (`SHAHEEN-AI-Platform`)
4. اضغط **"Add service"** ← سيُنشئ Railway خدمة تلقائياً

---

### الخطوة 2 — نشر خدمة Ollama (المحرك)

1. في لوحة تحكم المشروع، اضغط **"+ New Service"** → **"GitHub Repo"**
2. اختر المستودع نفسه
3. في إعدادات الخدمة ← **"Settings"** → **"Build"**:
   - **Root Directory**: `ollama-service`
   - **Build Command**: *(اتركه فارغاً — Dockerfile يتولى الأمر)*
4. اضغط **Deploy**

> ⚠️ **تنبيه مهم**: تنزيل نموذج `llama3:8b` (~5 GB) يستغرق **5–15 دقيقة** عند أول إقلاع.  
> راقب السجلات (Logs) من لوحة التحكم حتى تظهر رسالة `[SUCCESS]`.

---

### الخطوة 3 — تفعيل Private Networking لخدمة Ollama

1. افتح إعدادات **ollama-service**
2. اذهب إلى **"Networking"** → **"Private Networking"**
3. فعّل الخيار ← ستحصل على رابط داخلي بصيغة:
   ```
   http://ollama-service.railway.internal:11434
   ```
4. احفظ هذا الرابط — ستستخدمه في الخطوة التالية

---

### الخطوة 4 — نشر خدمة الوكلاء (CrewAI)

1. في المشروع نفسه، اضغط **"+ New Service"** → **"GitHub Repo"**
2. اختر المستودع
3. في إعدادات الخدمة ← **"Settings"** → **"Build"**:
   - **Root Directory**: `agents-service`
4. اذهب إلى **"Variables"** وأضف المتغيرات التالية:

| المتغير | القيمة |
|---------|--------|
| `OPENAI_API_BASE` | `http://ollama-service.railway.internal:11434/v1` |
| `OPENAI_API_KEY` | `local-secret-key-123` |
| `MODEL_NAME` | `llama3:8b` |

> 🔑 استبدل `ollama-service` في الرابط باسم خدمة Ollama الفعلي من لوحة تحكم Railway إن اختلف.

5. اضغط **Deploy**

---

### الخطوة 5 — التحقق من النشر الناجح

**لخدمة Ollama — راقب Logs حتى تظهر:**
```
[START] بدء تشغيل سيرفر Ollama في الخلفية...
[READY] سيرفر Ollama يستجيب بنجاح على المنفذ 11434.
[DOWNLOAD] جارٍ الآن تنزيل النموذج المفتوح المصدر: llama3:8b ...
[SUCCESS] تم تنزيل وتجهيز نموذج llama3:8b بنجاح داخل الحاوية!
[MONITOR] الحاوية مستقرة ومفتوحة للاتصالات الداخلية على المنفذ 11434.
```

**لخدمة الوكلاء — راقب Logs حتى تظهر:**
```
[CONFIG] Base URL  : http://ollama-service.railway.internal:11434/v1
[CONFIG] Model Name: llama3:8b
SHAHEEN-AI — نظام الوكلاء الذكي (CrewAI + Ollama)
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: خدمة الوكلاء لا تتصل بـ Ollama
**السبب الأرجح**: الرابط الداخلي خاطئ أو Private Networking غير مفعّل.  
**الحل**:
1. تأكد من تفعيل Private Networking في إعدادات **ollama-service**
2. تحقق من أن قيمة `OPENAI_API_BASE` تنتهي بـ `/v1`
3. تأكد من أن اسم الخدمة في الرابط يطابق اسمها الفعلي في Railway

### المشكلة: تنزيل النموذج يفشل
**السبب الأرجح**: انتهت مهلة الـ Health Check قبل انتهاء التنزيل.  
**الحل**: في إعدادات **ollama-service** → **"Settings"** → ابحث عن **"Health Check"**:
- غيّر `Start Period` إلى `300` ثانية (5 دقائق)

### المشكلة: خطأ `Connection refused` في Logs
**السبب الأرجح**: خدمة الوكلاء تشتغل قبل اكتمال تنزيل النموذج في Ollama.  
**الحل**: أعد تشغيل (Redeploy) خدمة الوكلاء بعد أن تظهر رسالة `[SUCCESS]` في Ollama.

---

## 💡 نصائح للإنتاج

- **التخزين الدائم (Persistent Volume)**: لتجنب إعادة تنزيل النموذج عند كل إعادة نشر،  
  أضف Volume في Railway وربطه بالمسار `/root/.ollama` داخل `ollama-service`.

- **تغيير النموذج**: لاستخدام نموذج أخف وزناً (أسرع/أرخص):
  - `phi3:mini` — 3.8B parameter, سريع جداً
  - `mistral:7b` — جودة عالية ومتوازنة
  - غيّر `MODEL_NAME` في متغيرات `agents-service` وعدّل `entrypoint.sh` في `ollama-service`

- **تعدد الوكلاء**: لإضافة وكلاء جدد، عرّفهم في `agents-service/app.py` بنفس نمط `researcher` و`writer`.

---

## 📊 التكلفة التقديرية على Railway

| الخدمة | RAM المطلوبة | CPU | التكلفة الشهرية التقديرية |
|--------|-------------|-----|---------------------------|
| ollama-service | 8–16 GB | 4+ vCPU | ~$20–$50 |
| agents-service | 512 MB | 0.5 vCPU | ~$5 |

> 🆓 Railway يوفر $5 مجاناً شهرياً — كافية للتجربة والتطوير.

---

## 🤝 المساهمة

هذا المشروع جزء من **SHAHEEN-AI-Platform** — منصة وكلاء ذكاء اصطناعي مفتوحة المصدر.  
للمساهمة أو الإبلاغ عن مشكلة: [github.com/Y-Shaheen/SHAHEEN-AI-Platform/issues](https://github.com/Y-Shaheen/SHAHEEN-AI-Platform/issues)

---

<div align="center">

**بُني بـ ❤️ بواسطة Y. Z. A. SHAHEEN 🇯🇴**  
*Intelligence • Code • Future*

</div>
