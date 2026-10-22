"""
src/schemas/consulta_recarga.py
--------------------------------
Schema Pydantic v2 do domínio EV usado na etapa de EXTRAÇÃO DE INTENÇÃO da
chain LCEL (Sprint 03, Aula 03 - Structured Output).

Substitui o papel que o function calling (tools.py) tinha na Sprint 2: em vez
do modelo decidir livremente "chamar uma tool", ele agora preenche um objeto
estruturado e validado (ConsultaRecarga), que o pipeline usa para decidir,
de forma determinística, qual lookup de dados mockados fazer (src/data/mock_data.py).

Isso corrige, por construção, o problema real observado no Teste 5 da Sprint 2
(ver docs/relatorio_evolucao.md, seção "Problemas encontrados"): o modelo às
vezes descrevia function calling em texto sem de fato emitir a tool_call,
resultando em resposta genérica ("não consegui consultar"). Com structured
output, a extração de intenção é obrigatória e validada por schema — não é
uma decisão opcional do modelo.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Persona(str, Enum):
    SINDICO = "sindico"
    MORADOR = "morador"
    TECNICO_ZELADOR = "tecnico_zelador"
    DESCONHECIDA = "desconhecida"


class TipoConsulta(str, Enum):
    CONSUMO = "consumo"
    STATUS_CARREGADOR = "status_carregador"
    AGENDAMENTOS = "agendamentos"
    ORQUESTRACAO_POTENCIA = "orquestracao_potencia"
    OUTRO_DENTRO_ESCOPO = "outro_dentro_escopo"
    FORA_DE_ESCOPO = "fora_de_escopo"


class ConsultaRecarga(BaseModel):
    """
    Representa a intenção extraída da pergunta do usuário, no domínio do
    sistema GoodWe EV ChargeOps. Preenchido pelo LLM via
    `llm.with_structured_output(ConsultaRecarga)` (LCEL, Aula 03).
    """

    persona: Persona = Field(
        description=(
            "Persona identificada na pergunta ou no histórico da conversa: "
            "'sindico', 'morador', 'tecnico_zelador' ou 'desconhecida' se não "
            "for possível inferir."
        )
    )
    tipo_consulta: TipoConsulta = Field(
        description=(
            "Categoria da pergunta. Use 'fora_de_escopo' para qualquer "
            "assunto que não seja carregamento de EVs / GoodWe ChargeOps."
        )
    )
    unidade: Optional[str] = Field(
        default=None,
        description=(
            "Identificação da unidade/apartamento mencionada explicitamente "
            "na pergunta ou no histórico (ex.: '101'). Nunca inventar."
        ),
    )
    carregador: Optional[str] = Field(
        default=None,
        description=(
            "Identificação do carregador/box mencionado explicitamente "
            "(ex.: 'box 7'). Nunca inventar."
        ),
    )
    resumo_pedido: str = Field(
        description="Resumo em até 200 caracteres do que o usuário está pedindo.",
        max_length=200,
    )

    @field_validator("unidade")
    @classmethod
    def normalizar_unidade(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("carregador")
    @classmethod
    def normalizar_carregador(cls, v: Optional[str]) -> Optional[str]:
        """
        Normaliza variações como '7', 'Box7', 'BOX 7' para o formato
        canônico usado na base mockada ('box 7'), evitando falhas de lookup
        por diferença de formatação.
        """
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        if v.isdigit():
            return f"box {v}"
        if v.startswith("box") and not v.startswith("box "):
            resto = v[3:].strip()
            return f"box {resto}" if resto else v
        return v

    @field_validator("resumo_pedido")
    @classmethod
    def resumo_nao_vazio(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("resumo_pedido não pode ser vazio.")
        return v
