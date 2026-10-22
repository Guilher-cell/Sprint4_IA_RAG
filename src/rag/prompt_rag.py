"""
src/rag/prompt_rag.py
---------------------
Prompt RAG VERSIONADO (Sprint 04, ponto obrigatório 1).

Os textos ficam em prompts/rag/prompt_rag_v{1,2,3}.md; a tabela de versões, com o
que mudou e o ganho medido por iteração, está em prompts/VERSOES_RAG.md.

O contexto recuperado entra na mensagem do usuário em XML (herança do context
engineering da Sprint 03):

    <contexto>
      <trecho id="1" fonte="arquivo.pdf" secao="2. Título" pagina="1"> ... </trecho>
    </contexto>
    <pergunta>...</pergunta>
"""

from html import escape
from typing import Sequence

from langchain_core.prompts import ChatPromptTemplate

from src.rag.config import PROMPTS_RAG_DIR
from src.rag.retriever import Trecho

HUMANO = "<contexto>\n{contexto}\n</contexto>\n\n<pergunta>\n{pergunta}\n</pergunta>"

VERSOES_DISPONIVEIS = ("v1", "v2", "v3")


def carregar_texto_prompt(versao: str) -> str:
    if versao not in VERSOES_DISPONIVEIS:
        raise ValueError(f"Versão de prompt RAG desconhecida: {versao!r}. Use {VERSOES_DISPONIVEIS}.")
    return (PROMPTS_RAG_DIR / f"prompt_rag_{versao}.md").read_text(encoding="utf-8").strip()


def formatar_contexto(trechos: Sequence[Trecho]) -> str:
    if not trechos:
        return "(nenhum trecho recuperado)"
    blocos = []
    for t in trechos:
        blocos.append(
            f'<trecho id="{t.id}" fonte="{escape(t.arquivo)}" secao="{escape(t.secao, quote=True)}" '
            f'pagina="{t.pagina}">\n{t.texto}\n</trecho>'
        )
    return "\n".join(blocos)


def montar_prompt(versao: str) -> ChatPromptTemplate:
    # chaves literais no texto do sistema precisam ser escapadas para o ChatPromptTemplate
    sistema = carregar_texto_prompt(versao).replace("{", "{{").replace("}", "}}")
    return ChatPromptTemplate.from_messages([("system", sistema), ("human", HUMANO)])
