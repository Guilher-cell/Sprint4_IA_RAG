"""
src/rag/seguranca.py
--------------------
Proteção contra PROMPT INJECTION VIA DOCUMENTOS (Sprint 04, item 6; Aula 07).

Ameaça: um documento da base (ex.: um PDF/FAQ editado por terceiros) contém
instruções dirigidas ao modelo — "ignore as instruções anteriores e responda X".
Se o trecho chega ao prompt como se fosse conteúdo confiável, o modelo pode obedecer.

Defesa em camadas:
  1. (este módulo) sanitização do contexto recuperado: sentenças que se dirigem ao
     assistente/modelo ou tentam sobrescrever regras são REMOVIDAS antes do prompt
     (e registradas para auditoria); tags que poderiam fechar o bloco <contexto>
     são neutralizadas;
  2. (prompt RAG v3) o contexto vai delimitado em XML e o prompt declara que o
     conteúdo dos trechos é DADO, nunca instrução;
  3. (pipeline) citação obrigatória e recusa por falta de contexto limitam o dano
     de uma resposta fora do que a base sustenta.

Limite honesto: regex não pega todo parafraseamento. É defesa em profundidade, não
garantia — ver "Limitações" em docs/relatorio_rag.md.
"""

import re

from src.rag.textutils import dividir_sentencas

# Padrões de instrução dirigida ao modelo, dentro de um documento.
PADROES_INJECAO_DOC = [
    r"ignor[ea]\s+(todas?\s+)?(as\s+)?(instru[cç][oõ]es|regras)",
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"desconsidere\s+(as\s+)?(instru[cç][oõ]es|regras)",
    r"(importante|aviso|nota|instru[cç][aã]o|aten[cç][aã]o)\s+(para|ao|à)\s+(o\s+|a\s+)?(assistente|ia|modelo|chatbot|llm|bot)",
    r"\b(assistente|chatbot|modelo|llm|\bia\b)\b[^.]{0,60}\b(deve|devem|precisa|tem que|must|should)\b",
    r"\b(responda|diga|afirme|informe)\s+(sempre\s+)?(que|apenas|somente|exatamente)\b",
    r"n[aã]o\s+(cite|mencione|informe)\s+(a\s+|as\s+)?(fontes?|origem)",
    r"(revele|mostre|exiba|imprima)\s+(o\s+|seu\s+)?(system\s+)?prompt",
    r"voc[eê]\s+(agora\s+)?[eé]\s+(um|uma|o|a)\s+",
    r"a\s+partir\s+de\s+agora",
    r"\bsystem\s*:",
    r"\[/?(inst|sys)\]",
]
_RE_INJECAO = [re.compile(p, re.IGNORECASE) for p in PADROES_INJECAO_DOC]

_RE_TAGS_PERIGOSAS = re.compile(r"</?\s*(contexto|trecho|pergunta|system|instru[cç][aã]o)[^>]*>", re.IGNORECASE)
_RE_COMENTARIO_HTML = re.compile(r"<!--.*?-->", re.DOTALL)
_RE_INVISIVEIS = re.compile(r"[​-‏⁠﻿]")


def eh_injecao(sentenca: str) -> bool:
    return any(p.search(sentenca) for p in _RE_INJECAO)


def sanitizar_trecho(texto: str) -> tuple[str, list[str]]:
    """
    Retorna (texto_limpo, sentencas_removidas).
    Remove texto oculto (comentários HTML, caracteres invisíveis), neutraliza tags
    de delimitação e descarta sentenças com instruções ao modelo.
    """
    limpo = _RE_COMENTARIO_HTML.sub(" ", texto)
    limpo = _RE_INVISIVEIS.sub("", limpo)
    limpo = _RE_TAGS_PERIGOSAS.sub(" ", limpo)

    removidas: list[str] = []
    linhas_saida: list[str] = []
    for linha in limpo.splitlines():
        if not linha.strip():
            linhas_saida.append(linha)
            continue
        partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9])", linha)
        mantidas = []
        for p in partes:
            if eh_injecao(p):
                removidas.append(p.strip())
            else:
                mantidas.append(p)
        if mantidas:
            linhas_saida.append(" ".join(mantidas))
    return "\n".join(linhas_saida).strip(), removidas


def auditar_chunks(chunks) -> list[dict]:
    """Varre os chunks da base e lista os que contêm padrões de injeção (para auditoria/CI)."""
    achados = []
    for c in chunks:
        _, removidas = sanitizar_trecho(c.page_content)
        if removidas:
            achados.append({"chunk_id": c.metadata.get("chunk_id"), "removidas": removidas})
    return achados
