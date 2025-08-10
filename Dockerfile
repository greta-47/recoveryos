FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONUNBUFFERED=1

# Start the API. Render injects $PORT at runtime (don’t set it yourself).
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT}"]


