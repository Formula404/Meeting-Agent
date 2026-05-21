# ── Stage 1: build frontend ──
FROM node:20-alpine AS frontend-builder
WORKDIR /build
RUN npm config set registry https://registry.npmmirror.com
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: runtime ──
FROM python:3.11-slim
WORKDIR /app

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends -o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 chromium fonts-noto-cjk fonts-wqy-zenhei fonts-liberation fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Copy application code
COPY meeting_agent/ /app/meeting_agent/

EXPOSE 8000

CMD ["uvicorn", "meeting_agent.web.run:app", "--host", "0.0.0.0", "--port", "8000"]
