#!/bin/bash
set -e

echo "[START] بدء تشغيل سيرفر Ollama في الخلفية..."
ollama serve > /var/log/ollama.log 2>&1 &
OLLAMA_PID=$!

echo "[CHECK] الانتظار حتى يصبح السيرفر جاهزاً للاستجابة على المنفذ 11434..."
MAX_ATTEMPTS=30
ATTEMPT=0

while ! curl -sf http://127.0.0.1:11434/ > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -eq "$MAX_ATTEMPTS" ]; then
        echo "[ERROR] فشل سيرفر Ollama في الإقلاع خلال الوقت المحدد ($(( MAX_ATTEMPTS * 2 )) ثانية). إغلاق الحاوية."
        echo "[LOG] آخر سطور من السجل:"
        tail -20 /var/log/ollama.log || true
        kill "$OLLAMA_PID" 2>/dev/null || true
        exit 1
    fi
    echo "[WAIT] السيرفر يستعد... محاولة ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

echo "[READY] سيرفر Ollama يستجيب بنجاح على المنفذ 11434."

echo "[DOWNLOAD] جارٍ الآن تنزيل النموذج المفتوح المصدر: llama3:8b ..."
if ollama pull llama3:8b; then
    echo "[SUCCESS] تم تنزيل وتجهيز نموذج llama3:8b بنجاح داخل الحاوية!"
else
    echo "[CRITICAL] فشل تنزيل النموذج. يرجى التحقق من اتصال الإنترنت الداخلي للحاوية."
    kill "$OLLAMA_PID" 2>/dev/null || true
    exit 1
fi

echo "[HEALTH] التحقق من جاهزية النموذج عبر API..."
if curl -sf -X POST http://127.0.0.1:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"llama3:8b","prompt":"ping","stream":false}' > /dev/null 2>&1; then
    echo "[VERIFIED] النموذج يستجيب للطلبات — الحاوية جاهزة تماماً."
else
    echo "[WARNING] النموذج محمّل لكن لم يستجب لطلب الاختبار. المتابعة على أي حال..."
fi

echo "[MONITOR] الحاوية مستقرة ومفتوحة للاتصالات الداخلية على المنفذ 11434."
echo "[INFO] PID الخاص بسيرفر Ollama: $OLLAMA_PID"

wait "$OLLAMA_PID"
