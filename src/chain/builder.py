"""
src/chain/builder.py
-----------------------
Núcleo conversacional refatorado em LangChain LCEL (Sprint 03, Aula 01).

Fluxo do pipeline (substitui o loop manual de function calling de chatbot.py
na Sprint 2):

    pergunta do usuário
        │
        ▼
    (1) guardrails determinísticos (jailbreak / domínio sensível) — sem LLM
        │  (se bater, retorna resposta fixa e encerra)
        ▼
    (2) extraction_chain = EXTRACTION_PROMPT | llm.with_structured_output(ConsultaRecarga)
        │  → classifica persona, tipo_consulta, unidade/carregador (Pydantic v2)
        ▼
    (3) lookup determinístico em src/data/mock_data.py, escolhido por tipo_consulta
        │  (substitui o function calling da Sprint 2: o Python decide a chamada,
        │   não mais o LLM)
        ▼
    (4) final_chain = FINAL_ANSWER_PROMPT | llm.with_structured_output(RespostaChat)
        │  → gera a resposta final em linguagem natural, validada por schema
        ▼
    RespostaChat (mensagem, precisa_escalar, destino_escalada, fonte_dados)

Memória: todo o pipeline é envolvido por RunnableWithMessageHistory
(src/chain/memoria.py), mantendo o histórico por sessão com limite de tokens.
"""

from pathlib import Path
from typing import Callable, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from src.chain.llm_factory import get_llm
from src.chain.memoria import get_session_history
from src.data.mock_data import (
    consultar_agendamentos,
    consultar_consumo,
    consultar_orquestracao_potencia,
    consultar_status_carregador,
)
from src.guardrails.moderation import verificar_dominio_sensivel
from src.guardrails.scope_validator import eh_fora_de_escopo, eh_tentativa_de_jailbreak
from src.schemas.consulta_recarga import ConsultaRecarga, Persona, TipoConsulta
from src.schemas.resposta_chat import RespostaChat

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def carregar_system_prompt(versao: str = "v2") -> str:
    caminho = PROMPTS_DIR / f"system_prompt_{versao}.md"
    return caminho.read_text(encoding="utf-8")


# ---------------------------------------------------------------------
# Few-shot examples (mesmo conteúdo da Sprint 2, system_prompt.py), agora
# injetados diretamente como mensagens no ChatPromptTemplate em vez de serem
# concatenados manualmente ao histórico (chatbot.py, _construir_historico_inicial).
# ---------------------------------------------------------------------
EXEMPLOS_FEW_SHOT = [
    (
        "Olá, sou morador do apartamento 102. Quanto eu já gastei com "
        "carregamento este mês?",
        (
            "Olá! Você é o Morador do apartamento 102. Vou consultar seu "
            "consumo no sistema GoodWe ChargeOps.\n\n"
            "Este mês você teve 3 ciclos de registro (sessões via RFID), "
            "totalizando 18,0 kWh, o que equivale a aproximadamente "
            "R$ 16,20 com base na tarifa atual de R$ 0,90/kWh definida "
            "pelo síndico. O histórico detalhado de cada sessão fica "
            "disponível no app GoodWe, em 'Meu Consumo'."
        ),
    ),
    (
        "Sou o síndico. Preciso entender como está a orquestração de "
        "potência agora, está perto do limite?",
        (
            "Olá, síndico! Consultando a orquestração de potência no "
            "sistema GoodWe ChargeOps:\n\n"
            "1. O limite configurado é de 22,0 kW de potência simultânea.\n"
            "2. Atualmente há 2 carregadores ativos, consumindo 14,0 kW.\n"
            "3. Ainda restam 8,0 kW disponíveis antes de atingir o limite.\n\n"
            "Não há risco imediato de sobrecarga. Caso queira ajustar o "
            "limite ou as prioridades de horário, isso pode ser feito no "
            "painel administrativo do GoodWe ChargeOps."
        ),
    ),
    (
        "Sou o zelador. O carregador box 7 parou de funcionar, o que eu "
        "faço?",
        (
            "Olá! Consultando o status do box 7 no sistema GoodWe "
            "ChargeOps: ele está com erro de comunicação, registrado há "
            "cerca de 2 horas, e o disjuntor do box 7 não está sendo "
            "monitorado.\n\n"
            "Passos recomendados:\n"
            "1. Verifique se o disjuntor do box 7 está ligado.\n"
            "2. Reinicie o carregador desligando e religando o disjuntor "
            "específico.\n"
            "3. Aguarde alguns minutos e verifique se o status volta a "
            "'online' no painel.\n\n"
            "Se o erro de comunicação persistir após esses passos, "
            "acione o suporte técnico GoodWe, pois pode indicar uma "
            "falha grave de equipamento."
        ),
    ),
]

