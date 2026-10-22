"""
src/rag/pipeline.py
-------------------
Pipeline RAG end-to-end da Sprint 04 (Aula 06), com grounding, citação e guardrails:

    pergunta
      │
      ▼ (1) guardrails determinísticos da Sprint 03 (jailbreak / domínio sensível / fora de escopo)
      ▼ (2) retriever: ChromaDB persistente (nomic-embed-text) → [rerank] → top-k
      ▼ (3) recusa por falta de contexto (limiar de relevância) e por código de produto ausente
      ▼ (4) sanitização do contexto (prompt injection via documentos)
      ▼ (5) geração: prompt RAG versionado | LLM (Groq)   — ou gerador extrativo offline
      ▼ (6) pós-validação de citação: toda resposta cita fonte(s) existente(s)
    RagResposta (resposta, fontes citadas, trechos recuperados, camada que decidiu)

Cada etapa é ligada/desligada por `RagConfig`, o que permite medir o ganho de
cada decisão nas iterações (evals/run_eval_rag.py).
"""

import os
import re
import time
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field

from src.guardrails.moderation import verificar_dominio_sensivel
from src.guardrails.scope_validator import eh_fora_de_escopo, eh_tentativa_de_jailbreak
from src.rag import gerador_offline
from src.rag.chunking import dividir
from src.rag.config import CHROMA_DIR, RagConfig, config_padrao, limiar_para
from src.rag.embeddings import get_embeddings
from src.rag.loader import carregar_base, carregar_system_prompt_v1
from src.rag.prompt_rag import carregar_texto_prompt, formatar_contexto, montar_prompt
from src.rag.retriever import Trecho, codigos_ausentes, recuperar
from src.rag.seguranca import sanitizar_trecho
from src.rag.vector_store import abrir_ou_criar

MSG_SEM_CONTEXTO = (
    "Não encontrei essa informação na base de conhecimento do EV ChargeOps, então não posso "
    "responder sem correr o risco de inventar. Posso ajudar com agendamento, consumo e rateio, "
    "diagnóstico de carregadores, orquestração de potência e regras do condomínio."
)
MSG_FORA_ESCOPO = (
    "Esse assunto está fora do escopo deste assistente, que trata de carregamento de veículos "
    "elétricos em condomínios com o GoodWe EV ChargeOps. Posso ajudar com agendamento, consumo, "
    "diagnóstico de carregadores e regras de uso."
)
MSG_JAILBREAK = (
    "Não posso alterar meu papel, ignorar minhas regras nem revelar minhas instruções internas. "
    "Posso ajudar com dúvidas sobre o GoodWe EV ChargeOps."
)
MSG_ENTIDADE_AUSENTE = (
    "O produto/modelo citado ({codigos}) não consta na base de conhecimento, e não vou inventar "
    "especificações. Consulte a documentação oficial do fabricante ou o suporte técnico GoodWe."
)

PROVIDERS = {"offline", "groq_oss", "groq_secundario", "ollama"}


class Fonte(BaseModel):
    id: int
    arquivo: str
    secao: str
    pagina: int
    trecho: str


class RagResposta(BaseModel):
    pergunta: str
    resposta: str
    fontes: list[Fonte] = Field(default_factory=list, description="Trechos efetivamente citados na resposta.")
    trechos: list[dict] = Field(default_factory=list, description="Trechos recuperados enviados ao prompt.")
    recusou: bool = False
    camada: str = ""            # quem decidiu: guardrail_*, retrieval_*, llm, offline_extrativo...
    cita_nativo: bool = False   # o gerador citou por conta própria (sem a pós-validação)?
    citacao_forcada: bool = False
    modelo: str = ""
    backend_embeddings: str = ""
    iteracao: str = ""
    latencia_s: float = 0.0
    melhor_score: Optional[float] = None


def resolver_provider(provider: Optional[str]) -> str:
    provider = (provider or os.environ.get("LLM_PROVIDER_RAG", "auto")).lower()
    if provider == "auto":
        return "groq_oss" if os.environ.get("GROQ_API_KEY") else "offline"
    if provider not in PROVIDERS:
        raise ValueError(f"Provider desconhecido: {provider!r}. Use auto ou {sorted(PROVIDERS)}.")
    return provider


