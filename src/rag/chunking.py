"""
src/rag/chunking.py
-------------------
Estratégia de chunking (Aula 07) — RecursiveCharacterTextSplitter com metadados
de seção, para que cada trecho recuperado possa ser citado como
"documento · seção · página".

Decisões (detalhadas em docs/relatorio_rag.md):
  - tamanho/overlap são parâmetros da iteração (ver config.py);
  - separadores priorizam quebra por parágrafo > linha > frase > palavra, para
    não cortar instruções passo a passo no meio;
  - a seção de cada chunk é a última linha de título ("## 3. ..." no Markdown ou
    "3. Título" no PDF) vista até o início do chunk, propagada entre páginas;
  - `prefixar_secao=True` injeta "[Seção: ...]" no texto do chunk: o título
    carrega vocabulário de busca ("Reinicialização remota básica") que o corpo
    do chunk nem sempre repete.
"""

import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_RE_TITULO_MD = re.compile(r"^#{1,3}\s+(.+?)\s*$")
_RE_TITULO_PDF = re.compile(r"^(\d+(?:\.\d+)*\.\s+[A-ZÀ-Ú].{0,90})$")


def _titulo(linha: str):
    linha = linha.strip()
    m = _RE_TITULO_MD.match(linha) or _RE_TITULO_PDF.match(linha)
    return m.group(1).strip() if m else None


def _ultimo_titulo_ate(texto: str, posicao: int):
    ultimo = None
    for m in re.finditer(r"^.*$", texto[: posicao + 1], flags=re.MULTILINE):
        t = _titulo(m.group(0))
        if t:
            ultimo = t
    return ultimo


def _primeiro_titulo_em(texto: str):
    for linha in texto.splitlines():
        t = _titulo(linha)
        if t:
            return t
    return None


def _segmentos_por_secao(texto: str, secao_inicial):
    """Divide o texto em (titulo, trecho) a cada linha de título; o título abre o seu segmento."""
    segs, titulo, buf = [], secao_inicial, []
    for linha in texto.splitlines():
        t = _titulo(linha)
        if t:
            if "".join(buf).strip():
                segs.append((titulo, "\n".join(buf)))
            titulo, buf = t, [linha]
        else:
            buf.append(linha)
    if "".join(buf).strip():
        segs.append((titulo, "\n".join(buf)))
    return segs


def dividir(
    docs: list[Document],
    chunk_size: int,
    chunk_overlap: int,
    prefixar_secao: bool = False,
    por_secao: bool = False,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
        add_start_index=True,
    )
    chunks: list[Document] = []
    secao_corrente: dict[str, str] = {}  # propaga a seção entre páginas do mesmo arquivo
    contador: dict[str, int] = {}

    for doc in docs:
        arquivo = doc.metadata["arquivo"]
        if por_secao:
            # Chunking AWARE de seção: nenhum chunk cruza a fronteira de um título. Cada item de
            # FAQ / seção de manual vira unidade própria, e a seção citada é a do conteúdo real.
            for titulo, segmento in _segmentos_por_secao(doc.page_content, secao_corrente.get(arquivo)):
                secao = titulo or "Introdução"
                for parte in splitter.split_text(segmento):
                    texto = parte.strip()
                    if not texto:
                        continue
                    n = contador.get(arquivo, 0)
                    contador[arquivo] = n + 1
                    if prefixar_secao:
                        texto = f"[Seção: {secao}]\n{texto}"
                    chunks.append(Document(page_content=texto, metadata={
                        "arquivo": arquivo, "pagina": doc.metadata.get("pagina", 1), "secao": secao,
                        "chunk_id": f"{arquivo}#{n}", "tipo": doc.metadata.get("tipo", "")}))
                    secao_corrente[arquivo] = titulo or secao_corrente.get(arquivo)
            continue
        for parte in splitter.split_documents([doc]):
            inicio = parte.metadata.get("start_index", 0)
            secao = _ultimo_titulo_ate(doc.page_content, inicio)
            if secao is None:
                # início de página no meio de uma seção: herda a seção da página anterior
                secao = secao_corrente.get(arquivo) or _primeiro_titulo_em(parte.page_content) or "Introdução"
            # se o chunk contém um título depois do início, a seção "corrente" avança
            ultimo_no_chunk = None
            for linha in parte.page_content.splitlines():
                t = _titulo(linha)
                if t:
                    ultimo_no_chunk = t
            secao_corrente[arquivo] = ultimo_no_chunk or secao

            n = contador.get(arquivo, 0)
            contador[arquivo] = n + 1
            texto = parte.page_content.strip()
            if not texto:
                continue
            if prefixar_secao:
                texto = f"[Seção: {secao}]\n{texto}"
            chunks.append(
                Document(
                    page_content=texto,
                    metadata={
                        "arquivo": arquivo,
                        "pagina": doc.metadata.get("pagina", 1),
                        "secao": secao,
                        "chunk_id": f"{arquivo}#{n}",
                        "tipo": doc.metadata.get("tipo", ""),
                    },
                )
            )
    return chunks
