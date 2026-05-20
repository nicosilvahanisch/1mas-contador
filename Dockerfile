# Imagen base con Python 3.11 slim — tiene wheels precompilados para pydantic-core
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema que necesita instagrapi
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar el cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
# --no-cache-dir mantiene la imagen liviana
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Puerto que expone Railway (Railway inyecta la variable $PORT automáticamente)
EXPOSE 8000

# Comando de inicio — Railway sobreescribe el puerto con $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
