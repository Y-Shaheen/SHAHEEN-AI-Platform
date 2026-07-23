FROM ollama/ollama:latest

# تثبيت curl لفحوصات الجاهزية والـ Health Check
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# نسخ سكربت الإقلاع الذكي
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ollama يستمع على المنفذ 11434 بشكل افتراضي
EXPOSE 11434

# فحص صحة الحاوية عبر Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -sf http://localhost:11434/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
