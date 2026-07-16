"""
pdf_utils.py — Geração do relatório PDF do Control.ILL
Compatível com amostras retornando 2 ou 3 colunas (amostra, inserido_em, inserido_por)
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Paleta ───────────────────────────────────────────────────────────────────
COR_PRINCIPAL  = colors.HexColor("#0F3D3E")
COR_SECUNDARIA = colors.HexColor("#1F4E5F")
COR_GRAFITE    = colors.HexColor("#263238")
COR_CINZA      = colors.HexColor("#607D8B")
COR_FUNDO      = colors.HexColor("#F4F6F8")
COR_BORDA      = colors.HexColor("#E0E6EA")
COR_OK         = colors.HexColor("#2E7D32")
COR_ERRO       = colors.HexColor("#C62828")
COR_AVISO      = colors.HexColor("#F9A825")
BRANCO         = colors.white

PAGE_W, PAGE_H = A4
MARGEM = 2 * cm


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COR_CINZA)
    y = MARGEM - 0.6 * cm
    canvas.drawString(MARGEM, y,
        "Registro gerado eletronicamente pelo Control.ILL.")
    canvas.drawString(MARGEM, y - 0.4 * cm,
        "Este registro contém apenas números de amostras/etiquetas para fins de rastreabilidade de uso do lote, sem identificação direta de pacientes.")
    canvas.drawRightString(PAGE_W - MARGEM, y, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf(lote: dict, amostras: list, termo_amostras: str = "dosadas") -> bytes:
    """
    Gera o PDF do lote.
    amostras: lista de tuplas com 2 ou 3 elementos (amostra, inserido_em, [inserido_por])
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=MARGEM + 1.2 * cm,
        title="Control.ILL — Registro de Validação e Rastreabilidade de Lote",
    )

    estilos = getSampleStyleSheet()

    e_titulo_cab = ParagraphStyle("TituloCab", fontName="Helvetica-Bold", fontSize=20,
        textColor=BRANCO, alignment=TA_LEFT, spaceAfter=2)
    e_subtitulo_cab = ParagraphStyle("SubCab", fontName="Helvetica", fontSize=8,
        textColor=colors.HexColor("#D9EAF2"), alignment=TA_LEFT)
    e_secao = ParagraphStyle("Secao", fontName="Helvetica-Bold", fontSize=9.5,
        textColor=BRANCO, alignment=TA_LEFT, leftIndent=6, spaceBefore=2, spaceAfter=2)
    e_label = ParagraphStyle("Label", fontName="Helvetica-Bold", fontSize=8.5, textColor=COR_GRAFITE)
    e_valor = ParagraphStyle("Valor", fontName="Helvetica", fontSize=8.5, textColor=COR_GRAFITE)
    e_total = ParagraphStyle("Total", fontName="Helvetica-Bold", fontSize=10, textColor=COR_PRINCIPAL)
    e_rodape = ParagraphStyle("Rod", fontName="Helvetica", fontSize=7, textColor=COR_CINZA)

    # Dados
    nome_exame    = lote.get("nome_exame") or "—"
    fabricante    = lote.get("fabricante") or "—"
    lote_reagente = lote.get("lote_reagente") or "—"
    validade      = lote.get("validade") or "—"
    setor         = lote.get("setor") or "—"
    cod_val       = lote.get("cod_validacao") or ""
    responsavel   = lote.get("responsavel") or "—"
    dt_abertura   = lote.get("dt_abertura") or "—"
    dt_fechamento = lote.get("dt_fechamento") or "Em aberto"
    aberto_por    = lote.get("aberto_por") or "—"
    fechado_por   = lote.get("fechado_por") or "—"
    total_am      = len(amostras)

    import re
    validado = bool(re.match(r"^VL_\d{4}_\w+$", cod_val)) if cod_val else False
    vencido  = False
    try:
        from datetime import date
        vencido = datetime.strptime(validade, "%d/%m/%Y").date() < date.today()
    except Exception:
        pass

    story = []
    col_larg = (PAGE_W - 2 * MARGEM) / 2

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    cab_data = [[
        [Paragraph("Control.ILL", e_titulo_cab),
         Paragraph("Sistema de Registro, Validação e Rastreabilidade de Lotes Laboratoriais", e_subtitulo_cab)]
    ]]
    cab_t = Table(cab_data, colWidths=[PAGE_W - 2 * MARGEM])
    cab_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), COR_PRINCIPAL),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
    ]))
    story.append(cab_t)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Registro de Validação e Rastreabilidade de Lote",
        ParagraphStyle("DT", fontName="Helvetica-Bold", fontSize=13, textColor=COR_GRAFITE)
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COR_PRINCIPAL, spaceAfter=6))

    # Alertas no PDF
    if vencido:
        at = Table([[Paragraph("⚠️ VALIDADE EXPIRADA — Lote vencido.",
            ParagraphStyle("Av", fontName="Helvetica-Bold", fontSize=9, textColor=COR_ERRO))]],
            colWidths=[PAGE_W - 2*MARGEM])
        at.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#FFEBEE")),
            ("BOX",(0,0),(-1,-1),1,COR_ERRO),("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),10)]))
        story.append(at); story.append(Spacer(1, 0.2*cm))

    if not validado:
        nv = Table([[Paragraph("🔴 Lote ainda não validado para uso.",
            ParagraphStyle("NV", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#E65100")))]],
            colWidths=[PAGE_W - 2*MARGEM])
        nv.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#FFF8E1")),
            ("BOX",(0,0),(-1,-1),1,COR_AVISO),("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),10)]))
        story.append(nv); story.append(Spacer(1, 0.2*cm))

    def bloco(titulo):
        t = Table([[Paragraph(titulo, e_secao)]], colWidths=[PAGE_W - 2*MARGEM])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),COR_SECUNDARIA),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8)]))
        return t

    def campo(label, valor):
        return [Paragraph(label, e_label), Paragraph(valor or "—", e_valor)]

    # ── Seção 1 ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.15*cm))
    story.append(bloco("1. Identificação do Lote"))
    story.append(Spacer(1, 0.1*cm))
    t1 = Table([
        campo("Setor", setor),
        campo("Nome do Exame/Teste", nome_exame),
        campo("Lote do Reagente", lote_reagente),
        campo("Fabricante", fabricante),
        campo("Validade do Lote", validade + (" ⚠️ VENCIDO" if vencido else "")),
    ], colWidths=[col_larg * 0.45, col_larg * 1.55])
    t1.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),8.5),("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BRANCO,COR_FUNDO]),
        ("BOX",(0,0),(-1,-1),0.5,COR_BORDA),("INNERGRID",(0,0),(-1,-1),0.3,COR_BORDA),
    ]))
    story.append(t1)

    # ── Seção 2 ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.25*cm))
    story.append(bloco("2. Dados da Validação"))
    story.append(Spacer(1, 0.1*cm))
    t2 = Table([
        campo("Código de Validação", cod_val if cod_val else "Não informado"),
        campo("Status da Validação", "✅ Validado" if validado else "🔴 Não validado"),
        campo("Responsável pela Validação", responsavel),
        campo("Data de Abertura", dt_abertura),
        campo("Aberto por", aberto_por),
        campo("Data de Fechamento", dt_fechamento),
        campo("Fechado por", fechado_por),
    ], colWidths=[col_larg * 0.55, col_larg * 1.45])
    t2.setStyle(TableStyle([
        ("FONTSIZE",(0,0),(-1,-1),8.5),("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BRANCO,COR_FUNDO]),
        ("BOX",(0,0),(-1,-1),0.5,COR_BORDA),("INNERGRID",(0,0),(-1,-1),0.3,COR_BORDA),
    ]))
    story.append(t2)

    # ── Seção 3: Tabela de amostras ───────────────────────────────────────────
    story.append(Spacer(1, 0.25*cm))
    story.append(bloco("3. Rastreabilidade de Uso do Lote"))
    story.append(Spacer(1, 0.08*cm))
    story.append(Paragraph(
        f"Amostras {termo_amostras} com o lote do teste",
        ParagraphStyle("SubSec", fontName="Helvetica", fontSize=8.5,
            textColor=COR_CINZA, leftIndent=4, spaceAfter=4)
    ))

    if amostras:
        # Detectar número de colunas (2 ou 3)
        tem_responsavel = len(amostras[0]) >= 3

        col_n  = (PAGE_W - 2*MARGEM) * (0.30 if tem_responsavel else 0.35)
        col_am = (PAGE_W - 2*MARGEM) * (0.30 if tem_responsavel else 0.35)
        col_dt = (PAGE_W - 2*MARGEM) * (0.25 if tem_responsavel else 0.30)
        col_rs = (PAGE_W - 2*MARGEM) * 0.15

        e_cab_am = ParagraphStyle("CabAm", fontName="Helvetica-Bold",
            textColor=BRANCO, fontSize=8)
        e_cel_am = ParagraphStyle("CelAm", fontName="Helvetica",
            textColor=COR_GRAFITE, fontSize=8)

        if tem_responsavel:
            cabecalho = [
                Paragraph("Nome do Exame/Teste", e_cab_am),
                Paragraph("Amostra/Etiqueta",    e_cab_am),
                Paragraph("Inserido em",          e_cab_am),
                Paragraph("Por",                  e_cab_am),
            ]
            col_widths = [col_n, col_am, col_dt, col_rs]
        else:
            cabecalho = [
                Paragraph("Nome do Exame/Teste", e_cab_am),
                Paragraph("Amostra/Etiqueta",    e_cab_am),
                Paragraph("Inserido em",          e_cab_am),
            ]
            col_widths = [col_n, col_am, col_dt + col_rs]

        am_rows = [cabecalho]
        for entrada in amostras:
            am   = entrada[0] if len(entrada) > 0 else "—"
            ins_em = entrada[1] if len(entrada) > 1 else "—"
            por  = entrada[2] if len(entrada) > 2 else ""

            if tem_responsavel:
                am_rows.append([
                    Paragraph(nome_exame, e_cel_am),
                    Paragraph(am,         e_cel_am),
                    Paragraph(ins_em or "—", e_cel_am),
                    Paragraph(por or "—", e_cel_am),
                ])
            else:
                am_rows.append([
                    Paragraph(nome_exame, e_cel_am),
                    Paragraph(am,         e_cel_am),
                    Paragraph(ins_em or "—", e_cel_am),
                ])

        am_t = Table(am_rows, colWidths=col_widths, repeatRows=1)
        am_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),COR_GRAFITE),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[BRANCO,COR_FUNDO]),
            ("BOX",(0,0),(-1,-1),0.5,COR_BORDA),("INNERGRID",(0,0),(-1,-1),0.3,COR_BORDA),
        ]))
        story.append(am_t)
    else:
        story.append(Paragraph("Nenhuma amostra registrada.",
            ParagraphStyle("SemAm", fontName="Helvetica", textColor=COR_CINZA, leftIndent=6)))

    # ── Seção 4: Resumo ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.25*cm))
    story.append(bloco("4. Resumo de Uso do Lote"))
    story.append(Spacer(1, 0.1*cm))
    res_t = Table([[Paragraph(
        f"Total de amostras {termo_amostras} com este lote: {total_am}", e_total
    )]], colWidths=[PAGE_W - 2*MARGEM])
    res_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#E3F2FD")),
        ("BOX",(0,0),(-1,-1),1,COR_SECUNDARIA),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),12),
    ]))
    story.append(res_t)

    # ── Seção 5: Observações ──────────────────────────────────────────────────
    story.append(Spacer(1, 0.25*cm))
    story.append(bloco("5. Observações"))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph("Sem observações registradas.",
        ParagraphStyle("Obs", fontName="Helvetica", textColor=COR_CINZA, leftIndent=6)))

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COR_BORDA))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph("Registro gerado eletronicamente pelo Control.ILL.",
        ParagraphStyle("R1", fontName="Helvetica", fontSize=7, textColor=COR_CINZA)))
    story.append(Paragraph(
        "Este registro contém apenas números de amostras/etiquetas para fins de rastreabilidade de uso do lote, sem identificação direta de pacientes.",
        ParagraphStyle("R2", fontName="Helvetica", fontSize=7, textColor=COR_CINZA)))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
