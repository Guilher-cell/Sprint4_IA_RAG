"""
src/rag/config.py
-----------------
Configurações do pipeline RAG e definição das ITERAÇÕES avaliadas na Sprint 04.

Cada iteração muda um conjunto pequeno e explícito de decisões (chunking, k,
reranking, guardrails, versão do prompt RAG) para que o ganho de score possa ser
atribuído a mudanças concretas — ver prompts/VERSOES_RAG.md e docs/relatorio_rag.md.

`baseline_s12` NÃO usa a base nova: representa o chatbot das Sprints 1/2, cujo
único "conhecimento" era o system prompt (prompts/system_prompt_v1.md), sem
recuperação, sem citação de fonte e sem recusa por falta de contexto.
"""

import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
KB_DIR = RAIZ / "data" / "knowledge_base"
CHROMA_DIR = RAIZ / "data" / "chroma_db"
PROMPTS_RAG_DIR = RAIZ / "prompts" / "rag"

# Limiar de relevância (similaridade de cosseno do melhor trecho) por backend de
# embeddings. Os valores devem ser recalibrados com `python evals/calibrar_limiar.py`
# ao trocar de backend/modelo. Podem ser sobrescritos por RAG_LIMIAR no .env.
LIMIAR_PADRAO_POR_BACKEND = {
    "nomic-embed-text": 0.55,
    "offline-hash": 0.22,
}


@dataclass(frozen=True)
class RagConfig:
    nome: str
    descricao: str
    chunk_size: int = 1200
    chunk_overlap: int = 0
    chunk_por_secao: bool = False     # nenhum chunk cruza a fronteira de um título
    prefixar_secao: bool = False      # injeta "[Seção: ...]" no texto do chunk
    k: int = 3                        # top-k enviado ao prompt
    fetch_k_mult: int = 3             # candidatos buscados = k * mult (para rerank)
    rerank: bool = False              # rerank lexical híbrido (diferencial opcional)
    usar_limiar: bool = False         # recusa se o melhor trecho for pouco relevante
    checar_entidades: bool = False    # recusa se a pergunta cita código de produto ausente
    guardrails_regex: bool = False    # jailbreak / domínio sensível / fora de escopo (Sprint 03)
    sanitizar_contexto: bool = False  # remove instruções embutidas em documentos
    exigir_citacao: bool = False      # pós-validação: toda resposta cita fonte
    prompt_version: str = "v1"
    base: str = "kb"                  # "kb" (base nova) | "system_prompt_v1" (baseline S1/2)
    # parâmetros de geração (relatorio_modelos.md)
    temperature: float = 0.0
    top_p: float = 1.0
    # 1024 (e não os 600 das Sprints 1-3): nos modelos de raciocínio gpt-oss (Groq) os tokens de
    # "reasoning" contam no limite de saída; com 600 a resposta pode sair truncada ou vazia.
    max_tokens: int = 1024

    def to_dict(self) -> dict:
        return asdict(self)


ITERACOES: dict[str, RagConfig] = {
    "baseline_s12": RagConfig(
        nome="baseline_s12",
        descricao="Sprints 1/2: conhecimento = system prompt v1; sem citação, sem recusa por contexto.",
        base="system_prompt_v1", chunk_size=1000, chunk_overlap=0, k=3, prompt_version="v1",
    ),
    "iter1": RagConfig(
        nome="iter1",
        descricao="RAG ingênuo: chunks 1200/0, k=3, prompt v1, sem guardrails.",
        chunk_size=1200, chunk_overlap=0, k=3, prompt_version="v1",
    ),
    "iter2": RagConfig(
        nome="iter2",
        descricao="Chunks 600/100 por seção (com título no texto), k=4, guardrails Sprint 03, citação obrigatória, prompt v2.",
        chunk_size=600, chunk_overlap=100, chunk_por_secao=True, prefixar_secao=True, k=4,
        guardrails_regex=True, exigir_citacao=True, prompt_version="v2",
    ),
    "iter3": RagConfig(
        nome="iter3",
        descricao="iter2 + rerank lexical, limiar de relevância, checagem de entidades, sanitização de contexto, prompt v3.",
        chunk_size=600, chunk_overlap=100, chunk_por_secao=True, prefixar_secao=True, k=4, rerank=True,
        usar_limiar=True, checar_entidades=True, guardrails_regex=True,
        sanitizar_contexto=True, exigir_citacao=True, prompt_version="v3",
    ),
}


def config_padrao() -> RagConfig:
    """Configuração usada pela interface e pelo CLI (a melhor iteração)."""
    return ITERACOES[os.environ.get("RAG_ITERACAO", "iter3")]


def com_parametros(cfg: RagConfig, **mudancas) -> RagConfig:
    return replace(cfg, **mudancas)


def limiar_para(backend: str) -> float:
    env = os.environ.get("RAG_LIMIAR")
    if env:
        return float(env)
    return LIMIAR_PADRAO_POR_BACKEND.get(backend, 0.5)
