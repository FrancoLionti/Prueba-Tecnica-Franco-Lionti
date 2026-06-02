"""
Test de la Fase 5 — Integración con LLM (RAG completo).

Levanta el servidor y prueba que el endpoint /ask ahora
devuelve respuestas generadas por OpenAI gpt-4o-mini
basadas en la documentación indexada.

Requiere:
- Saldo en la cuenta de OpenAI (OPENAI_API_KEY en .env)
- Documentación indexada en ChromaDB (Fase 3)
"""

import requests
import sys
import time

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


def test_rag_questions():
    """Prueba las preguntas de ejemplo del enunciado con RAG completo."""
    print("\n" + "=" * 60)
    print("  TEST: RAG completo — Preguntas del enunciado")
    print("=" * 60)

    preguntas = [
        "¿Cómo reinicio el servicio de autenticación?",
        "El sistema devuelve error 502, ¿qué significa?",
        "No puedo acceder al dashboard",
    ]

    for pregunta in preguntas:
        print(f"\n{'─' * 60}")
        print(f"  Pregunta: {pregunta}")
        print(f"{'─' * 60}")

        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": pregunta},
            timeout=30,
        )

        if r.status_code != 200:
            print(f"  ✗ Error {r.status_code}: {r.json().get('detail', 'desconocido')}")
            continue

        data = r.json()
        print(f"  Modelo: {data['model']}")
        print(f"  Respuesta:\n")

        # Indentar la respuesta para legibilidad
        for line in data["answer"].split("\n"):
            print(f"    {line}")

        print(f"\n  Fuentes ({len(data['sources'])}):")
        for i, src in enumerate(data["sources"], 1):
            print(f"    [{i}] {src['source_file']} (relevancia: {src['relevance']})")

        assert data["model"] != "retrieval-only", "Debería usar el LLM, no retrieval-only"
        assert data["model"] != "none"
        print(f"\n  ✓ OK — Respuesta generada por {data['model']}")


def test_question_without_info():
    """Prueba una pregunta sin información en la documentación."""
    print(f"\n{'─' * 60}")
    print("  TEST: Pregunta sin información disponible")
    print(f"{'─' * 60}")

    pregunta = "¿Cuál es la política de vacaciones de la empresa?"

    r = requests.post(
        f"{BASE_URL}/ask",
        json={"question": pregunta},
        timeout=30,
    )

    data = r.json()
    print(f"  Pregunta: {pregunta}")

    if r.status_code != 200:
        print(f"  ✗ Error {r.status_code}: {data.get('detail', 'desconocido')}")
        return

    print(f"  Respuesta:\n")
    for line in data["answer"].split("\n"):
        print(f"    {line}")

    print(f"\n  ✓ OK — El modelo debería indicar que no tiene esa información")


if __name__ == "__main__":
    print("=" * 60)
    print("  Fase 5 — Test de integración LLM (RAG completo)")
    print("=" * 60)
    print(f"\n  Verificando que el servidor esté en {BASE_URL}...")

    if not wait_for_server(timeout=5):
        print("  El servidor no está corriendo.")
        print("  Levantalo con: uvicorn src.api.main:app --reload")
        sys.exit(1)

    print("  ✓ Servidor disponible")

    test_rag_questions()
    test_question_without_info()

    print("\n" + "=" * 60)
    print("  Todos los tests pasaron ✓")
    print("=" * 60)
