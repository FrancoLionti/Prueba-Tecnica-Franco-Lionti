"""
Wrapper sobre ChromaDB para almacenamiento y búsqueda de vectores.

ChromaDB es una base de datos vectorial que permite
búsqueda por cos similarity.
"""

from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from src.config import CHROMA_PERSIST_DIR
from src.models import Chunk


COLLECTION_NAME = "support_docs"


@dataclass
class SearchResult:
    """Resultado de una búsqueda semántica."""
    text: str
    source_file: str
    chunk_index: int
    distance: float  # menor = más similar
    metadata: dict


class VectorStore:
    """
    Wrapper sobre ChromaDB que abstrae las operaciones de indexación y búsqueda.

    Persiste en disco para que los embeddings sobrevivan a eventuales reinicios del servidor.
    """

    def __init__(self, persist_dir: str | None = None):
        persist_path = persist_dir or str(CHROMA_PERSIST_DIR)

        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        # Cantidad de documentos indexados
        return self._collection.count()

    def index_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Indexa chunks con sus embeddings en ChromaDB.

        Args:
            chunks: Lista de chunks a indexar.
            embeddings: Lista de vectores correspondientes.

        Returns:
            Cantidad de chunks indexados.
        """
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            # ID único: nombre de archivo + índice del chunk
            chunk_id = f"{chunk.source_file}::chunk_{chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(chunk.text)
            metadatas.append({
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
                "document_title": chunk.document_title or "",
                # ChromaDB solo acepta str, int, float, bool en metadata
                "total_chunks": chunk.metadata.get("total_chunks", 0),
            })

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(ids)

    def search(self, query_embedding: list[float], top_k: int = 3) -> list[SearchResult]:
        """
        Busca los chunks más similares a un query embedding.

        Args:
            query_embedding: Vector de la pregunta del usuario.
            top_k: Cantidad de resultados a devolver.

        Returns:
            Lista de SearchResult ordenados por relevancia (menor distancia primero).
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.count) if self.count > 0 else top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results: list[SearchResult] = []

        if not results["documents"] or not results["documents"][0]:
            return search_results

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            search_results.append(SearchResult(
                text=doc,
                source_file=meta.get("source_file", ""),
                chunk_index=meta.get("chunk_index", 0),
                distance=dist,
                metadata=meta,
            ))

        return search_results

    def clear(self) -> None:
        """Elimina todos los documentos de la colección (útil para re-ingesta)."""
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
