"""
src/rag/loader.py
-----------------
Carregamento dos documentos da base de conhecimento (Aula 06):

  - PDFs (manuais e regimento)  -> PyMuPDFLoader   (uma Document por página)
  - Markdown/TXT (FAQ, tabelas) -> TextLoader

Cada Document recebe os metadados `arquivo`, `pagina` e `tipo`, usados depois
para a citação de fonte (documento/seção/página).
"""

import re
from pathlib import Path
from typing import Iterable, Optional

from langchain_core.documents import Document

from src.rag.config import KB_DIR, RAIZ


_RE_TITULO_NUMERADO = re.compile(r"^\d+(?:\.\d+)*\.\s+[A-ZÀ-Ú]")


def reflow_pdf(texto: str) -> str:
    """
    Reconstitui parágrafos em texto extraído de PDF. O PyMuPDF devolve uma linha por
    quebra visual; se o splitter cortasse em "\\n", as sentenças seriam partidas no meio
    ("...gateway do EV" / "ChargeOps"). Aqui as linhas de continuação são unidas, os
    títulos numerados ficam isolados e os parágrafos separados por linha em branco.
    """
    paragrafos: list[str] = []
    buf = ""
    for linha in texto.splitlines():
        l = linha.strip()
        if not l:
            continue
        if _RE_TITULO_NUMERADO.match(l):
            if buf:
                paragrafos.append(buf)
                buf = ""
            paragrafos.append(l)
        elif buf and not buf.endswith((".", "!", "?", ":")):
            buf += " " + l
        else:
            if buf:
                paragrafos.append(buf)
            buf = l
    if buf:
        paragrafos.append(buf)
    return "\n\n".join(paragrafos)


_RE_NOVO_ITEM_MD = re.compile(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||<)")


def reflow_md(texto: str) -> str:
    """Une linhas de um mesmo parágrafo em Markdown com quebra manual (hard wrap)."""
    saida: list[str] = []
    for linha in texto.splitlines():
        l = linha.rstrip()
        if not l.strip():
            saida.append("")
        elif saida and saida[-1] and not _RE_NOVO_ITEM_MD.match(l.lstrip()) and not saida[-1].startswith("#"):
            saida[-1] += " " + l.strip()
        else:
            saida.append(l.strip())
    return "\n".join(saida)


def _carregar_pdf(caminho: Path) -> list[Document]:
    from langchain_community.document_loaders import PyMuPDFLoader

    paginas = PyMuPDFLoader(str(caminho)).load()
    for p in paginas:
        p.page_content = reflow_pdf(p.page_content)
        p.metadata = {
            "arquivo": caminho.name,
            "pagina": int(p.metadata.get("page", 0)) + 1,
            "tipo": "pdf",
        }
    return paginas


def _carregar_texto(caminho: Path) -> list[Document]:
    texto = reflow_md(caminho.read_text(encoding="utf-8"))
    return [Document(page_content=texto, metadata={"arquivo": caminho.name, "pagina": 1, "tipo": "md"})]


def carregar_base(
    diretorio: Optional[Path] = None,
    extras: Optional[Iterable[Path]] = None,
) -> list[Document]:
    """
    Carrega todos os documentos de `diretorio` (padrão: data/knowledge_base/),
    sem entrar em subpastas (fontes_md/ guarda só os originais em Markdown dos
    PDFs). `extras` permite incluir arquivos avulsos (usado nos testes de
    prompt injection via documento, com fixtures em evals/fixtures/).
    """
    diretorio = Path(diretorio or KB_DIR)
    arquivos = sorted(
        p for p in diretorio.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".md", ".txt"}
    )
    arquivos += [Path(e) for e in (extras or [])]
    if not arquivos:
        raise FileNotFoundError(f"Nenhum documento encontrado em {diretorio}")

    docs: list[Document] = []
    for caminho in arquivos:
        docs.extend(_carregar_pdf(caminho) if caminho.suffix.lower() == ".pdf" else _carregar_texto(caminho))
    return docs


def carregar_system_prompt_v1() -> list[Document]:
    """Base do baseline Sprints 1/2: o único 'conhecimento' era o system prompt v1."""
    caminho = RAIZ / "prompts" / "system_prompt_v1.md"
    return _carregar_texto(caminho)
