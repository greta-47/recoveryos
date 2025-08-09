FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONUNBUFFERED=1

# Start the API. Render injects $PORT at runtime; default to 8000 for local.
CMD ["sh","-c","uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
