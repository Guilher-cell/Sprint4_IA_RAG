"""
main_v2.py
----------
GoodWe EV ChargeOps Chatbot - Sprint 03 (refactory em LangChain LCEL)

Substitui o loop manual de chatbot.py (Sprint 2) pela chain construída em
src/chain/builder.py: extração estruturada (Pydantic v2) -> guardrails ->
lookup determinístico -> resposta final estruturada (Pydantic v2), com
memória por sessão (RunnableWithMessageHistory + limite de tokens).

O chatbot.py da Sprint 2 é mantido intacto no repositório como baseline
"antes" para o comparativo do relatório de evolução (docs/relatorio_evolucao.md).

Ambos os modelos usados nesta Sprint (gpt-oss-120b e qwen3.6-27b) são
acessados via API da Groq, com a mesma GROQ_API_KEY — não é necessário
rodar Ollama local (ver src/chain/llm_factory.py para a decisão de design).

Variáveis de ambiente relevantes (ver .env.example):
  LLM_PROVIDER=groq_oss|groq_secundario|ollama   (default: groq_oss)
  GROQ_API_KEY=...            (obrigatório para groq_oss e groq_secundario)
  GROQ_MODEL_OSS=openai/gpt-oss-120b
  GROQ_MODEL_SECUNDARIO=openai/gpt-oss-20b

Execução: python main_v2.py
"""

import os
import sys
import uuid

from dotenv import load_dotenv

from src.chain.builder import construir_chatbot_com_memoria
from src.chain.memoria import limpar_sessao


def main() -> None:
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "groq_oss")
    versao_prompt = os.environ.get("SYSTEM_PROMPT_VERSION", "v2")

    try:
        chatbot = construir_chatbot_com_memoria(
            provider=provider, versao_prompt=versao_prompt
        )
    except RuntimeError as erro:
        print(f"[ERRO] {erro}")
        sys.exit(1)

    session_id = str(uuid.uuid4())
    config = {"configurable": {"session_id": session_id}}

    print("=" * 60)
    print(f"GoodWe EV ChargeOps Chatbot - Sprint 03 (LangChain LCEL)")
    print(f"Provider: {provider} | Prompt: system_prompt_{versao_prompt}.md")
    print("Digite sua pergunta ('sair' para encerrar, 'reset' para nova sessão).")
    print("=" * 60)

    while True:
        try:
            entrada = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando o chatbot. Até logo!")
            break

        if not entrada:
            continue
        if entrada.lower() in {"sair", "exit", "quit"}:
            print("Encerrando o chatbot. Até logo!")
            break
        if entrada.lower() == "reset":
            limpar_sessao(session_id)
            session_id = str(uuid.uuid4())
            config = {"configurable": {"session_id": session_id}}
            print("[Nova sessão / histórico reiniciado]")
            continue

        try:
            resultado = chatbot.invoke({"pergunta": entrada}, config=config)
        except Exception as erro:
            print(f"[ERRO ao consultar o modelo] {erro}")
            continue

        estruturado = resultado["estruturado"]
        print(f"\nGoodWe Assistant: {estruturado.mensagem}")
        if estruturado.precisa_escalar:
            print(f"[Escalar para: {estruturado.destino_escalada}]")


if __name__ == "__main__":
    main()
