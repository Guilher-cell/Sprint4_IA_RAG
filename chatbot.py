"""
chatbot.py
----------
GoodWe EV ChargeOps Chatbot - Sprint 2

Implementa o chatbot funcional com:
- Injeção de contexto via system prompt (system_prompt.py)
- Few-shot prompting: exemplos de pergunta/resposta (um por persona)
  injetados no início do histórico para calibrar tom e formato
- Gerenciamento de histórico de mensagens (memória de contexto multi-turno)
- Function calling: o modelo pode chamar ferramentas (tools.py) que
  consultam dados mockados do sistema GoodWe ChargeOps (consumo, status
  de carregador, agendamentos, orquestração de potência)
- API Groq (Llama 3), conforme escolha tecnológica da Sprint 1
- Carregamento de API Key via variável de ambiente / .env (nunca hardcoded)

Execução: python chatbot.py
"""

import os
import sys
from groq import Groq
from dotenv import load_dotenv

from system_prompt import SYSTEM_PROMPT, EXEMPLOS_FEW_SHOT
from tools import TOOLS_DEFINITIONS, executar_funcao


MODEL_NAME = "llama-3.3-70b-versatile"

# Limite de mensagens do histórico mantidas (além do system prompt e dos
# exemplos few-shot, que são sempre preservados), para controlar o
# tamanho do contexto enviado à API
MAX_HISTORY_MESSAGES = 20

# Número máximo de "rodadas" de function calling por pergunta do usuário
# (evita loops infinitos caso o modelo insista em chamar ferramentas)
MAX_TOOL_CALL_ROUNDS = 4


def carregar_api_key() -> str:
    """
    Carrega a chave da API Groq a partir de variável de ambiente.

    Prioridade:
    1. Variável de ambiente já definida (ex.: exportada no terminal,
       ou configurada via Google Colab Secrets e injetada no os.environ)
    2. Arquivo .env local (via python-dotenv), apenas em ambiente local

    Nunca deve haver chave de API escrita diretamente no código-fonte.
    """
    load_dotenv()  # carrega .env se existir (ambiente local)
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada.\n"
            "Defina a variável de ambiente GROQ_API_KEY antes de executar.\n"
            "- Local: crie um arquivo .env com GROQ_API_KEY=sua_chave\n"
            "- Google Colab: use Colab Secrets (aba de chave 🔑) e nomeie "
            "o secret como GROQ_API_KEY"
        )
    return api_key


def _construir_historico_inicial() -> list[dict]:
    """
    Monta o histórico inicial da conversa:
    - mensagem 0: system prompt (contexto fixo GoodWe ChargeOps)
    - mensagens seguintes: exemplos few-shot (pares user/assistant),
      um por persona, usados para calibrar tom e formato de resposta
    """
    historico = [{"role": "system", "content": SYSTEM_PROMPT}]

    for pergunta_exemplo, resposta_exemplo in EXEMPLOS_FEW_SHOT:
        historico.append({"role": "user", "content": pergunta_exemplo})
        historico.append({"role": "assistant", "content": resposta_exemplo})

    return historico


