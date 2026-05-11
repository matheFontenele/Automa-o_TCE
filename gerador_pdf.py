# gerador_pdf.py
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==============================================================================
# FUNÇÕES DE FORMATAÇÃO EXCLUSIVAS DO RELATÓRIO
# ==============================================================================
def formatar_moeda_pdf(valor):
    try:
        if pd.isna(valor) or valor is None:
            return "0,00"
        val_float = float(valor)
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00"

def formatar_data_pdf(data_raw):
    try:
        if pd.isna(data_raw) or data_raw is None:
            return "Não Informada"
        data_str = str(data_raw).split('T')[0]
        partes = data_str.split('-')
        if len(partes) == 3:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_str
    except Exception:
        return "Não Informada"

# ==============================================================================
# GERADOR DO PDF
# ==============================================================================
def gerar_pdf_empenho(row):
    """Gera o PDF estruturado do empenho usando ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=54, 
        leftMargin=54, 
        topMargin=54, 
        bottomMargin=54
    )
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#ff4b4b'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    
    bold_style = ParagraphStyle(
        'TableBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story.append(Paragraph(f"TCE-CE — DETALHES DO EMPENHO Nº {row.get('numero_empenho', 'N/A')}", title_style))
    story.append(Spacer(1, 5))
    
    def criar_linha_tabela(label, valor):
        val_str = str(valor) if pd.notna(valor) and valor is not None else "Não informado"
        return [Paragraph(f"<b>{label}</b>", bold_style), Paragraph(val_str, body_style)]

    # Seção 1: Informações do Empenho
    story.append(Paragraph("INFORMAÇÕES DO EMPENHO", section_style))
    fornecedor = row.get('nome_negociante', row.get('nome_responsavel_pagamento', 'Não Informado'))
    cnpj_fornecedor = row.get('numero_documento_negociante', row.get('cpf_cnpj_emitente', 'Ocultado'))
    num_licitacao = row.get('numero_licitacao')
    num_licitacao_str = str(num_licitacao) if pd.notna(num_licitacao) else "Não informado"
    
    dados_empenho = [
        criar_linha_tabela("Número do empenho:", row.get('numero_empenho', 'N/A')),
        criar_linha_tabela("Data:", formatar_data_pdf(row.get('data_emissao_empenho'))),
        criar_linha_tabela("Valor:", f"R$ {formatar_moeda_pdf(row.get('valor_empenhado', 0.0))}"),
        criar_linha_tabela("Fornecedor:", fornecedor),
        criar_linha_tabela("CNPJ do fornecedor:", cnpj_fornecedor),
        criar_linha_tabela("Modalidade de licitação:", row.get('tipo_processo_licitatorio', 'N/A')),
        criar_linha_tabela("Número de licitação:", num_licitacao_str)
    ]
    
    t_empenho = Table(dados_empenho, colWidths=[150, 350])
    t_empenho.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_empenho)
    story.append(Spacer(1, 10))

    # Seção 2: Informações de Orçamento
    story.append(Paragraph("INFORMAÇÕES DE ORÇAMENTO", section_style))
    unidade_gestora = row.get('nome_unidade_gestora', row.get('codigo_unidade_gestora', 'Não Informado'))
    proj_ativ = f"{row.get('codigo_projeto_atividade', '')}.{row.get('numero_projeto_atividade', '')}" if pd.notna(row.get('codigo_projeto_atividade')) else "Não informado"
    
    dados_orcamento = [
        criar_linha_tabela("Unidade gestora:", unidade_gestora),
        criar_linha_tabela("Órgão:", f"{row.get('codigo_orgao', 'N/A')} - {row.get('nome_orgao', 'Secretaria Municipal')}"[:90]),
        criar_linha_tabela("Unidade orçamentária:", row.get('codigo_unidade_orcamentaria', 'N/A')),
        criar_linha_tabela("Proj. atividade:", proj_ativ),
        criar_linha_tabela("Natureza:", row.get('descricao_elemento_despesa', 'N/A')[:90]),
        criar_linha_tabela("Função:", row.get('codigo_funcao', 'N/A')),
        criar_linha_tabela("Sub-função:", row.get('codigo_subfuncao', 'N/A')),
        criar_linha_tabela("Fonte de recurso:", row.get('fonte_recurso', 'Não Informada'))
    ]
    
    t_orcamento = Table(dados_orcamento, colWidths=[150, 350])
    t_orcamento.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_orcamento)
    story.append(Spacer(1, 10))

    # Seção 3: Histórico
    story.append(Paragraph("INFORMAÇÕES DO HISTÓRICO", section_style))
    hist_text = row.get('descricao_historico_empenho', 'Sem descrição adicional cadastrada.')
    t_historico = Table([[Paragraph(hist_text, body_style)]], colWidths=[500])
    t_historico.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_historico)

    doc.build(story)
    buffer.seek(0)
    return buffer