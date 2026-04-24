FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY server/ ./server/
COPY docs/ ./docs/
COPY README.md ./
COPY images/ ./images/
COPY --from=frontend-builder /app/web/dist ./web/dist

EXPOSE 8765

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8765"]
