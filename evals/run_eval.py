"""
evals/run_eval.py
--------------------
Reexecuta o eval_set.json (Sprint 2 + 2 casos novos de guardrail da Sprint 03)
contra:
  --mode legacy   -> chatbot.py da Sprint 2 (Groq, function calling manual)
  --mode sprint3  -> pipeline LCEL da Sprint 03 (src/chain/builder.py)

Para cada caso, mede:
  - tempo de resposta (latência, em segundos)
  - tokens de entrada e saída (tiktoken cl100k_base como proxy comparativo;
    ver nota de metodologia em prompts/VERSOES.md)
  - a resposta obtida (para avaliação qualitativa manual)

Os resultados são gravados/mesclados em evals/sprint3_results.json, por
`mode` e `provider`, para alimentar a tabela comparativo antes/depois do
docs/relatorio_evolucao.md.

Os dois modelos comparados no bônus multi-provider (openai/gpt-oss-120b e
openai/gpt-oss-20b) são acessados via API da Groq, com a mesma GROQ_API_KEY —
não é necessário Ollama local (ver src/chain/llm_factory.py).

ATENÇÃO - RATE LIMIT DO TIER GRATUITO DA GROQ (ver docs/relatorio_evolucao.md,
Problema 5): o tier gratuito costuma limitar a ~30 requisições/minuto POR
MODELO. Cada caso do eval_set faz 2 chamadas de LLM (extração + resposta
final), então 9 casos = 18 chamadas. Este script aguarda PAUSA_ENTRE_CASOS
segundos entre casos para reduzir a chance de 429 (Too Many Requests). Se
mesmo assim receber 429, o SDK da Groq tenta de novo automaticamente com
backoff (pode parecer "travado" por alguns segundos) — isso é esperado, não
é bug; espere ou aumente PAUSA_ENTRE_CASOS. Os resultados já obtidos até uma
interrupção (Ctrl+C) são salvos, não é preciso recomeçar do zero.

IMPORTANTE: este script faz chamadas reais de API. Ele não foi executado no
ambiente de montagem deste pacote porque esse ambiente não tem acesso de
rede a api.groq.com (ver docs/relatorio_evolucao.md, seção de limitações).
Rode localmente:

    python evals/run_eval.py --mode legacy
    python evals/run_eval.py --mode sprint3 --provider groq_oss
    python evals/run_eval.py --mode sprint3 --provider groq_secundario
"""

import argparse
import json
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EVAL_SET_PATH = RAIZ / "evals" / "eval_set.json"
RESULTADOS_PATH = RAIZ / "evals" / "sprint3_results.json"

# Pausa entre casos, para não estourar o limite de ~30 req/min do tier
# gratuito da Groq (cada caso = 2 chamadas de LLM na Sprint 03). Aumente se
# ainda tomar 429 com frequência.
PAUSA_ENTRE_CASOS_SEGUNDOS = 3

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def contar_tokens(texto: str) -> int:
        return len(_ENC.encode(texto or ""))

except Exception:

    def contar_tokens(texto: str) -> int:
        return max(1, round(len(texto or "") / 4))


def carregar_eval_set() -> list[dict]:
    with open(EVAL_SET_PATH, encoding="utf-8") as f:
        return json.load(f)["casos"]


def rodar_legacy(resultados: list[dict]) -> None:
    """Roda o eval legado, anexando cada resultado em `resultados` (lista
    compartilhada com o chamador) assim que fica pronto — assim, mesmo que
    a execução seja interrompida (Ctrl+C) no meio do loop, os casos já
    concluídos não se perdem."""
    import sys

    sys.path.insert(0, str(RAIZ))
    from dotenv import load_dotenv
    from groq import Groq

    from chatbot import GoodWeChatbot, MODEL_NAME

    load_dotenv()
    import os

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY não encontrada (necessária para --mode legacy).")
    client = Groq(api_key=api_key)

    casos = carregar_eval_set()
    for i, caso in enumerate(casos, start=1):
        print(f"[legacy] caso {i}/{len(casos)} (id={caso['id']})...", flush=True)
        chatbot = GoodWeChatbot(client)
        entrada_tokens = contar_tokens(caso["pergunta"])
        inicio = time.perf_counter()
        try:
            resposta = chatbot.perguntar(caso["pergunta"])
            erro = None
        except Exception as e:
            resposta = ""
            erro = str(e)
            print(f"  [ERRO] {erro}", flush=True)
        latencia = time.perf_counter() - inicio

        resultados.append(
            {
                "id": caso["id"],
                "categoria": caso["categoria"],
                "pergunta": caso["pergunta"],
                "resposta": resposta,
                "erro": erro,
                "latencia_segundos": round(latencia, 3),
                "tokens_entrada_pergunta": entrada_tokens,
                "tokens_saida_resposta": contar_tokens(resposta),
                "modelo": MODEL_NAME,
            }
        )
        if i < len(casos):
            time.sleep(PAUSA_ENTRE_CASOS_SEGUNDOS)


