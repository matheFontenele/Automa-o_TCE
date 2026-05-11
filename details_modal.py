# details_modal.py
import streamlit as st
import pandas as pd
import glob
import re

# IMPORTANDO O GERADOR DE PDF ISOLADO
from gerador_pdf import gerar_pdf_empenho

# ==============================================================================
# FUNÇÕES AUXILIARES DO MODAL
# ==============================================================================
def formatar_moeda_modal(valor):
    try:
        if pd.isna(valor) or valor is None:
            return "0,00"
        val_float = float(valor)
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00"

def formatar_data_modal(data_raw):
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

def obter_caminho_arquivos_modal(prefixo, ano, codigo_mun):
    if codigo_mun == "Todos":
        return sorted(glob.glob(f"data/{prefixo}_{ano}_*.parquet"))
    return sorted(glob.glob(f"data/{prefixo}_{ano}_*_{codigo_mun}.parquet"))

def carregar_e_filtrar_modal(arquivos):
    """Carrega os arquivos dinamicamente em memória apenas para o escopo do modal."""
    if not arquivos:
        return pd.DataFrame()
    dfs = []
    for f in arquivos:
        try:
            dfs.append(pd.read_parquet(f))
        except:
            continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ==============================================================================
# DIALOG (MODAL) EXPORTADO
# ==============================================================================
@st.dialog("📋 Detalhes do Empenho", width="large")
def exibir_modal_detalhes(row, categoria, ano, codigo_mun):
    
    # Cabeçalho Principal do Modal
    st.write(f"### Empenho Nº {row.get('numero_empenho', 'N/A')}")
    st.caption(f"📍 {row.get('municipio_referencia', 'Não Informado')} — Exercício Orçamentário: {str(row.get('exercicio_orcamento', ''))[:4]}")
    st.divider()

    # ==============================================================================
    # SEÇÃO 1: INFORMAÇÕES DO EMPENHO
    # ==============================================================================
    st.markdown("#### 📄 INFORMAÇÕES DO EMPENHO")
    
    col_emp1, col_emp2 = st.columns(2)
    with col_emp1:
        st.markdown(f"**Número do empenho:** `{row.get('numero_empenho', 'N/A')}`")
        
        # Data de emissão tratando empenho/fiscais/pagamentos
        data_emissao = row.get('data_emissao_empenho', row.get('data_emissao', row.get('data_nota_pagamento')))
        st.markdown(f"**Data:** {formatar_data_modal(data_emissao)}")
        
        # Valor do empenho
        valor_emp = row.get('valor_empenhado', row.get('valor_bruto', row.get('valor_nota_pagamento', 0.0)))
        st.markdown(f"**Valor:** `R$ {formatar_moeda_modal(valor_emp)}`")

    with col_emp2:
        # Fornecedor / Credor
        fornecedor = row.get('nome_negociante', row.get('nome_responsavel_pagamento', 'Não Informado'))
        st.markdown(f"**Fornecedor:** {fornecedor}")
        
        # CPF/CNPJ Documento do Negociante
        cnpj_fornecedor = row.get('numero_documento_negociante', row.get('cpf_cnpj_emitente', row.get('cpf_responsavel_pagamento', 'Ocultado')))
        st.markdown(f"**CNPJ/CPF Fornecedor:** `{cnpj_fornecedor}`")
        
        # Modalidade da Licitação
        modalidade_licitacao = row.get('tipo_processo_licitatorio', 'N/A')
        st.markdown(f"**Modalidade de Licitação:** `{modalidade_licitacao}`")

    st.divider()

    # ==============================================================================
    # SEÇÃO 2: INFORMAÇÕES DE ORÇAMENTO
    # ==============================================================================
    st.markdown("#### 🏛️ INFORMAÇÕES DE ORÇAMENTO")
    
    col_orc1, col_orc2 = st.columns(2)
    with col_orc1:
        # Unidade Gestora baseada no município e na unidade orçamentária
        unidade_gestora = f"{row.get('municipio_referencia', 'N/A')} - U.O. {row.get('codigo_unidade_orcamentaria', 'N/A')}"
        st.markdown(f"**Unidade Gestora:** {unidade_gestora}")
        
        st.markdown(f"**Órgão:** `{row.get('codigo_orgao', 'N/A')}`")
        st.markdown(f"**Unidade Orçamentária:** `{row.get('codigo_unidade_orcamentaria', 'N/A')}`")
        
        # Proj Atividade unindo código e número
        proj_ativ = f"{row.get('codigo_projeto_atividade', '')}.{row.get('numero_projeto_atividade', '')}".strip('.')
        st.markdown(f"**Proj. Atividade:** `{proj_ativ if proj_ativ else 'Não Informado'}`")

    with col_orc2:
        # Natureza da despesa (elemento)
        st.markdown(f"**Natureza (Elemento):** `{row.get('codigo_elemento_despesa', 'N/A')}`")
        st.markdown(f"**Função:** `{row.get('codigo_funcao', 'N/A')}`")
        st.markdown(f"**Sub-função:** `{row.get('codigo_subfuncao', 'N/A')}`")
        st.markdown(f"**Fonte de Recurso:** `{row.get('codigo_fonte', 'N/A')}`")

    st.divider()

    # ==============================================================================
    # SEÇÃO 3: HISTÓRICO / HISTÓRICO
    # ==============================================================================
    st.markdown("#### 📜 Histórico / Descrição")
    st.info(row.get('descricao_historico_empenho', 'Sem descrição adicional cadastrada.'))

    # ==============================================================================
    # SEÇÃO 4: ITENS DA NOTA FISCAL (Carregamento Dinâmico)
    # ==============================================================================
    st.markdown("#### 📦 Itens da Nota Fiscal")
    
    arquivos_itens = obter_caminho_arquivos_modal("itens_notas_fiscais", ano, codigo_mun)
    
    if arquivos_itens:
        df_itens = carregar_e_filtrar_modal(arquivos_itens)
        if not df_itens.empty:
            cod_mun_item = row.get('codigo_municipio', '')
            
            num_empenho_busca = str(row.get('numero_empenho', '')).strip()
            cod_mun_busca = str(cod_mun_item).strip()
            
            itens_filtrados = df_itens[
                (df_itens['numero_nota_empenho'].astype(str).str.strip() == num_empenho_busca) & 
                (df_itens['codigo_municipio'].astype(str).str.strip() == cod_mun_busca)
            ]
            
            if not itens_filtrados.empty:
                colunas_exibicao = {
                    'descricao_item': 'Descrição do Item',
                    'unidade_compra': 'Unidade',
                    'numero_quantidade_comprada': 'Qtd',
                    'valor_unitario_item': 'Valor Unitário',
                    'valor_total_item': 'Valor Total'
                }
                colunas_existentes = [col for col in colunas_exibicao.keys() if col in itens_filtrados.columns]
                
                if colunas_existentes:
                    df_exibir = itens_filtrados[colunas_existentes].rename(columns={k: v for k, v in colunas_exibicao.items() if k in colunas_existentes})
                    if 'Valor Unitário' in df_exibir.columns:
                        df_exibir['Valor Unitário'] = df_exibir['Valor Unitário'].apply(lambda x: f"R$ {formatar_moeda_modal(x)}")
                    if 'Valor Total' in df_exibir.columns:
                        df_exibir['Valor Total'] = df_exibir['Valor Total'].apply(lambda x: f"R$ {formatar_moeda_modal(x)}")
                    
                    st.dataframe(df_exibir, use_container_width=True, hide_index=True)
                else:
                    st.warning("As colunas de detalhamento de itens não foram localizadas nesta base.")
            else:
                st.warning("Nenhum item quantitativo discriminado foi anexado a este empenho.")
        else:
            st.warning("Base de dados de itens da NF não possui registros.")
    else:
        st.caption("Base de itens físicos das Notas Fiscais não localizada para este período.")

    st.divider()
    
    # Botão de download/geração do PDF
    try:
        pdf_data = gerar_pdf_empenho(row)
        st.download_button(
            label="🖨️ Imprimir Detalhes do Empenho (PDF)",
            data=pdf_data,
            file_name=f"Empenho_{row.get('numero_empenho', 'N/A')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Erro ao gerar o relatório em PDF: {e}")