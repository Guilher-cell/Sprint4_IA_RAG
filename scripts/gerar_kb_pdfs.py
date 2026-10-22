"""
scripts/gerar_kb_pdfs.py
------------------------
Converte as fontes em Markdown de data/knowledge_base/fontes_md/ nos PDFs de
data/knowledge_base/ (manuais e regimento), que são lidos pelo PyMuPDFLoader no
pipeline RAG (exigência da Sprint 04, item 2).

Os documentos do domínio são escritos em Markdown (fácil de versionar/revisar)
e publicados em PDF para exercitar o loader de PDF como em um cenário real, em
que manuais de produto chegam nesse formato.

Uso:  python scripts/gerar_kb_pdfs.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

RAIZ = Path(__file__).resolve().parents[1]
ORIGEM = RAIZ / "data" / "knowledge_base" / "fontes_md"
DESTINO = RAIZ / "data" / "knowledge_base"

FONTES_PDF = [
    "manual_ev_chargeops_sindico",
    "manual_ev_chargeops_morador",
    "manual_chargegrid_diagnostico_tecnico",
    "manual_orquestracao_potencia_chargegrid",
    "regimento_carregamento_compartilhado",
]

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _registrar_fontes() -> tuple[str, str]:
    """Usa DejaVu (suporta acentos) quando disponível; senão, Helvetica."""
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", str(_FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(
            TTFont("DejaVu-Bold", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        )
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def converter(nome: str) -> Path:
    normal, negrito = _registrar_fontes()
    estilo_t = ParagraphStyle("t", fontName=negrito, fontSize=16, leading=20, spaceAfter=10)
    estilo_h = ParagraphStyle("h", fontName=negrito, fontSize=12, leading=15, spaceBefore=12, spaceAfter=5)
    estilo_p = ParagraphStyle("p", fontName=normal, fontSize=10, leading=14, spaceAfter=6)

    linhas = (ORIGEM / f"{nome}.md").read_text(encoding="utf-8").splitlines()
    elementos = []
    for linha in linhas:
        linha = linha.rstrip()
        if not linha:
            continue
        if linha.startswith("# "):
            elementos.append(Paragraph(escape(linha[2:]), estilo_t))
        elif linha.startswith("## "):
            elementos.append(Paragraph(escape(linha[3:]), estilo_h))
        else:
            elementos.append(Paragraph(escape(linha), estilo_p))

    saida = DESTINO / f"{nome}.pdf"
    doc = SimpleDocTemplate(
        str(saida), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm, title=nome, author="Equipe EV Challenge",
    )
    doc.build(elementos)
    return saida


if __name__ == "__main__":
    for n in FONTES_PDF:
        print("gerado:", converter(n).relative_to(RAIZ))
