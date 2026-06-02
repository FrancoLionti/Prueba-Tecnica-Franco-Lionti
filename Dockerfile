FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para PyMuPDF
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente y documentación
COPY src/ src/
COPY docs/ docs/
COPY .env.example .env.example

# Crear directorio para persistencia de ChromaDB
RUN mkdir -p data/chroma

# Puerto de la API
EXPOSE 8000

# Ejecutar el pipeline de ingesta al iniciar (si no hay datos previos)
# y luego arrancar la API
CMD ["sh", "-c", "python -m src.ingestion.pipeline && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
