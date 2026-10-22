"""
src/rag/gerador_offline.py
--------------------------
Gerador EXTRATIVO determinístico — contingência quando não há LLM acessível
(sem GROQ_API_KEY ou sem rede).

IMPORTANTE (transparência): isto NÃO é um LLM. Ele escolhe, dentre as sentenças
dos trechos recuperados, as que mais cobrem os termos da pergunta e as devolve
com citação. Serve para (a) o app/CLI funcionarem sem internet e (b) medir, de
forma 100% reproduzível, a parte do sistema que NÃO depende do LLM (chunking,
embeddings, retrieval, guardrails, sanitização, citação). Scores gerados com ele
são rotulados "offline" nos resultados e relatórios; a avaliação com LLM real é
feita por `evals/run_eval_rag.py --modo live`.

Cada versão de prompt RAG é simulada pela política equivalente abaixo (o que o
texto do prompt pede ao LLM, aqui vira parâmetro):
  v1: 2 sentenças, sem citação.
  v2: 3 sentenças, citação [n] por sentença.
  v3: 3 sentenças, citação [n], deduplicação, linha "Fontes:" e prioridade a
      sentenças do trecho mais bem ranqueado quando há empate.
"""

import math
from dataclasses import dataclass
from typing import Sequence

from src.rag.retriever import Trecho
from src.rag.textutils import dividir_sentencas, tokens, tokens_unicos


@dataclass(frozen=True)
class PoliticaOffline:
    n_sentencas: int
    citar: bool
    linha_fontes: bool
    cobertura_minima: float


POLITICAS = {
    "v1": PoliticaOffline(2, False, False, 0.10),
    "v2": PoliticaOffline(3, True, False, 0.15),
    "v3": PoliticaOffline(3, True, True, 0.15),
}


def gerar(pergunta: str, trechos: Sequence[Trecho], versao_prompt: str) -> tuple[str, list[int]]:
    """Retorna (resposta, ids_de_trechos_citados). Resposta vazia se nada cobre a pergunta."""
    pol = POLITICAS[versao_prompt]
    q_toks = tokens_unicos(pergunta)
    if not q_toks or not trechos:
        return "", []

    candidatas: list[tuple[int, int, str]] = []  # (id_trecho, posição, sentença)
    for t in trechos:
        for pos, s in enumerate(dividir_sentencas(t.texto)):
            candidatas.append((t.id, pos, s))
    if not candidatas:
        return "", []

    # IDF sobre as sentenças candidatas: termos raros da pergunta pesam mais
    df: dict[str, int] = {}
    toks_sent = [tokens_unicos(s) for _, _, s in candidatas]
    for ts in toks_sent:
        for tk in ts:
            df[tk] = df.get(tk, 0) + 1
    n = len(candidatas)
    idf = {tk: math.log((n + 1) / (df.get(tk, 0) + 0.5)) + 1.0 for tk in q_toks}
    total_idf = sum(idf.values())

    pontuadas = []
    for (tid, pos, s), ts in zip(candidatas, toks_sent):
        cobertura = sum(idf[tk] for tk in q_toks if tk in ts) / total_idf
        bonus = (0.02 / tid) if pol.linha_fontes else 0.0  # v3: leve preferência pelo trecho mais bem ranqueado
        pontuadas.append((cobertura + bonus, cobertura, tid, pos, s))
    pontuadas.sort(key=lambda x: x[0], reverse=True)

    escolhidas, vistas = [], set()
    for _, cob, tid, pos, s in pontuadas:
        if cob < pol.cobertura_minima:
            break
        chave = frozenset(tokens(s))
        if pol.linha_fontes and chave in vistas:
            continue
        vistas.add(chave)
        escolhidas.append((tid, pos, s))
        if len(escolhidas) >= pol.n_sentencas:
            break
    if not escolhidas:
        return "", []

    escolhidas.sort(key=lambda x: (x[0], x[1]))  # ordem natural de leitura
    partes, citados = [], []
    for tid, _, s in escolhidas:
        s = s.rstrip()
        if pol.citar:
            partes.append(f"{s if s[-1] in '.!?' else s + '.'} [{tid}]")
            if tid not in citados:
                citados.append(tid)
        else:
            partes.append(s)
    resposta = " ".join(partes)
    if pol.linha_fontes and citados:
        resposta += "\n\nFontes: " + ", ".join(f"[{i}]" for i in citados)
    return resposta, citados
