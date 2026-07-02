"""
pdf_utils.py — Geração do relatório PDF do Control.ILL
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Paleta ───────────────────────────────────────────────────────────────────
COR_PRINCIPAL   = colors.HexColor("#0F3D3E")
COR_SECUNDARIA  = colors.HexColor("#1F4E5F")
COR_GRAFITE     = colors.HexColor("#263238")
COR_CINZA       = colors.HexColor("#607D8B")
COR_FUNDO_LINHA = colors.HexColor("#F4F6F8")
COR_BORDA       = colors.HexColor("#E0E6EA")
COR_OK          = colors.HexColor("#2E7D32")
COR_ERRO        = colors.HexColor("#C62828")
COR_AVISO       = colors.HexColor("#F9A825")
BRANCO          = colors.white

PAGE_W, PAGE_H = A4
MARGEM = 2 * cm


def _numero_paginas(canvas, doc):
    """Footer com paginação."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COR_CINZA)
    y_rod = MARGEM - 0.6 * cm
    canvas.drawString(MARGEM, y_rod,
        "Registro gerado eletronicamente pelo Control.ILL.")
    canvas.drawString(MARGEM, y_rod - 0.4 * cm,
        "Este registro contém apenas números de amostras/etiquetas para fins de rastreabilidade de uso do lote, sem identificação direta de pacientes.")
    pg_txt = f"Página {doc.page} de {doc.page}"   # será sobrescrito abaixo
    canvas.drawRightString(PAGE_W - MARGEM, y_rod, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf(lote: dict, amostras: list, termo_amostras: str = "dosadas") -> bytes:
    """
    Gera o relatório PDF conforme especificação Control.ILL.
    termo_amostras: 'dosadas' (padrão) ou 'processadas' (Microbiologia).
    """
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=MARGEM,
        bottomMargin=MARGEM + 1.2 * cm,
        title="Control.ILL — Registro de Validação e Rastreabilidade de Lote",
    )

    estilos = getSampleStyleSheet()

    # ── Estilos personalizados ────────────────────────────────────────────────
    e_titulo_doc = ParagraphStyle(
        "TituloDoc", parent=estilos["Normal"],
        fontName="Helvetica-Bold", fontSize=18,
        textColor=COR_PRINCIPAL, alignment=TA_LEFT, spaceAfter=2,
    )
    e_subtitulo_doc = ParagraphStyle(
        "SubtituloDoc", parent=estilos["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=COR_CINZA, alignment=TA_LEFT, spaceAfter=6,
    )
    e_titulo_doc2 = ParagraphStyle(
        "TituloDoc2", parent=estilos["Normal"],
        fontName="Helvetica-Bold", fontSize=11,
        textColor=COR_GRAFITE, alignment=TA_LEFT, spaceAfter=4,
    )
    e_secao = ParagraphStyle(
        "Secao", parent=estilos["Normal"],
        fontName="Helvetica-Bold", fontSize=9.5,
        textColor=BRANCO, alignment=TA_LEFT,
        leftIndent=6, spaceBefore=2, spaceAfter=2,
    )
    e_campo_label = ParagraphStyle(
        "CampoLabel", parent=estilos["Normal"],
        fontName="Helvetica-Bold", fontSize=8.5,
        textColor=COR_GRAFITE,
    )
    e_campo_valor = ParagraphStyle(
        "CampoValor", parent=estilos["Normal"],
        fontName="Helvetica", fontSize=8.5,
        textColor=COR_GRAFITE,
    )
    e_rodape = ParagraphStyle(
        "Rodape", parent=estilos["Normal"],
        fontName="Helvetica", fontSize=7,
        textColor=COR_CINZA,
    )
    e_total = ParagraphStyle(
        "Total", parent=estilos["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=COR_PRINCIPAL,
    )

    # ── Dados ────────────────────────────────────────────────────────────────
    nome_exame    = lote.get("nome_exame") or "—"
    fabricante    = lote.get("fabricante") or "—"
    lote_reagente = lote.get("lote_reagente") or "—"
    validade      = lote.get("validade") or "—"
    setor         = lote.get("setor") or "—"
    cod_val       = lote.get("cod_validacao") or ""
    responsavel   = lote.get("responsavel") or "—"
    dt_abertura   = lote.get("dt_abertura") or "—"
    dt_fechamento = lote.get("dt_fechamento") or "Em aberto"
    total_am      = len(amostras)

    import re as _re
    validado = bool(_re.match(r"^VL_\d{4}_\w+$", cod_val)) if cod_val else False

    # Verificar vencimento
    vencido = False
    try:
        val_d = datetime.strptime(validade, "%d/%m/%Y").date()
        from datetime import date
        vencido = val_d < date.today()
    except Exception:
        pass

    story = []

    # ── CABEÇALHO ─────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("Control.ILL", e_titulo_doc),
        ""
    ]]
    header_table = Table(header_data, colWidths=[PAGE_W - 2 * MARGEM - 2, 2])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_PRINCIPAL),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))

    # Override para cor branca no cabeçalho
    e_titulo_cab = ParagraphStyle(
        "TituloCab", parent=e_titulo_doc,
        textColor=BRANCO, fontSize=20,
    )
    e_subtitulo_cab = ParagraphStyle(
        "SubtituloCab", parent=e_subtitulo_doc,
        textColor=colors.HexColor("#D9EAF2"), fontSize=8,
    )

    cab_data = [[
        [
            Paragraph("Control.ILL", e_titulo_cab),
            Paragraph("Sistema de Registro, Validação e Rastreabilidade de Lotes Laboratoriais", e_subtitulo_cab),
        ],
    ]]
    cab_table = Table(cab_data, colWidths=[PAGE_W - 2 * MARGEM])
    cab_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_PRINCIPAL),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(cab_table)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        "Registro de Validação e Rastreabilidade de Lote",
        ParagraphStyle("DocTitle", parent=e_titulo_doc2, fontSize=13, spaceAfter=2)
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COR_PRINCIPAL, spaceAfter=6))

    # ── Alerta validade ───────────────────────────────────────────────────────
    if vencido:
        alerta_data = [[Paragraph("⚠️  VALIDADE EXPIRADA — Lote vencido.", ParagraphStyle(
            "Alerta", parent=e_campo_label, textColor=COR_ERRO, fontSize=9
        ))]]
        alerta_t = Table(alerta_data, colWidths=[PAGE_W - 2 * MARGEM])
        alerta_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFEBEE")),
            ("BOX", (0, 0), (-1, -1), 1, COR_ERRO),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(alerta_t)
        story.append(Spacer(1, 0.2 * cm))

    if not validado:
        nval_data = [[Paragraph("🔴  Lote ainda não validado para uso.", ParagraphStyle(
            "NVal", parent=e_campo_label, textColor=colors.HexColor("#E65100"), fontSize=9
        ))]]
        nval_t = Table(nval_data, colWidths=[PAGE_W - 2 * MARGEM])
        nval_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E1")),
            ("BOX", (0, 0), (-1, -1), 1, COR_AVISO),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(nval_t)
        story.append(Spacer(1, 0.2 * cm))

    def _bloco_secao(titulo: str):
        sec_data = [[Paragraph(titulo, e_secao)]]
        sec_t = Table(sec_data, colWidths=[PAGE_W - 2 * MARGEM])
        sec_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COR_SECUNDARIA),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return sec_t

    def _campo(label: str, valor: str):
        return [Paragraph(label, e_campo_label), Paragraph(valor or "—", e_campo_valor)]

    col_larg = (PAGE_W - 2 * MARGEM) / 2

    # ── SEÇÃO 1: Identificação do Lote ────────────────────────────────────────
    story.append(Spacer(1, 0.15 * cm))
    story.append(_bloco_secao("1. Identificação do Lote"))
    story.append(Spacer(1, 0.1 * cm))

    ident_data = [
        _campo("Setor", setor),
        _campo("Nome do Exame/Teste", nome_exame),
        _campo("Lote do Reagente", lote_reagente),
        _campo("Fabricante", fabricante),
        _campo("Validade do Lote", validade + (" ⚠️ VENCIDO" if vencido else "")),
    ]
    ident_t = Table(ident_data, colWidths=[col_larg * 0.45, col_larg * 1.55])
    ident_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRANCO, COR_FUNDO_LINHA]),
        ("BOX", (0, 0), (-1, -1), 0.5, COR_BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COR_BORDA),
    ]))
    story.append(ident_t)

    # ── SEÇÃO 2: Dados da Validação ───────────────────────────────────────────
    story.append(Spacer(1, 0.25 * cm))
    story.append(_bloco_secao("2. Dados da Validação"))
    story.append(Spacer(1, 0.1 * cm))

    cod_display = cod_val if cod_val else "Não informado"
    val_status = "✅ Validado" if validado else "🔴 Não validado"

    valid_data = [
        _campo("Código de Validação", cod_display),
        _campo("Status da Validação", val_status),
        _campo("Responsável pela Validação", responsavel),
        _campo("Data de Abertura", dt_abertura),
        _campo("Data de Fechamento", dt_fechamento),
    ]
    valid_t = Table(valid_data, colWidths=[col_larg * 0.55, col_larg * 1.45])
    valid_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRANCO, COR_FUNDO_LINHA]),
        ("BOX", (0, 0), (-1, -1), 0.5, COR_BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COR_BORDA),
    ]))
    story.append(valid_t)

    # ── SEÇÃO 3: Rastreabilidade ──────────────────────────────────────────────
    story.append(Spacer(1, 0.25 * cm))
    story.append(_bloco_secao(f"3. Rastreabilidade de Uso do Lote"))
    story.append(Spacer(1, 0.08 * cm))
    story.append(Paragraph(
        f"Amostras {termo_amostras} com o lote do teste",
        ParagraphStyle("SubSecao", parent=e_campo_label, fontSize=8.5,
                       textColor=COR_CINZA, leftIndent=4, spaceAfter=4)
    ))

    if amostras:
        # Cabeçalho da tabela
        col_nome = (PAGE_W - 2 * MARGEM) * 0.35
        col_am   = (PAGE_W - 2 * MARGEM) * 0.30
        col_dt   = (PAGE_W - 2 * MARGEM) * 0.35

        cab_am = [
            Paragraph("Nome do Exame/Teste", ParagraphStyle(
                "CabAm", parent=e_campo_label, textColor=BRANCO, fontSize=8)),
            Paragraph("Amostra/Etiqueta", ParagraphStyle(
                "CabAm2", parent=e_campo_label, textColor=BRANCO, fontSize=8)),
            Paragraph("Inserido em", ParagraphStyle(
                "CabAm3", parent=e_campo_label, textColor=BRANCO, fontSize=8)),
        ]
        am_rows = [cab_am]
        for am, ins_em in amostras:
            am_rows.append([
                Paragraph(nome_exame, e_campo_valor),
                Paragraph(am, e_campo_valor),
                Paragraph(ins_em or "—", e_campo_valor),
            ])

        am_table = Table(am_rows, colWidths=[col_nome, col_am, col_dt], repeatRows=1)
        am_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COR_GRAFITE),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, COR_FUNDO_LINHA]),
            ("BOX", (0, 0), (-1, -1), 0.5, COR_BORDA),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, COR_BORDA),
        ]))
        story.append(am_table)
    else:
        story.append(Paragraph(
            "Nenhuma amostra registrada.",
            ParagraphStyle("SemAm", parent=e_campo_valor, textColor=COR_CINZA, leftIndent=6)
        ))

    # ── SEÇÃO 4: Resumo de Uso ────────────────────────────────────────────────
    story.append(Spacer(1, 0.25 * cm))
    story.append(_bloco_secao("4. Resumo de Uso do Lote"))
    story.append(Spacer(1, 0.1 * cm))

    resumo_data = [[
        Paragraph(
            f"Total de amostras {termo_amostras} com este lote: {total_am}",
            e_total
        )
    ]]
    resumo_t = Table(resumo_data, colWidths=[PAGE_W - 2 * MARGEM])
    resumo_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E3F2FD")),
        ("BOX", (0, 0), (-1, -1), 1, COR_SECUNDARIA),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(resumo_t)

    # ── SEÇÃO 5: Observações ──────────────────────────────────────────────────
    story.append(Spacer(1, 0.25 * cm))
    story.append(_bloco_secao("5. Observações"))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(
        "Sem observações registradas.",
        ParagraphStyle("ObsP", parent=e_campo_valor, textColor=COR_CINZA, leftIndent=6)
    ))

    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COR_BORDA))
    story.append(Spacer(1, 0.1 * cm))

    # Rodapé inline (além do _numero_paginas)
    story.append(Paragraph(
        "Registro gerado eletronicamente pelo Control.ILL.",
        ParagraphStyle("Rod1", parent=e_rodape, fontSize=7, textColor=COR_CINZA)
    ))
    story.append(Paragraph(
        "Este registro contém apenas números de amostras/etiquetas para fins de rastreabilidade de uso do lote, sem identificação direta de pacientes.",
        ParagraphStyle("Rod2", parent=e_rodape, fontSize=7, textColor=COR_CINZA)
    ))

    doc.build(story, onFirstPage=_numero_paginas, onLaterPages=_numero_paginas)
    return buf.getvalue()
