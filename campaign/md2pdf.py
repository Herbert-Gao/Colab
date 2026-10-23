"""Render a Markdown document to PDF.

The report tools live in their own environment
(``envs/report-tools``, reportlab) so that the training environment stays
untouched.  The Chinese glyphs come from the Droid Sans Fallback font that
PyMuPDF ships (``assets/fonts/cjk.ttf``), embedded into the PDF.

    envs/report-tools/bin/python campaign/md2pdf.py docs/eval_report.md
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "cjk.ttf"
FONT_NAME = "CJK"


def register_font() -> None:
    if FONT.is_file():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT)))
    else:  # pragma: no cover - the report would render without Chinese glyphs
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def styles() -> dict:
    return {
        "h1": ParagraphStyle("h1", fontName=FONT_NAME, fontSize=15, leading=20, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=FONT_NAME, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", fontName=FONT_NAME, fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("body", fontName=FONT_NAME, fontSize=9, leading=13.5, spaceAfter=3,
                               alignment=TA_LEFT),
        "bullet": ParagraphStyle("bullet", fontName=FONT_NAME, fontSize=9, leading=13.5,
                                  leftIndent=10, spaceAfter=2),
        "cell": ParagraphStyle("cell", fontName=FONT_NAME, fontSize=7.6, leading=10),
        "cellhead": ParagraphStyle("cellhead", fontName=FONT_NAME, fontSize=7.6, leading=10),
    }


def inline(text: str) -> str:
    """Markdown inline markup to the reportlab paragraph markup."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"\1", escaped)
    return escaped


def parse_table(rows: list[list[str]], style: dict) -> Table:
    data = []
    for index, row in enumerate(rows):
        cell_style = style["cellhead"] if index == 0 else style["cell"]
        data.append([Paragraph(inline(cell), cell_style) for cell in row])
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa4b2")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def convert(markdown: Path, pdf: Path) -> None:
    register_font()
    style = styles()
    story = []
    lines = markdown.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip():
            index += 1
            continue
        if line.startswith("!["):
            # A chart reference: the image is embedded below the caption.
            match = re.search(r"\]\((.+?)\)", line)
            if match:
                image = Path(match.group(1))
                if not image.is_absolute():
                    image = markdown.parent / image
                if image.is_file():
                    from reportlab.platypus import Image
                    width = 165 * mm
                    story.append(Image(str(image), width=width, height=width * 0.45))
                    story.append(Spacer(1, 4))
            index += 1
            continue
        if line.startswith("|"):
            block = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(set(cell) <= set("-: ") and cell for cell in cells):
                    block.append(cells)
                index += 1
            if block:
                story.append(parse_table(block, style))
                story.append(Spacer(1, 6))
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), style["h3"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), style["h2"]))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), style["h1"]))
        elif line.startswith("- "):
            story.append(Paragraph("• " + inline(line[2:]), style["bullet"]))
        else:
            story.append(Paragraph(inline(line), style["body"]))
        index += 1

    document = SimpleDocTemplate(
        str(pdf), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=markdown.stem)
    document.build(story)
    print(f"pdf -> {pdf} ({pdf.stat().st_size / 1024:.0f} KiB)")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: md2pdf.py <markdown> [pdf]")
        return 2
    markdown = Path(sys.argv[1])
    pdf = Path(sys.argv[2]) if len(sys.argv) > 2 else markdown.with_suffix(".pdf")
    convert(markdown, pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
