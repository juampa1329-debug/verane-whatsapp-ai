FROM python:3.11-bookworm

WORKDIR /app

# Dependencias del sistema para Pillow + conversión AVIF/JPG
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libavif-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
