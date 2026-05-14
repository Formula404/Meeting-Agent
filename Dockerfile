# ── Stage 1: build frontend ──
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: runtime ──
FROM python:3.11-slim
WORKDIR /app

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Copy application code
COPY meeting_agent/ /app/meeting_agent/

EXPOSE 8000

CMD ["uvicorn", "meeting_agent.web.run:app", "--host", "0.0.0.0", "--port", "8000"]
