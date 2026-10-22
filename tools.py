"""
tools.py
--------
Funções (tools) que o chatbot GoodWe EV ChargeOps pode chamar via
function calling da API Groq.

Implementação do diferencial de FUNCTION CALLING citado no enunciado da
Sprint 2. As funções abaixo simulam consultas ao sistema GoodWe
ChargeOps (dados mockados, representativos do tipo de informação real
que o sistema retornaria), permitindo que o chatbot responda com dados
concretos em vez de apenas orientar o usuário a consultar o app.

Cada função tem uma definição correspondente em TOOLS_DEFINITIONS, no
formato esperado pela API Groq (compatível com o formato OpenAI
function calling / tools).
"""

import json


# ---------------------------------------------------------------------
# "Banco de dados" simulado do condomínio (mock)
# ---------------------------------------------------------------------

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
        "ultima_falha": "Falha de comunicação detectada há 2 horas. "
                          "Disjuntor do box 7 não está sendo monitorado.",
    },
}

AGENDAMENTOS = {
    "101": [
        {"dia": "segunda-feira", "horario": "23:00 - 02:00", "box": "box 1"},
    ],
    "201": [
        {"dia": "quarta-feira", "horario": "00:00 - 03:00", "box": "box 5"},
    ],
}

LIMITE_POTENCIA_SIMULTANEA_KW = 22.0
CARREGADORES_ATIVOS_AGORA = 2
POTENCIA_EM_USO_KW = 14.0


# ---------------------------------------------------------------------
# Implementação das funções (tools)
# ---------------------------------------------------------------------

def consultar_consumo(unidade: str) -> dict:
    """
    Retorna o consumo mensal (kWh e R$) e o número de ciclos de registro
    (sessões RFID) de uma unidade do condomínio.
    """
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


def consultar_status_carregador(identificacao: str) -> dict:
    """
    Retorna o status atual de um carregador (box) do condomínio, incluindo
    detalhes da última falha registrada, se houver.
    """
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


def consultar_agendamentos(unidade: str) -> dict:
    """
    Retorna os agendamentos de carregamento cadastrados para uma unidade.
    """
    agendamentos = AGENDAMENTOS.get(unidade)

    if agendamentos is None:
        return {
            "encontrado": True,
            "unidade": unidade,
            "agendamentos": [],
            "mensagem": "Nenhum agendamento cadastrado para esta unidade.",
        }

    return {
        "encontrado": True,
        "unidade": unidade,
        "agendamentos": agendamentos,
    }


def consultar_orquestracao_potencia() -> dict:
    """
    Retorna o status atual da orquestração de potência do condomínio:
    limite configurado, potência em uso e número de carregadores ativos.
    """
    return {
        "limite_potencia_simultanea_kw": LIMITE_POTENCIA_SIMULTANEA_KW,
        "potencia_em_uso_kw": POTENCIA_EM_USO_KW,
        "potencia_disponivel_kw": round(
            LIMITE_POTENCIA_SIMULTANEA_KW - POTENCIA_EM_USO_KW, 1
        ),
        "carregadores_ativos_agora": CARREGADORES_ATIVOS_AGORA,
    }


# ---------------------------------------------------------------------
# Definições das tools no formato esperado pela API Groq
# (compatível com o padrão OpenAI function calling)
# ---------------------------------------------------------------------

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_consumo",
            "description": (
                "Consulta o consumo mensal de energia (kWh e valor em "
                "reais) e o número de ciclos de registro (sessões RFID) "
                "de uma unidade do condomínio no sistema GoodWe ChargeOps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "unidade": {
                        "type": "string",
                        "description": (
                            "Identificação da unidade/apartamento, ex.: "
                            "'101', '201'."
                        ),
                    }
                },
                "required": ["unidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_status_carregador",
            "description": (
                "Consulta o status atual de um carregador (box) do "
                "condomínio no sistema GoodWe ChargeOps, incluindo "
                "detalhes de falhas recentes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "identificacao": {
                        "type": "string",
                        "description": (
                            "Identificação do carregador, ex.: 'box 7', "
                            "'box 1'."
                        ),
                    }
                },
                "required": ["identificacao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_agendamentos",
            "description": (
                "Consulta os agendamentos de carregamento cadastrados "
                "para uma unidade do condomínio no sistema GoodWe "
                "ChargeOps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "unidade": {
                        "type": "string",
                        "description": (
                            "Identificação da unidade/apartamento, ex.: "
                            "'101', '201'."
                        ),
                    }
                },
                "required": ["unidade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_orquestracao_potencia",
            "description": (
                "Consulta o status atual da orquestração de potência do "
                "condomínio no sistema GoodWe ChargeOps: limite de "
                "potência simultânea configurado, potência em uso e "
                "número de carregadores ativos agora."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# Mapeamento nome da função -> implementação real, usado pelo chatbot
# para executar a função escolhida pelo modelo.
FUNCOES_DISPONIVEIS = {
    "consultar_consumo": consultar_consumo,
    "consultar_status_carregador": consultar_status_carregador,
    "consultar_agendamentos": consultar_agendamentos,
    "consultar_orquestracao_potencia": consultar_orquestracao_potencia,
}


def executar_funcao(nome_funcao: str, argumentos_json: str) -> str:
    """
    Executa a função solicitada pelo modelo, a partir do nome e dos
    argumentos (em formato JSON, como retornado pela API), e retorna o
    resultado também como string JSON (formato esperado para a mensagem
    de role "tool").
    """
    funcao = FUNCOES_DISPONIVEIS.get(nome_funcao)

    if funcao is None:
        return json.dumps({"erro": f"Função '{nome_funcao}' não existe."})

    try:
        argumentos = json.loads(argumentos_json) if argumentos_json else {}
    except json.JSONDecodeError:
        return json.dumps({"erro": "Argumentos inválidos (JSON malformado)."})

    try:
        resultado = funcao(**argumentos)
    except TypeError as erro:
        return json.dumps({"erro": f"Argumentos inválidos para '{nome_funcao}': {erro}"})

    return json.dumps(resultado, ensure_ascii=False)
