FROM python:3.11-slim AS builder
WORKDIR /build
COPY backend/requirements.txt /build/backend-requirements.txt
COPY engine/requirements.txt /build/engine-requirements.txt
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels -r /build/backend-requirements.txt -r /build/engine-requirements.txt

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ASTROMATCH_RESULTS_DIR=/app/engine/out
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY engine/requirements.txt /tmp/engine-requirements.txt
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/backend-requirements.txt -r /tmp/engine-requirements.txt \
    && rm -rf /wheels \
    && useradd --system --uid 10001 --home-dir /app appuser
COPY backend/app /app/backend/app
COPY backend/entrypoint.sh /usr/local/bin/astromatch-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/astromatch-entrypoint
COPY engine /app/engine
COPY data/processed /app/data/processed
RUN mkdir -p /app/processing/out /app/discovery/out /app/engine/out \
    && chmod +x /usr/local/bin/astromatch-entrypoint \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
ENTRYPOINT ["/usr/local/bin/astromatch-entrypoint"]