_FEW_SHOT_MESSAGES = []
for _pergunta, _resposta in EXEMPLOS_FEW_SHOT:
    _FEW_SHOT_MESSAGES.append(("human", _pergunta))
    _FEW_SHOT_MESSAGES.append(("ai", _resposta))


def _montar_extraction_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é o módulo de extração de intenção do assistente GoodWe "
                "EV ChargeOps. A partir da pergunta do usuário e do histórico "
                "da conversa, preencha os campos do schema ConsultaRecarga. "
                "Nunca invente 'unidade' ou 'carregador' que não estejam "
                "explícitos na pergunta ou no histórico — nesse caso, deixe o "
                "campo como null. Classifique tipo_consulta='fora_de_escopo' "
                "para qualquer assunto que não seja carregamento de EVs, "
                "condomínio ou o sistema GoodWe ChargeOps.",
            ),
            MessagesPlaceholder("history"),
            ("human", "{pergunta}"),
        ]
    )


def _montar_final_prompt(versao_prompt: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", carregar_system_prompt(versao_prompt)),
            *_FEW_SHOT_MESSAGES,
            MessagesPlaceholder("history"),
            (
                "human",
                "<pergunta_usuario>{pergunta}</pergunta_usuario>\n"
                "<dados_consultados>{dados_consultados}</dados_consultados>\n"
                "<instrucao>Responda ao usuário em português, seguindo o "
                "formato_de_saida do system prompt. Use os dados em "
                "dados_consultados quando existirem; se indicarem erro ou "
                "ausência (encontrado=false), informe isso claramente e "
                "oriente a consulta no app/portal GoodWe. Nunca invente "
                "valores fora de dados_consultados.</instrucao>",
            ),
        ]
    )


# Mapa tipo_consulta -> função de lookup determinístico (substitui o
# FUNCOES_DISPONIVEIS de tools.py na Sprint 2; agora chamado pelo Python,
# não pelo LLM).
_LOOKUP_POR_TIPO: Dict[TipoConsulta, Callable[[ConsultaRecarga], dict]] = {
    TipoConsulta.CONSUMO: lambda c: consultar_consumo(c.unidade),
    TipoConsulta.STATUS_CARREGADOR: lambda c: consultar_status_carregador(c.carregador),
    TipoConsulta.AGENDAMENTOS: lambda c: consultar_agendamentos(c.unidade),
    TipoConsulta.ORQUESTRACAO_POTENCIA: lambda c: consultar_orquestracao_potencia(),
}


def _montar_chains(provider: str, versao_prompt: str):
    llm = get_llm(provider)
    extraction_chain = _montar_extraction_prompt() | llm.with_structured_output(
        ConsultaRecarga
    )
    final_chain = _montar_final_prompt(versao_prompt) | llm.with_structured_output(
        RespostaChat
    )
    # Chain de fallback SEM forçar tool-calling, usada quando o modelo se
    # recusa a chamar a ferramenta (ver docs/relatorio_evolucao.md,
    # Problema 8: gpt-oss-20b às vezes prefere responder em texto livre —
    # às vezes uma recusa legítima, às vezes um "falso negativo" causado
    # pela combinação reasoning-model + tool_choice forçado da Groq — e a
    # Groq retorna erro 400 (tool_use_failed) em vez de deixar passar.
    final_chain_bruta = _montar_final_prompt(versao_prompt) | llm | StrOutputParser()
    return extraction_chain, final_chain, final_chain_bruta


def _invocar_com_fallback(
    chain_estruturada, payload: dict, config, tentativas: int = 2
):
    """
    Tenta `chain_estruturada.invoke` até `tentativas` vezes. Se todas
    falharem (ex.: erro 400 tool_use_failed da Groq quando o modelo não
    chama a ferramenta), retorna (None, último_erro) em vez de propagar a
    exceção, para que o chamador decida um fallback gracioso.
    """
    ultimo_erro: Exception | None = None
    for _ in range(tentativas):
        try:
            return chain_estruturada.invoke(payload, config=config), None
        except Exception as e:  # noqa: BLE001 - queremos capturar qualquer erro da API aqui
            ultimo_erro = e
    return None, ultimo_erro


