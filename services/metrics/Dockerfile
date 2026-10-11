FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY services/metrics/requirements.txt /app/services/metrics/requirements.txt
RUN pip install --no-cache-dir -r services/metrics/requirements.txt && useradd --uid 10001 --create-home router && mkdir /data && chown router:router /data
COPY src/codex_model_router /app/src/codex_model_router
COPY services/metrics/app.py services/metrics/schema.sql /app/services/metrics/
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "services.metrics.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--limit-concurrency", "32", "--timeout-keep-alive", "5", "--no-access-log", "--no-proxy-headers"]
