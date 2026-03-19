"""
pdf_generator.py - Geração do PDF final com cabeçalho em todas as páginas.
Usa ReportLab para montar o documento A4.
Portado do DocPopular para o DocPopularEditor.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PAGE_W, PAGE_H = A4
MARGIN = 10 * mm
HEADER_H = 20 * mm


def _draw_header(c: canvas.Canvas, autorizacao: str, data: str) -> None:
    """Desenha o cabeçalho no topo de cada página."""
    header_text = f"AUTORIZAÇÃO {autorizacao} - DATA {data}"

    c.setFillColor(colors.HexColor("#0D3B66"))
    c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H - HEADER_H + 7 * mm, header_text)


def gerar_pdf(
    imagens: List[PILImage.Image],
    autorizacao: str,
    data: str,
    output_folder: str,
) -> Path:
    """Gera um arquivo PDF com todas as imagens, com cabeçalho em cada página."""
    data_safe = data.replace("/", "-")
    filename = f"AUTORIZAÇÃO {autorizacao} - DATA {data_safe}.pdf"
    output_path = Path(output_folder) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content_top = PAGE_H - HEADER_H - MARGIN
    content_h = PAGE_H - HEADER_H - 2 * MARGIN
    content_w = PAGE_W - 2 * MARGIN

    c = canvas.Canvas(str(output_path), pagesize=A4)

    for img in imagens:
        _draw_header(c, autorizacao, data)

        img_w, img_h = img.size
        ratio = min(content_w / img_w, content_h / img_h)
        draw_w = img_w * ratio
        draw_h = img_h * ratio

        x = MARGIN + (content_w - draw_w) / 2
        y = content_top - draw_h

        img_buffer = io.BytesIO()
        img.save(img_buffer, format="JPEG", quality=85)
        img_buffer.seek(0)
        reader = ImageReader(img_buffer)

        c.drawImage(reader, x, y, width=draw_w, height=draw_h)
        c.showPage()

    c.save()
    return output_path


def gerar_pdf_transacao(transaction) -> bytes:
    """
    Gera um PDF em memória com todas as imagens de todas as etapas da transação.
    Retorna os bytes do PDF, sem salvar em disco.
    """
    from src.core.date_manager import formatar_data_hoje

    data_hoje = formatar_data_hoje()
    autorizacao = getattr(transaction, "numero_autorizacao", transaction.nome_tipo)

    content_top = PAGE_H - HEADER_H - MARGIN
    content_h = PAGE_H - HEADER_H - 2 * MARGIN
    content_w = PAGE_W - 2 * MARGIN

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    for etapa in transaction.etapas:
        for img in etapa.imagens:
            _draw_header(c, autorizacao, data_hoje)

            img_w, img_h = img.size
            ratio = min(content_w / img_w, content_h / img_h)
            draw_w = img_w * ratio
            draw_h = img_h * ratio

            x = MARGIN + (content_w - draw_w) / 2
            y = content_top - draw_h

            img_buf = io.BytesIO()
            img_rgb = img.convert("RGB")
            img_rgb.save(img_buf, format="JPEG", quality=85)
            img_buf.seek(0)
            reader = ImageReader(img_buf)

            c.drawImage(reader, x, y, width=draw_w, height=draw_h)
            c.showPage()

    c.save()
    return buffer.getvalue()
