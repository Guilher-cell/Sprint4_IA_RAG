"""
src/rag/vector_store.py
-----------------------
ChromaDB PERSISTENTE (Aula 05): a base é vetorizada uma vez e reaproveitada nas
execuções seguintes (data/chroma_db/, ignorado pelo git).

O nome da coleção embute uma impressão digital (SHA-1) de: conteúdo dos
documentos + parâmetros de chunking + backend de embeddings. Assim:
  - mudou um documento, o tamanho do chunk ou o modelo de embeddings → coleção nova
    é criada automaticamente (sem índice desatualizado);
  - vetores de backends diferentes (nomic x offline) nunca se misturam.
"""

import hashlib
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.rag.config import CHROMA_DIR


def impressao_digital(chunks: list[Document], backend: str, extra: str = "") -> str:
    h = hashlib.sha1()
    h.update(backend.encode())
    h.update(extra.encode())
    for c in chunks:
        h.update(c.metadata.get("chunk_id", "").encode())
        h.update(c.page_content.encode("utf-8"))
    return h.hexdigest()[:10]


def abrir_ou_criar(
    chunks: list[Document],
    embeddings,
    backend: str,
    persist_dir: Optional[Path] = None,
    prefixo: str = "goodwe_kb",
    extra: str = "",
) -> Chroma:
    """Abre a coleção persistida (se já existir) ou vetoriza `chunks` e a cria."""
    persist_dir = Path(persist_dir or CHROMA_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)
    nome = f"{prefixo}_{backend.replace('-', '_')}_{impressao_digital(chunks, backend, extra)}"

    store = Chroma(
        collection_name=nome,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        # search_ef/construction_ef altos + 1 thread: busca praticamente exata e
        # determinística (o padrão, ef_search=10, é aproximado e variava entre execuções
        # em coleções pequenas como esta).
        collection_metadata={
            "hnsw:space": "cosine",
            "hnsw:search_ef": 200,
            "hnsw:construction_ef": 200,
            "hnsw:num_threads": 1,
        },
    )
    if store._collection.count() == 0:
        ids = [c.metadata["chunk_id"] for c in chunks]
        store.add_documents(chunks, ids=ids)
    return store
