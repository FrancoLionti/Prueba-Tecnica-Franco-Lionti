"""
Verificación de la Fase 3: Embeddings + búsqueda semántica.

1. Ejecuta la ingesta completa (read → chunk → embed local → store)
2. Prueba búsquedas con las preguntas de ejemplo del enunciado
3. Muestra los resultados con distancias (menor = más relevante)
"""

from src.ingestion.embedder import embed_texts
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import VectorStore


def main():
    print("=" * 60)
    print("  FASE 3 — Ingesta + Búsqueda Semántica")
    print("=" * 60)

    # Paso 1: ejecutar ingesta completa
    print("\n--- Ingesta ---")
    stats = run_ingestion()
    print(f"\n  {stats.total_indexed} chunks indexados correctamente.")

    # Paso 2: probar búsquedas con preguntas del enunciado
    print("\n--- Prueba de búsqueda semántica ---")

    preguntas = [
        "¿Cómo reinicio el servicio de autenticación?",
        "El sistema devuelve error 502, ¿qué significa?",
        "No puedo acceder al dashboard",
        "Credenciales incorrectas, ¿qué hago?",
        "Error de conexión con la base de datos",
    ]

    store = VectorStore()

    for pregunta in preguntas:
        print(f"\n  Pregunta: \"{pregunta}\"")
        print(f"  {'─' * 50}")

        # Embebir la pregunta (localmente)
        query_embedding = embed_texts([pregunta])[0]

        # Buscar en ChromaDB
        results = store.search(query_embedding, top_k=2)

        for i, result in enumerate(results):
            relevance = 1 - result.distance
            print(f"  Resultado #{i + 1} (similitud: {relevance:.3f})")
            print(f"    Fuente: {result.source_file}")
            lines = result.text.split("\n")[:2]
            for line in lines:
                print(f"    > {line[:80]}")
            print()

    print("=" * 60)
    print("  Fase 3 OK.")
    print("=" * 60)


if __name__ == "__main__":
    main()
