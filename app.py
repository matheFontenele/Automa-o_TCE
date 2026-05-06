import re
import streamlit as st
import pandas as pd
import os
import glob
import io
from main import executar_pipeline, carregar_municipios

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Automação TCE-CE", layout="wide")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'modo_tela' not in st.session_state: st.session_state.modo_tela = 'extracao'
if 'ano_base' not in st.session_state: st.session_state.ano_base = 2025
if 'mun_input' not in st.session_state: st.session_state.mun_input = "Todos"

# --- FUNÇÕES DE APOIO ---
def get_mun_code(mun_input):
    if mun_input == "Todos": return "*"
    match = re.search(r'\((\d+)\)', mun_input)
    return match.group(1) if match else "*"

def get_options_safe(df, col_name):
    """Retorna lista de opções únicas para um selectbox de forma segura."""
    if col_name in df.columns:
        return ["Todos"] + sorted(df[col_name].dropna().astype(str).unique().tolist())
    return ["Todos"]

def carregar_todos_dados(ano, mun_code):
    tipos = {
        "empenhos": "notas_empenho", 
        "pagamentos": "notas_pagamentos", 
        "liquidacoes": "liquidacoes", 
        "fiscais": "notas_fiscais"
    }
    dfs = {}
    for key, nome_arquivo in tipos.items():
        padrao = os.path.join('data', f"{nome_arquivo}_{ano}_*_{mun_code}.parquet")
        arquivos = glob.glob(padrao)
        if arquivos:
            dfs[key] = pd.concat([pd.read_parquet(f) for f in arquivos], ignore_index=True)
            # Garantir tipos de colunas chave
            if 'numero_empenho' in dfs[key].columns:
                dfs[key]['numero_empenho'] = dfs[key]['numero_empenho'].astype(str)
        else:
            dfs[key] = pd.DataFrame()
    return dfs

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configurações")
    
    col_nav1, col_nav2 = st.columns(2)
    if col_nav1.button("📊 Extração", use_container_width=True): st.session_state.modo_tela = 'extracao'
    if col_nav2.button("🔍 Consulta", use_container_width=True): st.session_state.modo_tela = 'consulta'
            
    st.divider()

    # --- CAMPOS CONDICIONAIS ---
    if st.session_state.modo_tela == 'extracao':
        st.session_state.ano_base = st.number_input("Ano Base", min_value=2000, max_value=2030, value=st.session_state.ano_base)
        
        try:
            lista_municipios = carregar_municipios()
            opcoes_mun = {f"{m['nome_municipio']} ({m['codigo_municipio']})": m for m in lista_municipios}
            opcoes_list = ["Todos"] + list(opcoes_mun.keys())
            idx = opcoes_list.index(st.session_state.mun_input) if st.session_state.mun_input in opcoes_list else 0
            st.session_state.mun_input = st.selectbox("Município", options=opcoes_list, index=idx)
        except Exception:
            st.error("Erro ao carregar municípios.")
        
        mes_input = st.selectbox("Mês de Extração", options=["Todos"] + list(range(1, 13)))
        
        if st.button("Executar Extração", type="primary", use_container_width=True):
            mun_sel = None if st.session_state.mun_input == "Todos" else opcoes_mun[st.session_state.mun_input]
            with st.spinner("Buscando dados no TCE..."):
                executar_pipeline(st.session_state.ano_base, mes_selecionado=mes_input, municipio_selecionado=mun_sel)
                st.success("Extração concluída!")

    elif st.session_state.modo_tela == 'consulta':
        st.subheader("Filtros de Consulta")
        f_data = st.text_input("Data (YYYY-MM-DD)")
        f_num = st.text_input("Número do Empenho")
        f_hist = st.text_input("Histórico")
        f_forn = st.text_input("Fornecedor")
        
        # Filtros Dinâmicos (Corrigidos com nomes de colunas reais)
        if 'dfs_consulta' in st.session_state and st.session_state.dfs_consulta is not None:
            df_ref = st.session_state.dfs_consulta.get("empenhos", pd.DataFrame())
            f_orgao = st.selectbox("Órgão", get_options_safe(df_ref, 'codigo_orgao'))
            f_elem = st.selectbox("Elemento", get_options_safe(df_ref, 'codigo_elemento_despesa'))
            f_fonte = st.selectbox("Fonte de Recursos", get_options_safe(df_ref, 'codigo_fonte'))
        else:
            f_orgao, f_elem, f_fonte = "Todos", "Todos", "Todos"

