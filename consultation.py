import streamlit as st
import pandas as pd
import glob
import os

# 1. Configuração de Estilo (CSS)
st.markdown("""
    <style>
    .report-card {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 6px solid #1c3d6e;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .card-header { 
        color: #1c3d6e; 
        font-weight: bold; 
        font-size: 13px; 
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .card-vendor { 
        color: #333; 
        font-weight: 700;
        font-size: 14px; 
        margin-bottom: 2px;
    }
    .card-body { 
        color: #666;
        font-size: 12px; 
        line-height: 1.4;
    }
    .card-value-label {
        font-size: 10px;
        color: #888;
        text-align: right;
        text-transform: uppercase;
    }
    .card-value { 
        font-weight: bold; 
        color: #28a745; 
        font-size: 16px;
        text-align: right; 
    }
    .view-btn {
        background-color: #1c3d6e;
        color: white;
        border: none;
        padding: 4px 8px;
        border-radius: 3px;
        font-size: 11px;
        float: right;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Cache para performance
@st.cache_data(show_spinner="Consolidando base de dados...")
def carregar_e_filtrar(arquivos, categoria):
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)

def render_consultation_page():
    st.header("🔍 Consulta Detalhada")

    # 3. Filtros Superiores
    with st.expander("🎯 Opções de Filtro", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            anos_disponiveis = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
            ano_sel = st.selectbox("Ano", options=anos_disponiveis, index=6) # Padrão 2026
        with col2:
            categoria_sel = st.selectbox("Tipo de Documento", 
                                         options=["Notas de Empenho", "Notas Fiscais", "Notas de Pagamento"])
        with col3:
            filtro_geral = st.text_input("Busca Geral", placeholder="Nome, CNPJ ou Histórico...")

    # Mapeamento para os Parquets baseados nos seus logs de colunas
    mapa_prefixos = {
        "Notas de Empenho": "notas_empenho",
        "Notas Fiscais": "notas_fiscais",
        "Notas de Pagamento": "notas_pagamentos"
    }

    prefixo = mapa_prefixos[categoria_sel]
    caminho_busca = f"data/{prefixo}_{ano_sel}_*.parquet"
    arquivos = glob.glob(caminho_busca)

    if arquivos:
        df = carregar_e_filtrar(arquivos, categoria_sel)

        # 4. Aplicação de Filtros (Usando os nomes de colunas confirmados pelo seu log)
        if filtro_geral:
            if categoria_sel == "Notas de Empenho":
                # Colunas: nome_negociante, descricao_historico_empenho
                mask = (df['nome_negociante'].str.contains(filtro_geral, case=False, na=False)) | \
                       (df['descricao_historico_empenho'].str.contains(filtro_geral, case=False, na=False))
            elif categoria_sel == "Notas de Pagamento":
                # Colunas: nome_responsavel_pagamento
                mask = df['nome_responsavel_pagamento'].str.contains(filtro_geral, case=False, na=False)
            else:
                # Notas Fiscais: municipio_referencia ou cpf_cnpj_emitente
                mask = (df['municipio_referencia'].str.contains(filtro_geral, case=False, na=False)) | \
                       (df['cpf_cnpj_emitente'].str.contains(filtro_geral, case=False, na=False))
            df = df[mask]

        st.subheader(f"LISTA DE {categoria_sel.upper()} - {ano_sel}")
        st.caption(f"Foram encontrados {len(df):,} registros.")

        # 5. Renderização em Cards (Evita o MessageSizeError de 500MB)
        limite_exibicao = 100
        
        for index, row in df.head(limite_exibicao).iterrows():
            # Mapeamento dinâmico de campos por tipo de arquivo
            if categoria_sel == "Notas de Empenho":
                id_doc = f"EMPENHO: {row['numero_empenho']} - DATA: {str(row['data_emissao_empenho'])[:10]}"
                entidade = row['nome_negociante']
                detalhe = row['descricao_historico_empenho']
                valor_principal = row['valor_empenhado']
                label_v = "Empenhado (R$)"
            elif categoria_sel == "Notas de Pagamento":
                id_doc = f"PAGAMENTO: {row['numero_nota_pagamento']} - EMPENHO REF: {row['numero_empenho']}"
                entidade = row['nome_responsavel_pagamento']
                detalhe = f"Doc Caixa: {row['numero_documento_caixa']}"
                valor_principal = row['valor_nota_pagamento']
                label_v = "Pago (R$)"
            else: # Notas Fiscais
                id_doc = f"NF: {row['numero_nota_fiscal']} - SÉRIE: {row['numero_serie']}"
                entidade = f"Emitente CNPJ: {row['cpf_cnpj_emitente']}"
                detalhe = f"Município: {row['municipio_referencia']} | Empenho: {row['numero_empenho']}"
                valor_principal = row['valor_bruto']
                label_v = "Bruto (R$)"

            # HTML do Card Estilizado
            st.markdown(f"""
                <div class="report-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 3;">
                            <div class="card-header">{id_doc}</div>
                            <div class="card-vendor">{entidade}</div>
                            <div class="card-body">
                                <b>Órgão/Unidade:</b> {row['codigo_orgao']} - {row['municipio_referencia']}<br>
                                <i>{str(detalhe)[:250] + '...' if len(str(detalhe)) > 250 else detalhe}</i>
                            </div>
                        </div>
                        <div style="flex: 1; text-align: right;">
                            <div class="card-value-label">{label_v}</div>
                            <div class="card-value">{valor_principal:,.2f}</div>
                            <div style="margin-top: 15px;">
                                <span style="font-size: 18px; color: #1c3d6e; cursor: pointer;">👁️</span>
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        if len(df) > limite_exibicao:
            st.warning(f"Exibindo apenas os primeiros {limite_exibicao} resultados por performance. Use o botão abaixo para baixar o total.")

        # 6. Botão de Exportação (Sempre gera o CSV do DF filtrado completo)
        st.divider()
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label=f"📥 Exportar Resultado Completo ({len(df):,} linhas)",
            data=csv,
            file_name=f"TCE_{prefixo}_{ano_sel}.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.warning(f"Nenhum arquivo de {categoria_sel} encontrado para o ano {ano_sel}.")
        st.info("Verifique se a extração foi concluída para este período.")