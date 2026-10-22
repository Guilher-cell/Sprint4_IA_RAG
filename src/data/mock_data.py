"""
src/data/mock_data.py
------------------------
"Banco de dados" simulado do condomínio, migrado de tools.py (Sprint 2).

Os mesmos valores mockados são mantidos de propósito, para que o
comparativo antes/depois do relatório de evolução (docs/relatorio_evolucao.md)
seja sobre a ARQUITETURA (function calling vs. structured output +
lookup determinístico), e não sobre diferenças de dados de teste.

Na Sprint 2, essas funções eram chamadas via function calling (o modelo
decidia se e quando chamar `consultar_consumo`, por exemplo). Na Sprint 03,
elas são chamadas de forma DETERMINÍSTICA pelo pipeline Python, a partir do
campo `tipo_consulta` já classificado e validado pelo schema `ConsultaRecarga`
(structured output) — o LLM não decide mais "se" a função é chamada, apenas
fornece os parâmetros extraídos da pergunta.
"""

from typing import Optional

CONSUMO_POR_UNIDADE = {
    "101": {"kwh_mes": 42.5, "valor_reais": 38.25, "ciclos_registro": 6},
    "102": {"kwh_mes": 18.0, "valor_reais": 16.20, "ciclos_registro": 3},
    "201": {"kwh_mes": 55.2, "valor_reais": 49.68, "ciclos_registro": 8},
    "202": {"kwh_mes": 30.0, "valor_reais": 27.00, "ciclos_registro": 5},
}

TARIFA_RS_KWH = 0.90

STATUS_CARREGADORES = {
    "box 1": {"status": "online", "ultima_falha": None},
    "box 5": {"status": "online", "ultima_falha": None},
    "box 7": {
        "status": "erro_comunicacao",
        "ultima_falha": (
            "Falha de comunicação detectada há 2 horas. Disjuntor do box 7 "
            "não está sendo monitorado."
        ),
    },
}

AGENDAMENTOS = {
    "101": [{"dia": "segunda-feira", "horario": "23:00 - 02:00", "box": "box 1"}],
    "201": [{"dia": "quarta-feira", "horario": "00:00 - 03:00", "box": "box 5"}],
}

LIMITE_POTENCIA_SIMULTANEA_KW = 22.0
CARREGADORES_ATIVOS_AGORA = 2
POTENCIA_EM_USO_KW = 14.0


def consultar_consumo(unidade: Optional[str]) -> dict:
    if not unidade:
        return {"encontrado": False, "mensagem": "Unidade não informada na pergunta."}
    dados = CONSUMO_POR_UNIDADE.get(unidade)
    if dados is None:
        return {
            "encontrado": False,
            "mensagem": f"Unidade '{unidade}' não encontrada nos registros do sistema.",
        }
    return {
        "encontrado": True,
        "unidade": unidade,
        "consumo_kwh_mes": dados["kwh_mes"],
        "valor_estimado_reais": dados["valor_reais"],
        "ciclos_de_registro_rfid": dados["ciclos_registro"],
        "tarifa_rs_por_kwh": TARIFA_RS_KWH,
    }


def consultar_status_carregador(identificacao: Optional[str]) -> dict:
    if not identificacao:
        return {"encontrado": False, "mensagem": "Carregador não informado na pergunta."}
    chave = identificacao.strip().lower()
    dados = STATUS_CARREGADORES.get(chave)
    if dados is None:
        return {
            "encontrado": False,
            "mensagem": f"Carregador '{identificacao}' não encontrado nos registros do sistema.",
        }
    return {
        "encontrado": True,
        "carregador": identificacao,
        "status": dados["status"],
        "detalhe_ultima_falha": dados["ultima_falha"],
    }


def consultar_agendamentos(unidade: Optional[str]) -> dict:
    if not unidade:
        return {"encontrado": False, "mensagem": "Unidade não informada na pergunta."}
    agendamentos = AGENDAMENTOS.get(unidade)
    if agendamentos is None:
        return {
            "encontrado": True,
            "unidade": unidade,
            "agendamentos": [],
            "mensagem": "Nenhum agendamento cadastrado para esta unidade.",
        }
    return {"encontrado": True, "unidade": unidade, "agendamentos": agendamentos}


def consultar_orquestracao_potencia() -> dict:
    return {
        "limite_potencia_simultanea_kw": LIMITE_POTENCIA_SIMULTANEA_KW,
        "potencia_em_uso_kw": POTENCIA_EM_USO_KW,
        "potencia_disponivel_kw": round(
            LIMITE_POTENCIA_SIMULTANEA_KW - POTENCIA_EM_USO_KW, 1
        ),
        "carregadores_ativos_agora": CARREGADORES_ATIVOS_AGORA,
    }
