FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SUPABASE_REST_MODE=true
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --uid 10001 --no-create-home app \
    && install -d -o app -g app /app/backend/data
COPY backend/app ./app
COPY --from=frontend /build/dist /app/frontend/dist
COPY backend/start-container.sh /usr/local/bin/start-sism2i
USER app
EXPOSE 8013
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8013/', timeout=2).close()"]
CMD ["/bin/sh", "/usr/local/bin/start-sism2i"]
