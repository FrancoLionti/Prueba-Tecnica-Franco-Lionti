# Asistente de Soporte RAG

Sistema de soporte técnico inteligente basado en **Retrieval-Augmented Generation (RAG)** que responde preguntas de usuarios utilizando documentación técnica interna como fuente de verdad.

## Arquitectura

```mermaid
flowchart LR
  %% ── Entradas ─────────────────────────────────────────────────────
  user([Usuario]) -->|pregunta| n8n[n8n\nWebhook]
  user -->|pregunta| api

  %% ── API (RAG) ────────────────────────────────────────────────────
  subgraph api[FastAPI]
    ask[POST /ask]\
    ingest[POST /ingest]\
    health[GET /health]
  end

  %% ── Flujo /ask ───────────────────────────────────────────────────
  n8n -->|forward JSON| ask

  ask -->|embed_texts()\n(all-MiniLM-L6-v2, local)| st[sentence-transformers]
  st -->|query_embedding| ask

  ask -->|VectorStore.search(top_k=RETRIEVAL_TOP_K)| chroma[(ChromaDB\nPersistentClient)]
  chroma -->|chunks + distances| ask

  ask -->|context_chunks| llm[OpenAI Chat Completions\nmodel: gpt-4o-mini]
  llm -->|answer| ask

  ask --> resp[[AnswerResponse\n(answer + sources + model)]]

  %% ── Flujo /ingest ────────────────────────────────────────────────
  ingest -->|run_ingestion(clear_existing=True)| pipeline[Ingestion Pipeline]

  subgraph pipeline[Ingestion Pipeline]
    docs[docs/\n(SUPPORTED_EXTENSIONS)] --> readers[get_reader()\nreaders.*]
    readers --> chunker[chunk_document()\n(CHUNK_SIZE + CHUNK_OVERLAP)]
    chunker --> embed[embed_chunks()\n(all-MiniLM-L6-v2, local)]
    embed --> index[VectorStore.index_chunks()]
  end

  index --> chroma

  %% ── Health ───────────────────────────────────────────────────────
  health -->|VectorStore.count| chroma
```

**Flujo completo (alto nivel):**
1. El usuario envía una pregunta vía webhook de n8n o directamente a la API
2. `/ask` genera el embedding con `sentence-transformers` (local)
3. `ChromaDB` busca los chunks más similares (`VectorStore.search`, `RETRIEVAL_TOP_K`)
4. Se arma `context_chunks` con texto + `source_file`
5. Se llama a OpenAI (`gpt-4o-mini`) para generar la respuesta
6. Se devuelve `AnswerResponse` con `answer`, `sources` (con relevancia) y `model`

## Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| API REST | FastAPI | Async, tipado, documentación automática OpenAPI |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, rápido, sin costo por uso |
| Vector Store | ChromaDB | Ligero, persistente, búsqueda coseno |
| LLM | OpenAI API (gpt-4o-mini) | Económico, rápido, buena calidad |
| Orquestación | n8n | Visual, extensible, webhooks nativos |
| Contenedores | Docker + Docker Compose | Reproducibilidad y despliegue simple |

## Estructura del Proyecto

```
├── src/
│   ├── api/               # API REST (FastAPI)
│   │   ├── main.py        # Endpoints: /ask, /ingest, /health
│   │   └── schemas.py     # Modelos Pydantic (request/response)
│   ├── ingestion/         # Pipeline de ingesta de documentos
│   │   ├── readers.py     # Lectores por formato (TXT, MD, JSON, PDF)
│   │   ├── normalizer.py  # Limpieza y normalización de texto
│   │   ├── chunker.py     # Fragmentación semántica con overlap
│   │   ├── embedder.py    # Generación de embeddings (local)
│   │   ├── vector_store.py # Wrapper ChromaDB
│   │   └── pipeline.py    # Orquestación del flujo de ingesta
│   ├── llm/               # Integración con OpenAI
│   │   ├── generator.py   # Cliente OpenAI y generación de respuestas
│   │   └── prompts.py     # Templates de prompts (anti-alucinación)
│   ├── config.py          # Configuración centralizada
│   └── models.py          # Dataclasses compartidos (Document, Chunk)
├── docs/                  # Documentación técnica a indexar
├── n8n/
│   └── workflow.json      # Workflow exportable para n8n
├── scripts/               # Scripts de testing por fase
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Requisitos Previos

- Python 3.12+
- Docker y Docker Compose
- Clave de API de OpenAI

## Instalación y Ejecución

### Opción 1: Docker Compose (recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/FrancoLionti/Prueba-Tecnica-Franco-Lionti.git
cd Prueba-Tecnica-Franco-Lionti

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu OPENAI_API_KEY

# 3. Levantar los servicios
docker compose up -d

# 4. Verificar que estén corriendo
docker compose ps
```

La API estará disponible en `http://localhost:8000` y n8n en `http://localhost:5678`.

### Opción 2: Ejecución Local

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu OPENAI_API_KEY

# 4. Ejecutar el pipeline de ingesta (indexa la documentación)
python -m src.ingestion.pipeline

# 5. Iniciar la API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## Uso de la API

### Hacer una pregunta

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Error de conexión a base de datos"}'
```

**Respuesta:**
```json
{
  "answer": "El mensaje de error es 'Error de conexión con el servidor de datos'. Las causas posibles son: ...",
  "sources": [
    {
      "text": "3.2 Error: no se puede conectar con la base de datos...",
      "source_file": "docs/Documentación 2.txt",
      "relevance": 0.6837
    }
  ],
  "model": "gpt-4o-mini"
}
```

### Re-indexar documentación

```bash
curl -X POST http://localhost:8000/ingest
```

### Health check

```bash
curl http://localhost:8000/health
```

### Vía n8n (webhook)

```bash
curl -X POST http://localhost:5678/webhook/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Error de conexión a base de datos"}'
```

## Configuración del Workflow n8n

1. Acceder a n8n en `http://localhost:5678`
2. Crear cuenta de administrador (primera vez)
3. Importar el workflow desde `n8n/workflow.json`
4. Publicar/activar el workflow
5. El webhook queda disponible en `/webhook/ask`

## Documentación Soportada

El sistema soporta los siguientes formatos de documentación:

| Formato | Reader | Notas |
|---------|--------|-------|
| `.txt`  | TxtReader | Extrae secciones numeradas como metadata |
| `.md`   | MarkdownReader | Extrae títulos H1 y palabras clave |
| `.json` | JsonReader | Convierte estructura JSON a texto legible |
| `.pdf`  | PdfReader | Extrae texto con PyMuPDF (bonus) |

## Decisiones de Diseño

### Embeddings locales vs OpenAI
Se usa `sentence-transformers` (all-MiniLM-L6-v2) para embeddings en lugar de la API de OpenAI. Esto permite:
- Cero costo por embedding generado
- Sin dependencia de red para la indexación
- Latencia mínima en búsquedas

El requisito de usar OpenAI API se cumple en la generación de respuestas (gpt-4o-mini).

### Chunking semántico con overlap
Los documentos se fragmentan en chunks de ~500 caracteres con 50 caracteres de overlap entre chunks consecutivos. Esto evita perder contexto en los bordes de cada fragmento.

### Prompt anti-alucinación
El system prompt instruye al LLM a responder exclusivamente con información del contexto proporcionado. Si no encuentra información relevante, responde explícitamente que no la encontró en lugar d[...]