class RagPipeline:
    def __init__(
        self,
        cfg: Optional[RagConfig] = None,
        provider: Optional[str] = None,
        embeddings_backend: Optional[str] = None,
        persist_dir: Optional[Path] = None,
        extras: Optional[Iterable[Path]] = None,
        limiar: Optional[float] = None,
    ):
        self.cfg = cfg or config_padrao()
        self.provider = resolver_provider(provider)
        self.embeddings, self.backend = get_embeddings(embeddings_backend)
        self.limiar = limiar if limiar is not None else limiar_para(self.backend)

        docs = carregar_system_prompt_v1() if self.cfg.base == "system_prompt_v1" else carregar_base(extras=extras)
        self.chunks = dividir(docs, self.cfg.chunk_size, self.cfg.chunk_overlap, self.cfg.prefixar_secao,
                              self.cfg.chunk_por_secao)
        extra = (f"{self.cfg.base}|{self.cfg.chunk_size}|{self.cfg.chunk_overlap}|"
                 f"{self.cfg.prefixar_secao}|{self.cfg.chunk_por_secao}")
        self.store = abrir_ou_criar(
            self.chunks, self.embeddings, self.backend,
            persist_dir=persist_dir or CHROMA_DIR, prefixo=f"goodwe_{self.cfg.base}", extra=extra,
        )
        self._llm = None
        self._chain = None
        self.modelo = "extrativo-offline" if self.provider == "offline" else self.provider

    # ------------------------------------------------------------------ LLM
    def _cadeia(self):
        if self._chain is None:
            from langchain_core.output_parsers import StrOutputParser

            from src.chain.llm_factory import get_llm

            self._llm = get_llm(
                self.provider, temperature=self.cfg.temperature, top_p=self.cfg.top_p,
                max_tokens=self.cfg.max_tokens,
            )
            self.modelo = getattr(self._llm, "model_name", None) or getattr(self._llm, "model", self.provider)
            self._chain = montar_prompt(self.cfg.prompt_version) | self._llm | StrOutputParser()
        return self._chain

    def _gerar_llm(self, pergunta: str, trechos: list[Trecho]) -> str:
        if self.cfg.base == "system_prompt_v1":
            # Baseline Sprints 1/2 com LLM: system prompt v1 inteiro, sem recuperação.
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate

            from src.chain.llm_factory import get_llm

            sistema = carregar_texto_prompt_legado() + (
                "\n\nNOTA DA AVALIAÇÃO: nesta execução NÃO há ferramentas (tools) disponíveis. "
                "Responda apenas em texto, sem tentar chamar funções."
            )
            sistema = sistema.replace("{", "{{").replace("}", "}}")
            llm = get_llm(self.provider, temperature=self.cfg.temperature, top_p=self.cfg.top_p,
                          max_tokens=self.cfg.max_tokens)
            self.modelo = getattr(llm, "model_name", None) or getattr(llm, "model", self.provider)
            try:
                return (ChatPromptTemplate.from_messages([("system", sistema), ("human", "{pergunta}")])
                        | llm | StrOutputParser()).invoke({"pergunta": pergunta})
            except Exception as erro:
                # O prompt legado descreve ferramentas; se o modelo tentar chamá-las mesmo assim, a Groq
                # responde 400 `tool_use_failed`. Não há ferramenta aqui: o baseline não produziu resposta
                # textual válida, e isso é registrado como tal (em vez de derrubar a avaliação).
                if "tool_use_failed" in str(erro):
                    return "(baseline: o modelo tentou chamar uma ferramenta inexistente e não respondeu em texto)"
                raise
        return self._cadeia().invoke({"contexto": formatar_contexto(trechos), "pergunta": pergunta})

    # ------------------------------------------------------------- helpers
    def _recusa(self, pergunta, texto, camada, t0, trechos=None, score=None) -> RagResposta:
        return RagResposta(
            pergunta=pergunta, resposta=texto, recusou=True, camada=camada,
            trechos=[t.to_dict() for t in (trechos or [])], modelo=self.modelo,
            backend_embeddings=self.backend, iteracao=self.cfg.nome,
            latencia_s=round(time.perf_counter() - t0, 4), melhor_score=score,
        )

    def recuperar(self, pergunta: str) -> list[Trecho]:
        return recuperar(self.store, pergunta, self.cfg.k, self.cfg.rerank, self.cfg.fetch_k_mult)

    # ----------------------------------------------------------------- ask
    def ask(self, pergunta: str) -> RagResposta:
        t0 = time.perf_counter()
        pergunta = (pergunta or "").strip()
        if not pergunta:
            return self._recusa(pergunta, "Digite uma pergunta sobre o EV ChargeOps.", "entrada_vazia", t0)

        # (1) guardrails determinísticos (Sprint 03)
        if self.cfg.guardrails_regex:
            if eh_tentativa_de_jailbreak(pergunta):
                return self._recusa(pergunta, MSG_JAILBREAK, "guardrail_jailbreak", t0)
            sensivel = verificar_dominio_sensivel(pergunta)
            if sensivel:
                return self._recusa(pergunta, sensivel, "guardrail_dominio_sensivel", t0)
            if eh_fora_de_escopo(pergunta):
                return self._recusa(pergunta, MSG_FORA_ESCOPO, "guardrail_escopo", t0)

        # (2) retrieval
        trechos = self.recuperar(pergunta)
        melhor = trechos[0].score if trechos else None

        # (3) recusa por falta de contexto / entidade ausente
        if self.cfg.usar_limiar and (not trechos or melhor < self.limiar):
            return self._recusa(pergunta, MSG_SEM_CONTEXTO, "retrieval_sem_contexto", t0, trechos, melhor)
        if self.cfg.checar_entidades:
            faltando = codigos_ausentes(pergunta, trechos)
            if faltando:
                return self._recusa(
                    pergunta, MSG_ENTIDADE_AUSENTE.format(codigos=", ".join(faltando)),
                    "retrieval_entidade_ausente", t0, trechos, melhor,
                )

        # (4) sanitização do contexto (prompt injection via documentos)
        if self.cfg.sanitizar_contexto:
            for t in trechos:
                t.texto, t.removidos = sanitizar_trecho(t.texto)
                t.sanitizado = bool(t.removidos)
            trechos = [t for t in trechos if t.texto.strip()]
            for i, t in enumerate(trechos, start=1):
                t.id = i

        # (5) geração
        if self.provider == "offline":
            texto, citados = gerador_offline.gerar(pergunta, trechos, self.cfg.prompt_version)
            camada = "offline_extrativo"
            cita_nativo = bool(citados)
            if not texto:
                return self._recusa(pergunta, MSG_SEM_CONTEXTO, "gerador_sem_cobertura", t0, trechos, melhor)
        else:
            texto = (self._gerar_llm(pergunta, trechos) or "").strip()
            camada = "llm"
            texto = normalizar_citacoes(texto)
            if not texto:  # ex.: orçamento de tokens esgotado pelo raciocínio do modelo
                return self._recusa(
                    pergunta,
                    "O modelo não devolveu texto (possível limite de tokens esgotado). Tente novamente "
                    "ou aumente max_tokens.", "llm_resposta_vazia", t0, trechos, melhor,
                )
            ids_validos = {t.id for t in trechos}
            citados = [int(n) for n in re.findall(r"\[(\d+)\]", texto) if int(n) in ids_validos]
            cita_nativo = bool(citados)
            if texto.lower().startswith("não encontrei essa informação"):
                return self._recusa(pergunta, texto, "llm_recusa", t0, trechos, melhor)

        # (6) pós-validação da citação
        forcada = False
        if self.cfg.exigir_citacao:
            ids_validos = {t.id for t in trechos}
            texto = re.sub(r"\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) in ids_validos else "", texto)
            citados = [i for i in dict.fromkeys(citados) if i in ids_validos]
            if not citados and trechos:
                citados = [t.id for t in trechos[:2]]
                texto += "\n\nFontes: " + ", ".join(f"[{i}]" for i in citados)
                forcada = True

        fontes = [
            Fonte(id=t.id, arquivo=t.arquivo, secao=t.secao, pagina=t.pagina, trecho=t.texto)
            for t in trechos if t.id in set(citados)
        ]
        return RagResposta(
            pergunta=pergunta, resposta=texto, fontes=fontes, trechos=[t.to_dict() for t in trechos],
            recusou=False, camada=camada, cita_nativo=cita_nativo, citacao_forcada=forcada,
            modelo=self.modelo, backend_embeddings=self.backend, iteracao=self.cfg.nome,
            latencia_s=round(time.perf_counter() - t0, 4), melhor_score=melhor,
        )


def normalizar_citacoes(texto: str) -> str:
    """
    Uniformiza marcadores de citação para o formato [n] antes da pós-validação.
    Observado ao vivo (gpt-oss-120b, prompt v2): o modelo citou com `【1】` (colchetes largos) em 12 de 20
    respostas; sem normalização o validador não os reconhecia e a citação era *forçada* pelo código.
    Também aceita `[1, 2]` e `[1][2]`.
    """
    texto = re.sub(r"[【\[]\s*(\d+(?:\s*[,;]\s*\d+)*)\s*[】\]]",
                   lambda m: " ".join(f"[{n}]" for n in re.findall(r"\d+", m.group(1))), texto)
    return texto


def carregar_texto_prompt_legado() -> str:
    from src.rag.config import RAIZ

    return (RAIZ / "prompts" / "system_prompt_v1.md").read_text(encoding="utf-8")
