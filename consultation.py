import streamlit as st
import pandas as pd
import glob
import os

# 1. Configuração de Estilo Adaptativo (CSS)
st.markdown("""
    <style>
    .report-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 8px solid #ff4b4b;
        color: var(--text-color);
        transition: transform 0.2s;
    }
    .report-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #ff4b4b;
    }
    .card-header { 
        color: #ff4b4b; 
        font-weight: bold; 
        font-size: 0.8rem; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .card-vendor { 
        font-size: 1.15rem; 
        font-weight: 700;
        margin: 5px 0;
    }
    .card-org {
        font-size: 0.9rem;
        opacity: 0.8;
        margin-bottom: 12px;
    }
    .card-value { 
        font-family: 'Roboto Mono', monospace;
        font-weight: bold; 
        color: #28a745; 
        font-size: 1.4rem;
    }
    .btn-fake {
        background-color: #ff4b4b;
        color: white !important;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 12px;
        text-decoration: none;
        display: inline-block;
        margin-top: 10px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Consolidando base de dados...")
def carregar_e_filtrar(arquivos):
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)

def render_consultation_page():
    st.header("🔍 Consulta Detalhada")

    # Filtros Superiores
    with st.expander("🎯 Opções de Filtro", expanded=True):
        c1, c2, c3 = st.columns(3)
        ano_sel = c1.selectbox("Ano", [2020, 2021, 2022, 2023, 2024, 2025, 2026], index=6)
        categoria_sel = c2.selectbox("Tipo de Documento", ["Notas de Empenho", "Notas Fiscais", "Notas de Pagamento"])
        filtro_geral = c3.text_input("Busca Geral", placeholder="Nome ou Histórico...")

    mapa_prefixos = {
        "Notas de Empenho": "notas_empenho",
        "Notas Fiscais": "notas_fiscais",
        "Notas de Pagamento": "notas_pagamentos"
    }

    prefixo = mapa_prefixos[categoria_sel]
    arquivos = glob.glob(f"data/{prefixo}_{ano_sel}_*.parquet")

    if arquivos:
        df = carregar_e_filtrar(arquivos)

        # Lógica de Filtro
        if filtro_geral:
            if categoria_sel == "Notas de Empenho":
                mask = (df['nome_negociante'].str.contains(filtro_geral, case=False, na=False)) | \
                       (df['descricao_historico_empenho'].str.contains(filtro_geral, case=False, na=False))
            elif categoria_sel == "Notas de Pagamento":
                mask = df['nome_responsavel_pagamento'].str.contains(filtro_geral, case=False, na=False)
            else:
                mask = (df['municipio_referencia'].str.contains(filtro_geral, case=False, na=False)) | \
                       (df['cpf_cnpj_emitente'].str.contains(filtro_geral, case=False, na=False))
            df = df[mask]

        st.subheader(f"LISTA DE {categoria_sel.upper()} - {ano_sel}")
        st.caption(f"Foram encontrados {len(df):,} registros.")

        limite = 100
        for _, row in df.head(limite).iterrows():
            # Mapeamento Dinâmico
            if categoria_sel == "Notas de Empenho":
                id_doc, entidade, detalhe, valor, label = f"EMPENHO: {row['numero_empenho']}", row['nome_negociante'], row['descricao_historico_empenho'], row['valor_empenhado'], "Empenhado (R$)"
            elif categoria_sel == "Notas de Pagamento":
                id_doc, entidade, detalhe, valor, label = f"PAGAMENTO: {row['numero_nota_pagamento']}", row['nome_responsavel_pagamento'], f"Empenho Ref: {row['numero_empenho']}", row['valor_nota_pagamento'], "Pago (R$)"
            else:
                id_doc, entidade, detalhe, valor, label = f"NF: {row['numero_nota_fiscal']}", f"Emitente: {row['cpf_cnpj_emitente']}", f"Empenho: {row['numero_empenho']}", row['valor_bruto'], "Bruto (R$)"

            # HTML do Card com Alinhamento Corrigido
            st.markdown(f"""
                <div class="report-card">
                    <div style="display: flex; justify-content: space-between; align-items: stretch;">
                        <div style="flex: 3; border-right: 1px solid rgba(128,128,128,0.2); padding-right: 20px;">
                            <div class="card-header">{id_doc}</div>
                            <div class="card-vendor">{entidade}</div>
                            <div class="card-org">📍 {row['municipio_referencia']}</div>
                            <div style="font-size: 0.85rem; line-height: 1.5; opacity: 0.9;">
                                {str(detalhe)[:250] + '...' if len(str(detalhe)) > 250 else detalhe}
                            </div>
                        </div>
                        <div style="flex: 1; text-align: right; padding-left: 20px; display: flex; flex-direction: column; justify-content: center;">
                            <div style="font-size: 0.7rem; opacity: 0.6; text-transform: uppercase;">{label}</div>
                            <div class="card-value">R$ {valor:,.2f}</div>
                            <div><a href="#" class="btn-fake">🔍 DETALHES</a></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        if len(df) > limite:
            st.warning(f"Exibindo os primeiros {limite} resultados por performance.")

        st.divider()
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(f"📥 Exportar Resultado Completo ({len(df):,} linhas)", csv, f"TCE_{prefixo}_{ano_sel}.csv", "text/csv", use_container_width=True)
    else:
        st.warning(f"Nenhum arquivo de {categoria_sel} encontrado para o ano {ano_sel}.")