# --- ÁREA PRINCIPAL ---
st.title("🚀 Painel de Automação TCE-CE")

if st.session_state.modo_tela == 'extracao':
    st.subheader("Visualizar Dados Extraídos")
    # (Manter lógica de abas de extração aqui)
    st.info("Utilize a barra lateral para configurar e executar a extração.")

else: # MODO CONSULTA
    st.header("🔍 Consulta Detalhada por Empenho")
    mun_code = get_mun_code(st.session_state.mun_input)
    
    if 'dfs_consulta' not in st.session_state or st.session_state.dfs_consulta is None:
        if st.button("Carregar Base de Dados para Consulta"):
            with st.spinner("Consolidando dados..."):
                st.session_state.dfs_consulta = carregar_todos_dados(st.session_state.ano_base, mun_code)
                st.rerun()
    
    if 'dfs_consulta' in st.session_state and st.session_state.dfs_consulta is not None:
        dfs = st.session_state.dfs_consulta
        if "empenhos" not in dfs or dfs["empenhos"].empty:
            st.error("Nenhum dado de empenho carregado para estes critérios.")
        else:
            df = dfs["empenhos"].copy()
            
            # --- Lógica de filtragem atualizada ---
            df_filtrado = df.copy()
            
            # Filtros de Texto
            if f_num: df_filtrado = df_filtrado[df_filtrado['numero_empenho'].astype(str).str.contains(f_num, na=False)]
            if f_data: df_filtrado = df_filtrado[df_filtrado['data_emissao_empenho'].astype(str).str.contains(f_data, na=False)]
            if f_forn and 'nome_negociante' in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado['nome_negociante'].str.contains(f_forn, case=False, na=False)]
            if f_hist and 'descricao_historico_empenho' in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado['descricao_historico_empenho'].str.contains(f_hist, case=False, na=False)]
            
            # Filtros Selecionáveis (Mapeados com chaves corretas)
            if f_orgao != "Todos" and 'codigo_orgao' in df_filtrado.columns: 
                df_filtrado = df_filtrado[df_filtrado['codigo_orgao'].astype(str) == str(f_orgao)]
            
            if f_elem != "Todos" and 'codigo_elemento_despesa' in df_filtrado.columns: 
                df_filtrado = df_filtrado[df_filtrado['codigo_elemento_despesa'].astype(str) == str(f_elem)]
            
            if f_fonte != "Todos" and 'codigo_fonte' in df_filtrado.columns: 
                df_filtrado = df_filtrado[df_filtrado['codigo_fonte'].astype(str) == str(f_fonte)]

            st.write(f"### Resultados encontrados: {len(df_filtrado)}")
            
            if not df_filtrado.empty:
                empenho_sel = st.selectbox("Selecione o Empenho na lista:", df_filtrado['numero_empenho'].unique())
                dados_emp = df_filtrado[df_filtrado['numero_empenho'] == empenho_sel].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Valor Empenhado", f"R$ {float(dados_emp.get('valor_empenhado', 0)):,.2f}")
                c2.metric("Data", str(dados_emp.get('data_emissao_empenho', ''))[:10])
                c3.metric("Fornecedor", dados_emp.get('nome_negociante', 'N/A'))
                
                st.text_area("Descrição/Histórico", dados_emp.get('descricao_historico_empenho', ''), height=100)