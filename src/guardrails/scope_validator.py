"""
src/guardrails/scope_validator.py
-----------------------------------
Camada de guardrail DETERMINÍSTICA (sem LLM) para escopo e jailbreak.

Isso é defesa em profundidade: o system prompt (v2) já instrui o modelo a
recusar jailbreak e assuntos fora de escopo, e o schema `ConsultaRecarga`
classifica isso via `tipo_consulta=fora_de_escopo`. Este módulo adiciona uma
checagem por regex ANTES de qualquer chamada ao LLM, para os padrões mais
óbvios — reduzindo custo (evita chamada de API) e risco (não depende de o
modelo "se lembrar" da instrução em cada turno).

Nenhuma das duas camadas substitui a outra: regex pega os casos óbvios e
baratos de bloquear; a classificação via LLM cobre parafraseamentos e casos
ambíguos que um regex simples não alcança.
"""

import re

# ---------------------------------------------------------------------
# Fora de escopo: heurística leve por palavra-chave. Serve como apoio à
# classificação principal, feita pelo campo `tipo_consulta` do schema
# ConsultaRecarga (preenchido pelo LLM via structured output).
# ---------------------------------------------------------------------
PALAVRAS_FORA_DE_ESCOPO = [
    "receita de",
    "bolo de",
    "resultado do jogo",
    "campeonato",
    "horóscopo",
    "signo",
    "previsão do tempo",
    "quem foi eleito",
    "filme",
    "série de tv",
    "piada",
]

# ---------------------------------------------------------------------
# Jailbreak / prompt injection: padrões de tentativa de troca de papel,
# exposição do system prompt ou desativação de regras.
# ---------------------------------------------------------------------
PADROES_JAILBREAK = [
    r"ignore (todas )?as? instru[cç][oõ]es",
    r"esque[cç]a (tudo|suas? instru[cç][oõ]es)",
    r"revele (o|seu) system prompt",
    r"mostre (o|seu) prompt (completo|original|na [ií]ntegra)",
    r"palavra por palavra",
    r"finja (que )?(voc[eê] )?(n[aã]o )?[eé] (outra|uma) (ia|intelig[eê]ncia|pessoa)",
    r"assuma (o|a) (papel|identidade|persona) de",
    r"a partir de agora voc[eê]",
    r"voc[eê] n[aã]o [eé] mais o assistente",
    r"modo desenvolvedor",
    r"modo sem restri[cç][oõ]es",
    r"\bdan\b.*mode",
    r"jailbreak",
]

_RE_JAILBREAK = [re.compile(p, re.IGNORECASE) for p in PADROES_JAILBREAK]


def eh_tentativa_de_jailbreak(pergunta: str) -> bool:
    """Retorna True se a pergunta bater em algum padrão conhecido de jailbreak/injection."""
    texto = (pergunta or "").lower()
    return any(padrao.search(texto) for padrao in _RE_JAILBREAK)


def eh_fora_de_escopo(pergunta: str) -> bool:
    """
    Heurística de apoio: só usada como rede de segurança adicional. A
    classificação primária de escopo é feita pelo LLM via
    `ConsultaRecarga.tipo_consulta == TipoConsulta.FORA_DE_ESCOPO`.
    """
    texto = (pergunta or "").lower()
    return any(palavra in texto for palavra in PALAVRAS_FORA_DE_ESCOPO)
