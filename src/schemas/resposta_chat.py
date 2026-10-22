"""
src/schemas/resposta_chat.py
------------------------------
Schema Pydantic v2 da resposta final do chatbot (Sprint 03, Aula 03).

A chain final (`FINAL_ANSWER_PROMPT | llm.with_structured_output(RespostaChat)`)
retorna sempre um objeto validado, em vez de texto livre. Isso permite ao
`main_v2.py` decidir programaticamente se deve exibir um aviso de escalada
humana, sem depender de o modelo "lembrar" de mencionar isso em prosa.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RespostaChat(BaseModel):
    mensagem: str = Field(
        description=(
            "Resposta final ao usuário, em português brasileiro, seguindo o "
            "FORMATO_DE_SAIDA do system prompt (3 a 6 frases ou parágrafo curto "
            "+ lista numerada quando for passo a passo)."
        )
    )
    precisa_escalar: bool = Field(
        default=False,
        description="True se a resposta recomenda escalada para suporte humano.",
    )
    destino_escalada: Optional[str] = Field(
        default=None,
        description=(
            "Para onde escalar quando precisa_escalar=True (ex.: 'suporte "
            "técnico GoodWe', 'administração do condomínio', 'eletricista "
            "habilitado', 'advogado/contador')."
        ),
    )
    fonte_dados: Optional[str] = Field(
        default=None,
        description=(
            "Origem dos dados usados para compor a resposta (ex.: "
            "'mock_consumo', 'mock_status_carregador', 'guardrail_escopo', "
            "'guardrail_jailbreak', 'guardrail_dominio_sensivel')."
        ),
    )

    @field_validator("mensagem")
    @classmethod
    def mensagem_valida(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("A resposta final não pode ser vazia.")
        if len(v) > 1500:
            v = v[:1500].rstrip() + "..."
        return v

    @field_validator("destino_escalada")
    @classmethod
    def normalizar_destino(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @model_validator(mode="after")
    def validar_consistencia_escalada(self) -> "RespostaChat":
        """
        Regra de domínio (Sprint 03, §6 do enunciado): toda resposta que
        recomenda escalada humana precisa dizer para onde escalar — evita
        respostas incompletas do tipo "procure ajuda especializada" sem
        indicar qual especialidade/canal.
        """
        if self.precisa_escalar and not self.destino_escalada:
            raise ValueError(
                "Quando precisa_escalar=True, destino_escalada é obrigatório."
            )
        return self
