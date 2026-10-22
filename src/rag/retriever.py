"""
src/rag/retriever.py
--------------------
Recuperação de trechos (Aulas 05–07).

Fluxo: busca por similaridade de cosseno no ChromaDB (fetch_k candidatos)
→ [opcional] rerank lexical híbrido → top-k.

Rerank lexical híbrido (diferencial opcional do enunciado): score final =
0.7 · cosseno + 0.3 · cobertura lexical (fração dos termos da pergunta presentes
no trecho). Corrige casos em que o embedding aproxima trechos "do mesmo assunto"
mas que não contêm o termo decisivo da pergunta (ex.: "LED amarelo").
"""

import re
from dataclasses import asdict, dataclass, field
from typing import Optional

from src.rag.textutils import tokens_unicos

PESO_COSSENO = 0.7
PESO_LEXICAL = 0.3


@dataclass
class Trecho:
    id: int                 # posição (1-based) usada na citação [n]
    texto: str
    arquivo: str
    secao: str
    pagina: int
    score: float            # score usado para ordenar/decidir (híbrido se rerank)
    cosseno: float
    chunk_id: str = ""
    sanitizado: bool = False
    removidos: list = field(default_factory=list)

    def fonte(self) -> str:
        return f"{self.arquivo} · {self.secao} · p. {self.pagina}"

    def to_dict(self) -> dict:
        return asdict(self)


def _cobertura(pergunta_toks: set[str], texto: str) -> float:
    if not pergunta_toks:
        return 0.0
    return len(pergunta_toks & tokens_unicos(texto)) / len(pergunta_toks)


def recuperar(store, pergunta: str, k: int, rerank: bool = False, fetch_k_mult: int = 3) -> list[Trecho]:
    # Busca sempre mais candidatos que k: empates exatos de score na fronteira do top-k
    # (o índice devolve um dos empatados de forma arbitrária) são resolvidos abaixo, de
    # forma determinística, e não pelo índice.
    fetch_k = max(k, k * fetch_k_mult)
    resultados = store.similarity_search_with_score(pergunta, k=fetch_k)  # (Document, distância cosseno)

    pergunta_toks = tokens_unicos(pergunta)
    candidatos: list[Trecho] = []
    for doc, dist in resultados:
        cos = 1.0 - float(dist)
        score = cos
        if rerank:
            score = PESO_COSSENO * cos + PESO_LEXICAL * _cobertura(pergunta_toks, doc.page_content)
        candidatos.append(
            Trecho(
                id=0,
                texto=doc.page_content,
                arquivo=doc.metadata.get("arquivo", "?"),
                secao=doc.metadata.get("secao", ""),
                pagina=int(doc.metadata.get("pagina", 1)),
                score=score,
                cosseno=cos,
                chunk_id=doc.metadata.get("chunk_id", ""),
            )
        )
    # desempate determinístico: empates exatos de score (chunks com texto quase idêntico
    # por causa do overlap) são ordenados por chunk_id, não pela ordem interna do índice HNSW
    candidatos.sort(key=lambda t: (-round(t.score, 6), t.chunk_id))
    top = candidatos[:k]
    for i, t in enumerate(top, start=1):
        t.id = i
    return top


# Códigos de produto/modelo (ex.: "HC-22000", "X9000"): letras seguidas de dígitos.
_RE_CODIGO = re.compile(r"\b[a-zA-Z]{1,6}-?\d{2,}[a-zA-Z0-9-]*\b")


def codigos_ausentes(pergunta: str, trechos: list[Trecho]) -> list[str]:
    """
    Códigos de produto citados na pergunta que não aparecem em nenhum trecho
    recuperado. Serve para o requisito "não inventar especificações de produtos
    não inseridas na base": se o usuário pergunta sobre o 'HC-22000' e a base não
    tem esse código, o assistente recusa em vez de responder com dados de outro modelo.
    """
    corpus = " ".join(t.texto for t in trechos).lower()
    return [c for c in _RE_CODIGO.findall(pergunta) if c.lower() not in corpus]
