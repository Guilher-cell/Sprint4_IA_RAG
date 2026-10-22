"""
scripts/gerar_pdf.py
--------------------
Converte um relatório Markdown (subconjunto: #/##/###, parágrafos, listas, tabelas, citações,
**negrito**, `código`) em PDF A4 com reportlab, e informa o número de páginas.

    python scripts/gerar_pdf.py docs/relatorio_evolucao_sprint4.md            # -> .pdf ao lado
    python scripts/gerar_pdf.py docs/relatorio_rag.md --max-paginas 8
"""

import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = colors.HexColor("#1F3A5F")


def registrar_fontes() -> tuple[str, str, str]:
    """DejaVu (suporta acentos, '→', '≥', '✓'); cai em Helvetica se não houver."""
    for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"):
        regular, bold, mono = (Path(base) / n for n in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf"))
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("DV", str(regular)))
            pdfmetrics.registerFont(TTFont("DV-B", str(bold)))
            pdfmetrics.registerFont(TTFont("DV-M", str(mono if mono.exists() else regular)))
            pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")
            return "DV", "DV-B", "DV-M"
    return "Helvetica", "Helvetica-Bold", "Courier"


def inline(txt: str, mono: str) -> str:
    txt = escape(txt).replace("\\*", "&#42;")
    txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    txt = re.sub(r"`(.+?)`", rf'<font name="{mono}" color="#8B1A1A">\1</font>', txt)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", txt)


def construir(md: str, corpo: float, mono: str, normal: str, negrito: str):
    ss = getSampleStyleSheet()
    est = {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName=negrito, fontSize=15, leading=18, textColor=AZUL, alignment=TA_LEFT, spaceAfter=3),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=negrito, fontSize=corpo + 2.5, leading=corpo + 5, textColor=AZUL, spaceBefore=6, spaceAfter=2),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName=negrito, fontSize=corpo + 1, leading=corpo + 3.5, spaceBefore=4, spaceAfter=1),
        "p": ParagraphStyle("p", parent=ss["BodyText"], fontName=normal, fontSize=corpo, leading=corpo * 1.32, spaceAfter=2.5),
        "li": ParagraphStyle("li", parent=ss["BodyText"], fontName=normal, fontSize=corpo, leading=corpo * 1.3, leftIndent=11, bulletIndent=2, spaceAfter=1),
        "q": ParagraphStyle("q", parent=ss["BodyText"], fontName=normal, fontSize=corpo - 0.5, leading=corpo * 1.25, leftIndent=8, textColor=colors.HexColor("#444444"), spaceAfter=3),
        "cel": ParagraphStyle("cel", fontName=normal, fontSize=corpo - 1.6, leading=(corpo - 1.6) * 1.22),
        "celh": ParagraphStyle("celh", fontName=negrito, fontSize=corpo - 1.6, leading=(corpo - 1.6) * 1.22, textColor=colors.white),
    }
    fluxo, linhas, i = [], md.splitlines(), 0
    while i < len(linhas):
        l = linhas[i].rstrip()
        if not l.strip() or l.strip() == "---":
            i += 1
        elif l.startswith("```"):
            i += 1
            while i < len(linhas) and not linhas[i].startswith("```"):
                fluxo.append(Paragraph(escape(linhas[i]).replace(" ", "&nbsp;") or "&nbsp;",
                                       ParagraphStyle("c", fontName=mono, fontSize=corpo - 1.5, leading=corpo, leftIndent=6)))
                i += 1
            i += 1
        elif l.startswith("# "):
            fluxo.append(Paragraph(inline(l[2:], mono), est["h1"])); i += 1
        elif l.startswith("## "):
            fluxo.append(Paragraph(inline(l[3:], mono), est["h2"])); i += 1
        elif l.startswith("### "):
            fluxo.append(Paragraph(inline(l[4:], mono), est["h3"])); i += 1
        elif l.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].startswith("|"):
                bloco.append(linhas[i]); i += 1
            linhas_t = [[c.strip() for c in b.strip().strip("|").split("|")] for b in bloco if not re.match(r"^\|[\s:|-]+\|?$", b)]
            n = max(len(r) for r in linhas_t)
            dados = [[Paragraph(inline(c, mono), est["celh"] if r == 0 else est["cel"]) for c in (row + [""] * (n - len(row)))]
                     for r, row in enumerate(linhas_t)]
            larg = A4[0] - 28 * mm
            pesos = [max(len(re.sub(r"[`*]", "", row[c])) if c < len(row) else 1 for row in linhas_t) for c in range(n)]
            pesos = [min(max(p, 11), 46) for p in pesos]
            t = Table(dados, colWidths=[larg * p / sum(pesos) for p in pesos], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), AZUL), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C2CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
            fluxo += [t, Spacer(1, 3)]
        elif re.match(r"^\s*([-*]|\d+\.)\s+", l):
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", l)
            marca = "•" if m.group(2) in "-*" else m.group(2)
            fluxo.append(Paragraph(inline(m.group(3), mono), est["li"], bulletText=marca)); i += 1
        elif l.startswith(">"):
            citacao = []
            while i < len(linhas) and linhas[i].startswith(">"):
                citacao.append(linhas[i].lstrip("> ").strip()); i += 1
            fluxo.append(Paragraph(inline(" ".join(citacao), mono), est["q"]))
        else:
            par = [l.strip()]
            i += 1
            while i < len(linhas) and linhas[i].strip() and not re.match(r"^(#|\||>|```|\s*([-*]|\d+\.)\s)", linhas[i]):
                par.append(linhas[i].strip()); i += 1
            fluxo.append(Paragraph(inline(" ".join(par), mono), est["p"]))
    return fluxo


def gerar(md_path: Path, corpo: float) -> tuple[Path, int]:
    normal, negrito, mono = registrar_fontes()
    destino = md_path.with_suffix(".pdf")
    doc = SimpleDocTemplate(str(destino), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=md_path.stem, author="EV Challenge GoodWe")

    def rodape(canvas, d):
        canvas.setFont(normal, 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(14 * mm, 6 * mm, "FIAP × GoodWe · EV Challenge · Sprint 04")
        canvas.drawRightString(A4[0] - 14 * mm, 6 * mm, f"pág. {d.page}")

    doc.build(construir(md_path.read_text(encoding="utf-8"), corpo, mono, normal, negrito), onFirstPage=rodape, onLaterPages=rodape)
    from pypdf import PdfReader  # noqa: WPS433

    return destino, len(PdfReader(str(destino)).pages)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--max-paginas", type=int, default=None)
    ap.add_argument("--corpo", type=float, default=9.0, help="tamanho da fonte do corpo (pt)")
    args = ap.parse_args()
    destino, n = gerar(Path(args.markdown), args.corpo)
    print(f"{destino} — {n} página(s)")
    if args.max_paginas and n > args.max_paginas:
        sys.exit(f"ERRO: {n} páginas (máximo {args.max_paginas}). Reduza o texto ou use --corpo menor.")


if __name__ == "__main__":
    main()