class GoodWeChatbot:
    """
    Encapsula o cliente Groq, o system prompt + few-shot examples de
    contexto GoodWe, o histórico de mensagens da conversa (memória
    multi-turno) e o ciclo de function calling com as ferramentas
    definidas em tools.py.
    """

    def __init__(self, client: Groq, model: str = MODEL_NAME):
        self.client = client
        self.model = model
        # Número de mensagens "fixas" no início do histórico (system
        # prompt + few-shot examples), que nunca são removidas pelo
        # limite de histórico.
        self.historico_inicial = _construir_historico_inicial()
        self.tamanho_historico_fixo = len(self.historico_inicial)
        self.history: list[dict] = list(self.historico_inicial)

    def _aplicar_limite_historico(self) -> None:
        """
        Mantém o histórico dentro de um limite, preservando sempre o
        bloco fixo inicial (system prompt + few-shot examples) e
        descartando as mensagens mais antigas da conversa real quando o
        limite é excedido.
        """
        limite_total = self.tamanho_historico_fixo + MAX_HISTORY_MESSAGES
        if len(self.history) > limite_total:
            mensagens_excedentes = len(self.history) - limite_total
            inicio = self.tamanho_historico_fixo
            del self.history[inicio:inicio + mensagens_excedentes]

    def _chamar_modelo(self):
        """Faz uma chamada à API Groq com o histórico atual e as tools."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            tools=TOOLS_DEFINITIONS,
            tool_choice="auto",
            temperature=0.4,
            max_tokens=600,
        )

    def perguntar(self, mensagem_usuario: str) -> str:
        """
        Envia a mensagem do usuário ao modelo, incluindo todo o histórico
        de contexto (system prompt + few-shot + turnos anteriores).

        Caso o modelo solicite o uso de uma ou mais ferramentas (function
        calling), executa as funções correspondentes em tools.py, devolve
        os resultados ao modelo e repete até obter uma resposta final em
        texto (ou até atingir MAX_TOOL_CALL_ROUNDS).

        Atualiza o histórico com todos os turnos (usuário, chamadas de
        ferramenta, resultados de ferramenta e resposta final) e retorna
        apenas o texto da resposta final ao usuário.
        """
        self.history.append({"role": "user", "content": mensagem_usuario})
        self._aplicar_limite_historico()

        for _ in range(MAX_TOOL_CALL_ROUNDS):
            resposta = self._chamar_modelo()
            mensagem = resposta.choices[0].message
            tool_calls = getattr(mensagem, "tool_calls", None)

            if not tool_calls:
                # Resposta final em texto: encerra o ciclo
                conteudo_resposta = mensagem.content
                self.history.append(
                    {"role": "assistant", "content": conteudo_resposta}
                )
                self._aplicar_limite_historico()
                return conteudo_resposta

            # O modelo pediu para usar uma ou mais ferramentas:
            # registra a mensagem do assistente com as tool_calls
            self.history.append(
                {
                    "role": "assistant",
                    "content": mensagem.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            # Executa cada função solicitada e registra o resultado
            for tool_call in tool_calls:
                resultado_funcao = executar_funcao(
                    tool_call.function.name, tool_call.function.arguments
                )
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": resultado_funcao,
                    }
                )

            self._aplicar_limite_historico()

        # Caso o limite de rodadas de function calling seja atingido sem
        # uma resposta final em texto, faz uma última chamada sem tools
        # para forçar uma resposta textual.
        resposta_final = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            temperature=0.4,
            max_tokens=600,
        )
        conteudo_resposta = resposta_final.choices[0].message.content
        self.history.append({"role": "assistant", "content": conteudo_resposta})
        self._aplicar_limite_historico()
        return conteudo_resposta

    def resetar_conversa(self) -> None:
        """Reinicia o histórico, mantendo system prompt + few-shot examples."""
        self.history = list(self.historico_inicial)


def main() -> None:
    try:
        api_key = carregar_api_key()
    except RuntimeError as erro:
        print(f"[ERRO] {erro}")
        sys.exit(1)

    client = Groq(api_key=api_key)
    chatbot = GoodWeChatbot(client)

    print("=" * 60)
    print("GoodWe EV ChargeOps Chatbot - EV Challenge 2026")
    print("Digite sua pergunta (ou 'sair' para encerrar,")
    print("'reset' para limpar o histórico da conversa).")
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
            chatbot.resetar_conversa()
            print("[Histórico de conversa reiniciado]")
            continue

        try:
            resposta = chatbot.perguntar(entrada)
        except Exception as erro:
            print(f"[ERRO ao consultar a API] {erro}")
            continue

        print(f"\nGoodWe Assistant: {resposta}")


if __name__ == "__main__":
    main()
