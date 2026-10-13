# Build from repository root: docker build -f api/Dockerfile -t highground-api .
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg62-turbo-dev zlib1g-dev libfreetype6-dev libraqm-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY api/requirements.txt api/requirements-build.txt ./
RUN pip install --no-cache-dir --no-deps -r requirements-build.txt \
    && pip wheel --no-cache-dir --no-deps --no-build-isolation --no-binary=Pillow \
       -C raqm=enable -r requirements.txt --wheel-dir=/wheels

FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g libfreetype6 libraqm0 \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY --from=wheels /wheels /wheels
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --no-deps --find-links=/wheels -r requirements.txt \
    && pip check && rm -rf /wheels \
    && python -c "from PIL import features; import sys; sys.exit(0 if all(features.check(x) for x in ('raqm','fribidi','harfbuzz')) else 'Required Pillow RAQM shaping unavailable')" \
    && groupadd --gid 10001 highground && useradd --uid 10001 --gid 10001 --no-create-home highground
COPY --chown=10001:10001 api /app/api
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/healthz',timeout=3)"
CMD ["sh", "-c", "exec python -m uvicorn api.main:app --host 0.0.0.0 --port \"${PORT:-8080}\""]
