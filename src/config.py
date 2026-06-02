import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────
# BASE_DIR apunta a la raíz del proyecto (donde está docker-compose.yml)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carpeta con los documentos de soporte a ingestar
DOCS_DIR = BASE_DIR / "docs"

# Carpeta donde ChromaDB persiste los embeddings
CHROMA_PERSIST_DIR = BASE_DIR / "data" / "chroma"

# ── OpenAI ─────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_CHAT_MODEL = "gpt-4o-mini"

# ── Chunking ───────────────────────────────────────────────────────
# Tamaño máximo de cada chunk en caracteres.
# 500 es un buen balance: suficiente para capturar un error completo
# con su causa y solución, pero no tanto como para desperdiciar tokens.
CHUNK_SIZE = 500

# Superposición entre chunks consecutivos en caracteres.
# Evita que información se "pierda" en los bordes entre chunks.
CHUNK_OVERLAP = 50

# ── Retrieval ──────────────────────────────────────────────────────
# Cantidad de chunks relevantes a devolver en cada búsqueda.
# Con documentación pequeña (4 archivos), 3 es suficiente.
RETRIEVAL_TOP_K = 3

# ── API ────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ── Formatos de archivo soportados ─────────────────────────────────
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".pdf"}
