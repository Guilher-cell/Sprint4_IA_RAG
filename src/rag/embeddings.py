"""
src/rag/embeddings.py
---------------------
Embeddings do pipeline RAG (Aula 05).

Backend principal (exigido pelo enunciado): `nomic-embed-text` servido pelo
Ollama — Ollama Cloud (OLLAMA_API_KEY + OLLAMA_BASE_URL=https://ollama.com) ou um
servidor Ollama local. O nomic-embed-text espera prefixos de tarefa
("search_document: " / "search_query: "), aplicados aqui.

Backend de contingência: `offline-hash` — embeddings determinísticos por hashing
de tokens (sem rede, sem modelo). Existe para que o projeto rode, seja testado e
avaliado em ambientes sem acesso ao Ollama (ex.: CI, sala de aula sem internet).
NÃO substitui o nomic-embed-text na entrega: os scores finais da Sprint devem ser
reexecutados com `EMBEDDINGS_BACKEND=nomic` (ver README).

Seleção (variável EMBEDDINGS_BACKEND): nomic | offline | auto (padrão).
`auto` tenta o nomic e, se o Ollama estiver inacessível, cai para offline com um
aviso explícito — o nome do backend usado fica registrado na coleção do Chroma e
nos resultados das avaliações, para nunca misturar os dois silenciosamente.
"""

import os
import warnings
import zlib
from typing import Optional

import numpy as np
from langchain_core.embeddings import Embeddings

from src.rag.textutils import tokens

NOMIC_MODEL = "nomic-embed-text"


class HashingEmbeddings(Embeddings):
    """Embeddings offline: unigramas + bigramas (stems) em espaço hash de 2048 dims, L2-normalizados."""

    nome = "offline-hash"

    def __init__(self, dim: int = 2048):
        self.dim = dim

    def _vetor(self, texto: str) -> list[float]:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = tokens(texto)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        for f in set(feats):
            h = zlib.crc32(f.encode("utf-8"))
            v[h % self.dim] += 1.0  # contagem binária (cada feature conta uma vez)
        n = np.linalg.norm(v)
        return (v / n).tolist() if n else v.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vetor(text)


class NomicOllamaEmbeddings(Embeddings):
    """nomic-embed-text via Ollama, com os prefixos de tarefa recomendados pelo modelo."""

    nome = NOMIC_MODEL

    def __init__(self, modelo: str = NOMIC_MODEL, base_url: Optional[str] = None, api_key: Optional[str] = None):
        from langchain_ollama import OllamaEmbeddings

        api_key = api_key or os.environ.get("OLLAMA_API_KEY")
        # chave de exemplo do .env.example (ou vazia) não é chave: usa o Ollama LOCAL
        if api_key is not None and (not api_key.strip() or api_key.lower().startswith("coloque")):
            api_key = None
            # a biblioteca `ollama` também lê OLLAMA_API_KEY do ambiente e enviaria o cabeçalho sozinha
            os.environ.pop("OLLAMA_API_KEY", None)
        base_url = base_url or os.environ.get(
            "OLLAMA_BASE_URL", "https://ollama.com" if api_key else "http://localhost:11434"
        )
        kwargs = {}
        if api_key:
            kwargs["client_kwargs"] = {"headers": {"Authorization": f"Bearer {api_key}"}, "timeout": 30}
        self._emb = OllamaEmbeddings(model=modelo, base_url=base_url, **kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._emb.embed_documents([f"search_document: {t}" for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._emb.embed_query(f"search_query: {text}")


def get_embeddings(backend: Optional[str] = None):
    """
    Retorna (embeddings, nome_do_backend).
    Levanta RuntimeError se backend='nomic' e o Ollama estiver inacessível.
    """
    backend = (backend or os.environ.get("EMBEDDINGS_BACKEND", "auto")).lower()
    if backend not in {"nomic", "offline", "auto"}:
        raise ValueError("EMBEDDINGS_BACKEND deve ser nomic, offline ou auto.")

    if backend == "offline":
        e = HashingEmbeddings()
        return e, e.nome

    try:
        e = NomicOllamaEmbeddings()
        e.embed_query("teste de conexão")  # sonda: falha cedo se o Ollama não responde
        return e, e.nome
    except Exception as erro:  # rede, auth, modelo não baixado...
        if backend == "nomic":
            raise RuntimeError(
                f"nomic-embed-text indisponível ({type(erro).__name__}: {erro}). "
                "Verifique OLLAMA_API_KEY/OLLAMA_BASE_URL ou rode `ollama pull nomic-embed-text`."
            ) from erro
        warnings.warn(
            "Ollama/nomic-embed-text inacessível — usando embeddings OFFLINE (hash). "
            "Resultados valem apenas como contingência; use EMBEDDINGS_BACKEND=nomic para a entrega.",
            stacklevel=2,
        )
        e = HashingEmbeddings()
        return e, e.nome
