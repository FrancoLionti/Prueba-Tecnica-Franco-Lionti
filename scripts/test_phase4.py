"""
Test de la Fase 4 — API REST con FastAPI.

Levanta el servidor y prueba los 3 endpoints.
Requiere que la ingesta ya se haya ejecutado (Fase 3).
"""

import requests
import time
import subprocess
import sys
import os

BASE_URL = "http://localhost:8000"


def wait_for_server(timeout: int = 30) -> bool:
    """Espera a que el servidor esté listo."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    return False


def test_health():
    """Prueba GET /health."""
    print("\n" + "=" * 50)
    print("  TEST: GET /health")
    print("=" * 50)

    r = requests.get(f"{BASE_URL}/health")
    data = r.json()

    print(f"  Status code: {r.status_code}")
    print(f"  Status: {data['status']}")
    print(f"  Chunks indexados: {data['indexed_chunks']}")
    print(f"  Versión: {data['version']}")

    assert r.status_code == 200
    assert data["status"] == "ok"
    print("  ✓ Health check OK")


def test_ask():
    """Prueba POST /ask con preguntas de ejemplo."""
    print("\n" + "=" * 50)
    print("  TEST: POST /ask")
    print("=" * 50)

    preguntas = [
        "¿Cómo reinicio el servicio de autenticación?",
        "El sistema devuelve error 502, ¿qué significa?",
        "No puedo acceder al dashboard",
    ]

    for pregunta in preguntas:
        print(f"\n  Pregunta: {pregunta}")
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": pregunta},
        )
        data = r.json()

        print(f"  Status code: {r.status_code}")
        print(f"  Modelo: {data.get('model', 'N/A')}")
        print(f"  Fuentes encontradas: {len(data.get('sources', []))}")

        for i, source in enumerate(data.get("sources", []), 1):
            print(f"    [{i}] {source['source_file']} "
                  f"(relevancia: {source['relevance']})")

        assert r.status_code == 200
        print(f"  ✓ OK")


def test_ask_empty():
    """Prueba POST /ask con pregunta vacía (debe fallar con 422)."""
    print("\n" + "=" * 50)
    print("  TEST: POST /ask (input vacío)")
    print("=" * 50)

    r = requests.post(f"{BASE_URL}/ask", json={"question": ""})
    print(f"  Status code: {r.status_code}")
    assert r.status_code == 422
    print("  ✓ Validación de input vacío OK")


def test_ingest():
    """Prueba POST /ingest."""
    print("\n" + "=" * 50)
    print("  TEST: POST /ingest")
    print("=" * 50)

    r = requests.post(f"{BASE_URL}/ingest")
    data = r.json()

    print(f"  Status code: {r.status_code}")
    print(f"  Archivos procesados: {data['files_processed']}")
    print(f"  Archivos saltados: {data['files_skipped']}")
    print(f"  Chunks generados: {data['total_chunks']}")
    print(f"  Chunks indexados: {data['total_indexed']}")
    print(f"  Mensaje: {data['message']}")

    assert r.status_code == 200
    assert data["total_indexed"] > 0
    print("  ✓ Ingesta vía API OK")


if __name__ == "__main__":
    print("=" * 50)
    print("  Fase 4 — Test de API REST")
    print("=" * 50)
    print(f"\n  Verificando que el servidor esté en {BASE_URL}...")

    if not wait_for_server(timeout=5):
        print("  El servidor no está corriendo.")
        print("  Levantalo con: uvicorn src.api.main:app --reload")
        sys.exit(1)

    print("  ✓ Servidor disponible\n")

    test_health()
    test_ask()
    test_ask_empty()
    test_ingest()

    print("\n" + "=" * 50)
    print("  Todos los tests pasaron ✓")
    print("=" * 50)
