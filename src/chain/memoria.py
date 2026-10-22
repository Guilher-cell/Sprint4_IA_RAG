"""
src/chain/memoria.py
-----------------------
Memória conversacional por sessão com limite de tokens (Sprint 03, Aula 02).

A Sprint 2 controlava o histórico por NÚMERO DE MENSAGENS
(MAX_HISTORY_MESSAGES=20, em chatbot.py). A Sprint 03 pede algo mais preciso:
limite por TOKENS, no espírito do `ConversationTokenBufferMemory` do
LangChain, mas implementado sobre a interface `BaseChatMessageHistory`
exigida por `RunnableWithMessageHistory` (a API de memória por sessão do
LCEL moderno).

`TokenBufferChatMessageHistory` faz o mesmo papel do
`ConversationTokenBufferMemory`: mantém as mensagens mais recentes e
descarta as mais antigas quando o total de tokens da sessão ultrapassa
`max_token_limit`, mas o faz na estrutura de histórico por sessão que
`RunnableWithMessageHistory` espera (uma instância por `session_id`).
"""

from typing import Dict, List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def contar_tokens(texto: str) -> int:
        return len(_ENC.encode(texto or ""))

except Exception:  # pragma: no cover - fallback se tiktoken não puder baixar o vocab
    def contar_tokens(texto: str) -> int:
        # Aproximação char/4 (ver prompts/VERSOES.md, nota de metodologia).
        return max(1, round(len(texto or "") / 4))


def _conteudo_como_texto(mensagem: BaseMessage) -> str:
    conteudo = mensagem.content
    return conteudo if isinstance(conteudo, str) else str(conteudo)


class TokenBufferChatMessageHistory(BaseChatMessageHistory):
    """
    Histórico de mensagens de UMA sessão, com poda por limite de tokens.
    Implementa a interface mínima exigida por RunnableWithMessageHistory:
    propriedade `messages`, `add_message` e `clear`.
    """

    def __init__(self, max_token_limit: int = 2000):
        self._messages: List[BaseMessage] = []
        self.max_token_limit = max_token_limit

    @property
    def messages(self) -> List[BaseMessage]:
        return self._messages

    def add_messages(self, messages: List[BaseMessage]) -> None:
        self._messages.extend(messages)
        self._podar_por_tokens()

    def add_message(self, message: BaseMessage) -> None:
        self._messages.append(message)
        self._podar_por_tokens()

    def _podar_por_tokens(self) -> None:
        total = sum(contar_tokens(_conteudo_como_texto(m)) for m in self._messages)
        # Mantém sempre ao menos a última mensagem, mesmo que ela sozinha
        # ultrapasse o limite (evita loop infinito / histórico vazio).
        while total > self.max_token_limit and len(self._messages) > 1:
            removida = self._messages.pop(0)
            total -= contar_tokens(_conteudo_como_texto(removida))

    def clear(self) -> None:
        self._messages = []


# Store em memória de processo: session_id -> histórico da sessão.
# Para produção real, isso seria substituído por Redis/SQL, mas está fora do
# escopo da Sprint 03 (ver enunciado: sem observabilidade/infra nova).
_STORE: Dict[str, TokenBufferChatMessageHistory] = {}


def get_session_history(
    session_id: str, max_token_limit: int = 2000
) -> TokenBufferChatMessageHistory:
    if session_id not in _STORE:
        _STORE[session_id] = TokenBufferChatMessageHistory(
            max_token_limit=max_token_limit
        )
    return _STORE[session_id]


def limpar_sessao(session_id: str) -> None:
    _STORE.pop(session_id, None)
