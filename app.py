import streamlit as st
import extraction
import consultation

st.set_page_config(page_title="Automação TCE-CE", layout="wide")

# Estilização para o Menu Superior
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #f0f2f6;
    }
    /* Estilo para quando o botão estiver selecionado (simulado via cor de destaque) */
    .highlight {
        border: 2px solid #ff4b4b !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializa o estado de navegação
if 'modo_tela' not in st.session_state:
    st.session_state.modo_tela = 'Extração'

# Layout de Menu Superior
st.title("🚀 Painel de Automação TCE-CE")
col_nav1, col_nav2, col_spacer = st.columns([1, 1, 4])

with col_nav1:
    if st.button("📊 Extração", key="btn_ext", 
                 type="primary" if st.session_state.modo_tela == 'Extração' else "secondary"):
        st.session_state.modo_tela = 'Extração'
        st.rerun()

with col_nav2:
    if st.button("🔍 Consulta", key="btn_con", 
                 type="primary" if st.session_state.modo_tela == 'Consulta' else "secondary"):
        st.session_state.modo_tela = 'Consulta'
        st.rerun()

st.divider()

# Exibição do conteúdo
if st.session_state.modo_tela == 'Extração':
    extraction.render_extraction_page()
elif st.session_state.modo_tela == 'Consulta':
    consultation.render_consultation_page()