def construir_pipeline(provider: str = "groq_oss", versao_prompt: str = "v2") -> RunnableLambda:
    """
    Monta o RunnableLambda que implementa o fluxo completo (guardrails +
    extração + lookup + resposta final). Ainda SEM memória — ver
    `construir_chatbot_com_memoria` para a versão com histórico por sessão.
    """
    extraction_chain, final_chain, final_chain_bruta = _montar_chains(
        provider, versao_prompt
    )

    def _pipeline(inputs: dict, config=None) -> dict:
        pergunta: str = inputs["pergunta"]
        history = inputs.get("history", [])

        # (1) Guardrails determinísticos, antes de qualquer chamada ao LLM.
        if eh_tentativa_de_jailbreak(pergunta):
            resposta = RespostaChat(
                mensagem=(
                    "Não posso seguir esse tipo de instrução. Sou o "
                    "assistente oficial GoodWe EV ChargeOps e minha função é "
                    "apoiar dúvidas sobre o carregamento de veículos "
                    "elétricos no condomínio."
                ),
                precisa_escalar=False,
                fonte_dados="guardrail_jailbreak",
            )
            return {"texto": resposta.mensagem, "estruturado": resposta}

        alerta_dominio = verificar_dominio_sensivel(pergunta)
        if alerta_dominio:
            resposta = RespostaChat(
                mensagem=alerta_dominio,
                precisa_escalar=True,
                destino_escalada="profissional habilitado / administração do condomínio",
                fonte_dados="guardrail_dominio_sensivel",
            )
            return {"texto": resposta.mensagem, "estruturado": resposta}

        # (2) Extração de intenção estruturada e validada (Pydantic v2),
        # com fallback caso o modelo não chame a ferramenta (Problema 8).
        consulta, erro_extracao = _invocar_com_fallback(
            extraction_chain, {"pergunta": pergunta, "history": history}, config
        )
        if consulta is None:
            # Sem classificação confiável: não arriscamos lookup de dados
            # errado, mas ainda tentamos responder de forma útil na etapa
            # (4), que tem seu próprio fallback em texto livre.
            consulta = ConsultaRecarga(
                persona=Persona.DESCONHECIDA,
                tipo_consulta=TipoConsulta.OUTRO_DENTRO_ESCOPO,
                resumo_pedido=pergunta[:200],
            )

        if (
            consulta.tipo_consulta == TipoConsulta.FORA_DE_ESCOPO
            or eh_fora_de_escopo(pergunta)
        ):
            resposta = RespostaChat(
                mensagem=(
                    "Esse pedido está fora do escopo deste assistente, que "
                    "apoia a gestão do carregamento de veículos elétricos no "
                    "sistema GoodWe EV ChargeOps. Posso ajudar com dúvidas "
                    "sobre consumo, agendamento, rateio ou diagnóstico dos "
                    "carregadores."
                ),
                precisa_escalar=False,
                fonte_dados="guardrail_escopo",
            )
            return {"texto": resposta.mensagem, "estruturado": resposta}

        # (3) Lookup determinístico nos dados mockados.
        funcao_lookup = _LOOKUP_POR_TIPO.get(consulta.tipo_consulta)
        dados = funcao_lookup(consulta) if funcao_lookup else {}

        # (4) Resposta final estruturada e validada (Pydantic v2), com
        # fallback para texto livre (sem forçar tool-calling) se a Groq
        # retornar tool_use_failed (Problema 8).
        payload_final = {
            "pergunta": pergunta,
            "dados_consultados": dados,
            "history": history,
        }
        resposta, erro_final = _invocar_com_fallback(final_chain, payload_final, config)

        if resposta is None:
            try:
                texto_bruto = final_chain_bruta.invoke(payload_final, config=config)
                texto_bruto = getattr(texto_bruto, "content", str(texto_bruto)).strip()
            except Exception:
                texto_bruto = ""
            resposta = RespostaChat(
                mensagem=(
                    texto_bruto
                    if texto_bruto
                    else (
                        "Não consegui gerar uma resposta estruturada agora "
                        "por uma instabilidade técnica do modelo. Pode "
                        "tentar reformular a pergunta ou repetir em "
                        "instantes?"
                    )
                ),
                precisa_escalar=False,
                fonte_dados="fallback_tool_use_failed",
            )
        elif not resposta.fonte_dados:
            resposta.fonte_dados = f"mock_{consulta.tipo_consulta.value}"

        return {"texto": resposta.mensagem, "estruturado": resposta}

    return RunnableLambda(_pipeline)


def construir_chatbot_com_memoria(
    provider: str = "groq_oss",
    versao_prompt: str = "v2",
    max_token_limit: int = 2000,
) -> RunnableWithMessageHistory:
    """
    Envolve o pipeline com RunnableWithMessageHistory (Aula 02), usando
    TokenBufferChatMessageHistory como implementação de memória por sessão
    com limite de tokens.
    """
    pipeline = construir_pipeline(provider, versao_prompt)

    return RunnableWithMessageHistory(
        pipeline,
        lambda session_id: get_session_history(session_id, max_token_limit),
        input_messages_key="pergunta",
        history_messages_key="history",
        output_messages_key="texto",
    )
