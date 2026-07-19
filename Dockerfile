# Minimal Dockerfile for ATLAS backend (run server + deps; frontend/Electron run separately)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "server.py"]