def rodar_sprint3(provider: str, resultados: list[dict]) -> None:
    """Mesma lógica de `rodar_legacy`, para o pipeline LCEL da Sprint 03."""
    import sys

    sys.path.insert(0, str(RAIZ))
    from dotenv import load_dotenv

    from src.chain.builder import construir_chatbot_com_memoria

    load_dotenv()
    chatbot = construir_chatbot_com_memoria(provider=provider)

    casos = carregar_eval_set()
    for i, caso in enumerate(casos, start=1):
        print(f"[sprint3/{provider}] caso {i}/{len(casos)} (id={caso['id']})...", flush=True)
        session_id = str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}
        entrada_tokens = contar_tokens(caso["pergunta"])
        inicio = time.perf_counter()
        try:
            saida = chatbot.invoke({"pergunta": caso["pergunta"]}, config=config)
            estruturado = saida["estruturado"]
            resposta = estruturado.mensagem
            fonte_dados = estruturado.fonte_dados
            precisa_escalar = estruturado.precisa_escalar
            erro = None
        except Exception as e:
            resposta, fonte_dados, precisa_escalar, erro = "", None, None, str(e)
            print(f"  [ERRO] {erro}", flush=True)
        latencia = time.perf_counter() - inicio

        resultados.append(
            {
                "id": caso["id"],
                "categoria": caso["categoria"],
                "pergunta": caso["pergunta"],
                "resposta": resposta,
                "fonte_dados": fonte_dados,
                "precisa_escalar": precisa_escalar,
                "erro": erro,
                "latencia_segundos": round(latencia, 3),
                "tokens_entrada_pergunta": entrada_tokens,
                "tokens_saida_resposta": contar_tokens(resposta),
                "provider": provider,
            }
        )
        if i < len(casos):
            time.sleep(PAUSA_ENTRE_CASOS_SEGUNDOS)


def salvar_resultados(chave: str, resultados: list[dict]) -> None:
    dados = {}
    if RESULTADOS_PATH.exists():
        with open(RESULTADOS_PATH, encoding="utf-8") as f:
            dados = json.load(f)
    dados[chave] = {
        "executado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "casos": resultados,
    }
    with open(RESULTADOS_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"[OK] Resultados salvos em {RESULTADOS_PATH} (chave='{chave}')")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reexecuta o eval set (Sprint 2 e Sprint 3).")
    parser.add_argument("--mode", choices=["legacy", "sprint3"], required=True)
    parser.add_argument(
        "--provider",
        choices=["groq_oss", "groq_secundario", "ollama"],
        default="groq_oss",
        help="Só usado com --mode sprint3.",
    )
    args = parser.parse_args()

    chave = "legacy_groq_sprint2" if args.mode == "legacy" else f"sprint3_{args.provider}"
    resultados_parciais: list[dict] = []
    try:
        if args.mode == "legacy":
            rodar_legacy(resultados_parciais)
        else:
            rodar_sprint3(args.provider, resultados_parciais)
    except KeyboardInterrupt:
        print(
            "\n[AVISO] Interrompido pelo usuário (Ctrl+C). Salvando os "
            f"{len(resultados_parciais)} casos já concluídos antes de sair..."
        )
    finally:
        if resultados_parciais:
            salvar_resultados(chave, resultados_parciais)
        else:
            print("[AVISO] Nenhum caso foi concluído; nada foi salvo.")


if __name__ == "__main__":
    main()
