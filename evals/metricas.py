"""
evals/metricas.py
-----------------
Métricas da avaliação RAG da Sprint 04 — RUBRICA MANUAL DETERMINÍSTICA (0–1), o
"fallback documentado" aceito pelo enunciado (§8) quando o RAGAS não pode ser
executado. Critérios completos e justificativa de equivalência: evals/RUBRICA.md.

Todas as funções são puras e reproduzíveis (sem LLM, sem rede).
"""

import re
from typing import Iterable, Optional

from src.rag.textutils import dividir_sentencas, normalizar, tokens_unicos

LIMIAR_SUPORTE = 0.70  # fração dos termos de uma afirmação que precisa estar no contexto


def _limpar_resposta(resposta: str) -> str:
    resposta = re.sub(r"\n*Fontes:.*$", "", resposta, flags=re.DOTALL)
    return re.sub(r"\[\d+\]", "", resposta)


def afirmacoes(resposta: str) -> list[str]:
    return dividir_sentencas(_limpar_resposta(resposta))


def _suportada(afirmacao: str, contexto_toks: set[str]) -> bool:
    toks = tokens_unicos(afirmacao)
    if not toks:
        return True
    numeros = {t for t in toks if t[0].isdigit()}
    if not numeros <= contexto_toks:       # todo número citado precisa existir no contexto
        return False
    palavras = toks - numeros
    if not palavras:
        return True
    return len(palavras & contexto_toks) / len(palavras) >= LIMIAR_SUPORTE


def fidelidade(resposta: str, contextos: Iterable[str], isolado: bool = False) -> Optional[float]:
    """
    Equivalente manual de RAGAS `faithfulness`: fração das afirmações da resposta
    sustentadas pelo contexto. Como no RAGAS, o contexto é o CONJUNTO dos trechos
    recuperados (isolado=False). Com isolado=True cada texto é testado sozinho —
    mais estrito; usado em `fidelidade_base` (a afirmação precisa estar num único
    documento da base autoritativa). None se não há afirmações (ex.: recusa).
    """
    afs = afirmacoes(resposta)
    if not afs:
        return None
    textos = list(contextos)
    if isolado:
        ctx_sets = [tokens_unicos(c) for c in textos] or [set()]
    else:
        ctx_sets = [tokens_unicos(" ".join(textos))]
    ok = sum(1 for a in afs if any(_suportada(a, cs) for cs in ctx_sets))
    return ok / len(afs)


def cobertura_pontos_chave(resposta: str, grupos: list[list[str]]) -> float:
    """
    Equivalente manual de RAGAS `answer_relevancy` neste domínio: fração dos pontos
    esperados (cada ponto = grupo de sinônimos) que a resposta efetivamente aborda.
    """
    if not grupos:
        return 1.0
    r = normalizar(resposta)
    return sum(1 for g in grupos if any(normalizar(x) in r for x in g)) / len(grupos)


def contexto_recall(arquivos_recuperados: list[str], docs_ouro: list[str]) -> float:
    """Fração dos documentos-ouro que aparecem entre os trechos recuperados."""
    if not docs_ouro:
        return 1.0
    return len(set(docs_ouro) & set(arquivos_recuperados)) / len(docs_ouro)


def contexto_precisao(arquivos_recuperados: list[str], docs_ouro: list[str]) -> float:
    """Fração dos trechos recuperados que vêm de documentos-ouro."""
    if not arquivos_recuperados:
        return 0.0
    return sum(1 for a in arquivos_recuperados if a in set(docs_ouro)) / len(arquivos_recuperados)


def mrr(arquivos_recuperados: list[str], docs_ouro: list[str]) -> float:
    for i, a in enumerate(arquivos_recuperados, start=1):
        if a in set(docs_ouro):
            return 1.0 / i
    return 0.0


def contem_proibido(resposta: str, proibidos: list[str]) -> bool:
    r = normalizar(resposta)
    return any(normalizar(p) in r for p in proibidos)
