FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para instagrapi
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Puerto por defecto
ENV PORT=8000

# Comando de inicio
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
