"""
src/rag/textutils.py
--------------------
Utilitários de texto em português usados em três lugares do projeto:
  - embeddings offline (fallback quando o Ollama não está acessível),
  - reranking lexical do retriever,
  - gerador extrativo offline e métricas da rubrica manual (evals/metricas.py).

Tudo é determinístico e não depende de rede nem de modelo.
"""

import re
import unicodedata

STOPWORDS = set(
    """a o as os um uma uns umas de do da dos das em no na nos nas por para com sem
    sobre entre e ou mas que se ao aos à às é são foi ser ter tem há como qual quais
    quando onde quem eu meu minha seu sua nosso nossa ele ela eles elas isso isto esse
    essa este esta pode posso podem fazer faz mais menos muito já não sim também até
    depois antes cada todo toda todos todas só ainda vez então me te nos lhe vai vão
    estar está estão sendo pela pelo pelas pelos num numa deve devem""".split()
)

_RE_TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)?")

_SUFIXOS = (
    "amentos", "amento", "imentos", "imento", "acoes", "acao", "coes", "cao",
    "adores", "adoras", "ador", "adora", "idades", "idade", "mente", "aveis",
    "avel", "ivos", "ivas", "ivo", "iva", "oes", "ais", "eis", "es", "s", "a", "o",
)


def normalizar(texto: str) -> str:
    """minúsculas + remoção de acentos (mantém dígitos, vírgulas e pontos)."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def _stem(token: str) -> str:
    if token[0].isdigit():
        return token
    for suf in _SUFIXOS:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


_STOP_NORM = {normalizar(s) for s in STOPWORDS}


def tokens(texto: str) -> list[str]:
    """Tokens normalizados, sem stopwords e com stemming leve."""
    brutos = _RE_TOKEN.findall(normalizar(texto))
    return [_stem(t) for t in brutos if t not in _STOP_NORM]


def tokens_unicos(texto: str) -> set[str]:
    return set(tokens(texto))


def dividir_sentencas(texto: str) -> list[str]:
    """Divide em sentenças e itens de lista; descarta linhas de título."""
    saida: list[str] = []
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if re.match(r"^\d+(?:\.\d+)*\.\s+[A-ZÀ-Ú][^.]{0,80}$", linha):
            continue  # título numerado de seção (PDF)
        if linha.startswith("[Seção:") or linha.startswith("[Secao:"):
            continue
        for parte in re.split(r"(?:(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9])|(?<=;)\s+)", linha):
            parte = parte.strip(" -•\t")
            if parte.endswith(";"):
                parte = parte[:-1] + "."
            if len(parte) > 3:
                saida.append(parte)
    return saida
