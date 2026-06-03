"""
Fixtures compartidas para los tests del proyecto RAG.

Proporciona archivos temporales de cada formato soportado y
objetos Document/Chunk pre-construidos para evitar duplicación.
"""

import json
import textwrap

import pytest
from pathlib import Path

from src.models import Document, Chunk


# ── Fixtures de archivos temporales ───────────────────────────────

@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    """Crea un archivo .txt de ejemplo con formato de secciones numeradas."""
    content = textwrap.dedent("""\
        3.2 Error: no se puede conectar con la base de datos
        Mensaje mostrado

        Error de conexión con el servidor de datos.

        Causas posibles
        Servidor de base de datos apagado.
        Parámetros de conexión incorrectos.
        Solución

        Revisar la conexión de red y validar los parámetros de configuración.

        3.3 Error: código de material duplicado
        Mensaje mostrado

        Ya existe un material registrado con este código.

        Causas posibles
        Registro manual con código repetido.
        Solución

        Buscar el código en el catálogo y actualizar el registro existente.
    """)
    f = tmp_path / "test_doc.txt"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def sample_md(tmp_path: Path) -> Path:
    """Crea un archivo .md de ejemplo con headers y sección de palabras clave."""
    content = textwrap.dedent("""\
        # Error frecuente: Credenciales incorrectas

        ## Código
        ERR-AUTH-001

        ## Categoría
        Autenticación

        ## Causas posibles
        - Contraseña mal escrita.
        - Usuario inexistente.

        ## Solución recomendada
        1. Verificar usuario y contraseña.
        2. Comprobar si la cuenta está activa.

        ## Palabras clave
        login, inicio de sesión, contraseña, credenciales
    """)
    f = tmp_path / "test_doc.md"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def sample_json(tmp_path: Path) -> Path:
    """Crea un archivo .json de ejemplo con la estructura de Unilink."""
    data = {
        "software": "MineCatalog",
        "tipo_documento": "documentacion_tecnica",
        "version": "1.0",
        "modulo": "errores_frecuentes",
        "contenido": [
            {
                "id": "ERR-DB-001",
                "categoria": "configuracion_servicios",
                "titulo": "No se puede conectar con la base de datos",
                "mensaje_usuario": "Error de conexión con el servidor de datos.",
                "causas_posibles": [
                    "Servidor de base de datos apagado",
                    "Parámetros de conexión incorrectos",
                ],
                "solucion": [
                    "Verificar que el servidor esté activo",
                    "Validar host, puerto y credenciales",
                ],
                "nivel_soporte": "Nivel 2",
                "palabras_clave": ["base de datos", "conexión", "servidor"],
            }
        ],
    }
    f = tmp_path / "test_doc.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f


@pytest.fixture
def sample_document() -> Document:
    """Documento pre-construido para tests del chunker."""
    content = (
        "Sección 1: Descripción del error de conexión.\n"
        "El servidor no responde a las peticiones del cliente.\n"
        "\n\n"
        "Sección 2: Causas posibles.\n"
        "El puerto 5432 está bloqueado por el firewall.\n"
        "Las credenciales configuradas son incorrectas.\n"
        "\n\n"
        "Sección 3: Solución recomendada.\n"
        "Verificar la configuración del firewall y las credenciales."
    )
    return Document(
        content=content,
        source_file="docs/test_doc.txt",
        file_type=".txt",
        metadata={"format": "txt", "section_count": 3},
    )


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    """Lista de Chunks pre-construidos para tests de la API."""
    return [
        Chunk(
            text="Error de conexión con el servidor de datos. Verificar red.",
            source_file="docs/Documentación 2.txt",
            chunk_index=0,
            metadata={"format": "txt", "total_chunks": 2},
        ),
        Chunk(
            text="Código de material duplicado. Buscar en catálogo.",
            source_file="docs/Documentación 2.txt",
            chunk_index=1,
            metadata={"format": "txt", "total_chunks": 2},
        ),
    ]
