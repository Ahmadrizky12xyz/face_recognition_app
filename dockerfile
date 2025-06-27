
# Gunakan base image Python 3.9 slim
FROM python:3.9-slim

# Install dependensi sistem untuk dlib, face_recognition, dan psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set direktori kerja
WORKDIR /app

# Salin requirements.txt dan instal dependensi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh proyek
COPY . .

# Set variabel lingkungan untuk port
ENV PORT=8080

# Jalankan aplikasi dengan gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
