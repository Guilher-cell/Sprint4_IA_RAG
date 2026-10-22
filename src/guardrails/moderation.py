"""
src/guardrails/moderation.py
-------------------------------
Guardrail de DOMÍNIO SENSÍVEL, exigido explicitamente pela Sprint 03 (§6):

    "recusa de aconselhamento jurídico, financeiro ou de segurança elétrica
    sem orientar profissional habilitado"

Diferente do scope_validator (que decide se algo está dentro/fora do
escopo GoodWe ChargeOps), este módulo trata de perguntas que ESTÃO
relacionadas ao condomínio/carregamento, mas pedem um tipo de conselho que
o assistente não deve dar diretamente — apenas orientar a busca por um
profissional habilitado.

Roda ANTES da chain de extração de intenção: se bater em um padrão sensível,
o pipeline retorna a mensagem de orientação sem gastar uma chamada de LLM
para "decidir" isso.
"""

import re
from typing import Optional

_PADROES_ELETRICOS_PERIGOSOS = [
    r"mexer no disjuntor sozinho",
    r"abrir o quadro el[eé]trico",
    r"fio desencapado",
    r"choque el[eé]trico",
    r"desmontar o carregador",
    r"ligar o carregador direto na (tomada|rede)",
]

_PADROES_JURIDICOS = [
    r"processar\s+(o\s+|a\s+)?s[ií]ndico",
    # cobre "processar ele/ela na justiça" quando o contexto já é sobre o
    # síndico (a pergunta inteira é passada para _bate_algum, não só esta
    # frase) — ver docs/relatorio_evolucao.md, Problema 8, para o caso real
    # que expôs essa lacuna (regex exigia adjacência literal "o síndico").
    r"processar\s+(ele|ela)\b.{0,40}justi[çc]a",
    r"a[cç][aã]o judicial",
    r"processo (judicial|contra)",
    r"advogado",
    r"multa condominial indevida",
    r"direito de (mor|uso)",
]

_PADROES_FINANCEIROS = [
    r"reajuste (da|de) taxa condominial",
    r"financiamento",
    r"investir",
    r"emprestar dinheiro",
    r"parcelar a d[ií]vida do cond[oô]minio",
]

_MENSAGENS = {
    "eletrico": (
        "Por segurança, não posso orientar diretamente uma intervenção elétrica manual "
        "no quadro geral ou nos carregadores. Esse tipo de procedimento deve ser feito "
        "por um eletricista habilitado ou pelo suporte técnico GoodWe — posso te ajudar "
        "a descrever o problema para acionar o suporte correto."
    ),
    "juridico": (
        "Essa é uma questão jurídica e está fora do que posso orientar com segurança. "
        "Recomendo buscar um advogado ou a administração do condomínio para tratar disso "
        "formalmente."
    ),
    "financeiro": (
        "Essa é uma decisão financeira que está fora do escopo deste assistente. Recomendo "
        "consultar um profissional de contabilidade/finanças ou a administração do "
        "condomínio antes de decidir."
    ),
}


def _bate_algum(padroes: list[str], texto: str) -> bool:
    return any(re.search(p, texto, re.IGNORECASE) for p in padroes)


def verificar_dominio_sensivel(pergunta: str) -> Optional[str]:
    """
    Retorna a mensagem de orientação a profissional habilitado se a pergunta
    bater em um padrão jurídico/financeiro/elétrico sensível; caso contrário,
    retorna None (segue o fluxo normal do pipeline).
    """
    texto = pergunta or ""
    if _bate_algum(_PADROES_ELETRICOS_PERIGOSOS, texto):
        return _MENSAGENS["eletrico"]
    if _bate_algum(_PADROES_JURIDICOS, texto):
        return _MENSAGENS["juridico"]
    if _bate_algum(_PADROES_FINANCEIROS, texto):
        return _MENSAGENS["financeiro"]
    return None
