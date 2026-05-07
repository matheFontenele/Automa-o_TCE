import streamlit as st
import pandas as pd
import glob
import os

# 1. Configuração de Estilo Adaptativo (CSS) - FIXADO
st.markdown("""
    <style>
    /* ESTILO DOS BOTÕES */
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        height: 3.5em !important;
        background-color: #1E1E24 !important; /* Grafite Escuro */
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        font-weight: 600 !important;
    }

    .stButton > button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }

    /* ESTILO DOS CARDS (Correção de espaçamento e sombra) */
    .report-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.3); 
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 25px; 
        border-left: 10px solid #ff4b4b;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2); 
    }

    .card-header { color: #ff4b4b; font-weight: bold; font-size: 0.75rem; text-transform: uppercase; }
    .card-vendor { font-size: 1.2rem; font-weight: 800; margin: 8px 0; }
    .card-org { font-size: 0.95rem; opacity: 0.85; margin-bottom: 15px; }
    .card-value { font-family: 'Roboto Mono', monospace; font-weight: 700; color: #28a745; font-size: 1.5rem; }

    .btn-fake {
        background-color: #1E1E24;
        color: white !important;
        padding: 8px 18px;
        border-radius: 6px;
        text-decoration: none;
        display: inline-block;
        font-weight: bold;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Consolidando base de dados...")
def carregar_e_filtrar(arquivos):
    if not arquivos:
        return pd.DataFrame()
    # Tratamento para arquivos vazios ou erro de leitura
    dfs = []
    for f in arquivos:
        try:
            dfs.append(pd.read_parquet(f))
        except:
            continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def render_consultation_page():
    st.header("🔍 Consulta Detalhada")

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

        if filtro_geral and not df.empty:
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
            if categoria_sel == "Notas de Empenho":
                id_doc, entidade, detalhe, valor, label = f"EMPENHO: {row['numero_empenho']}", row['nome_negociante'], row['descricao_historico_empenho'], row['valor_empenhado'], "Empenhado (R$)"
            elif categoria_sel == "Notas de Pagamento":
                id_doc, entidade, detalhe, valor, label = f"PAGAMENTO: {row['numero_nota_pagamento']}", row['nome_responsavel_pagamento'], f"Empenho Ref: {row['numero_empenho']}", row['valor_nota_pagamento'], "Pago (R$)"
            else:
                id_doc, entidade, detalhe, valor, label = f"NF: {row['numero_nota_fiscal']}", f"Emitente: {row['cpf_cnpj_emitente']}", f"Empenho: {row['numero_empenho']}", row['valor_bruto'], "Bruto (R$)"

            # HTML do CARD de Itens
            st.markdown("""
                <style>
                .report-card {
                    background-color: #FFFFFF; /* Fundo branco para contraste total no tema escuro/claro */
                    border: 1px solid rgba(0, 0, 0, 0.1); 
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 20px; 
                    border-left: 8px solid #ff4b4b;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                    color: #1E1E24 !important; /* Texto sempre escuro para legibilidade */
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }

                .report-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 12px 20px rgba(0, 0, 0, 0.15);
                    border-color: #ff4b4b;
                }

                .card-header { 
                    color: #666; 
                    font-weight: 700; 
                    font-size: 0.7rem; 
                    text-transform: uppercase; 
                    letter-spacing: 1px;
                }
                
                .card-vendor { 
                    font-size: 1.15rem; 
                    font-weight: 800; 
                    color: #1E1E24;
                    margin: 5px 0;
                }

                .card-org { 
                    font-size: 0.85rem; 
                    color: #ff4b4b; 
                    font-weight: 600;
                    margin-bottom: 12px;
                }

                .card-value { 
                    font-family: 'Roboto Mono', monospace; 
                    font-weight: 800; 
                    color: #15803d; /* Verde escuro mais legível */
                    font-size: 1.6rem; 
                }

                .btn-fake {
                    background-color: #1E1E24;
                    color: white !important;
                    padding: 10px 20px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 12px;
                    font-weight: bold;
                    transition: 0.3s;
                }

                .btn-fake:hover {
                    background-color: #ff4b4b;
                    box-shadow: 0 4px 8px rgba(255, 75, 75, 0.3);
                }
                </style>
            """, unsafe_allow_html=True)

        if len(df) > limite:
            st.warning(f"Exibindo os primeiros {limite} resultados por performance.")

        st.divider()
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(f"📥 Exportar Resultado Completo ({len(df):,} linhas)", csv, f"TCE_{prefixo}_{ano_sel}.csv", "text/csv", use_container_width=True)
    else:
        st.warning(f"Nenhum arquivo encontrado para {categoria_sel} em {ano_sel}.")