FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY assistant.py .
COPY bot.py .
COPY config.py .
COPY handlers.py .
COPY knowledge_base.py .
COPY utils.py .
COPY data/ ./data/

RUN mkdir -p /app/chroma_db

CMD ["python", "bot.py"]
