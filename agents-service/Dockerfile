FROM python:3.12-slim

# تعيين مجلد العمل
WORKDIR /app

# تحسين الأداء: تعطيل كتابة .pyc وتشغيل الإخراج الفوري
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# تثبيت الاعتماديات أولاً للاستفادة من Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ كود التطبيق
COPY app.py .

# نسخ ملف البيئة المحلي إن وُجد (اختياري — Railway يمرر المتغيرات تلقائياً)
COPY .env* ./

# تشغيل نظام الوكلاء
CMD ["python", "app.py"]
