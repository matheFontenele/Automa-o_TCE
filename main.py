import os
import sys
import requests
import pandas as pd
import concurrent.futures
import json
from tqdm import tqdm

# --- CONFIGURAÇÕES GERAIS ---
def carregar_municipios():
    try:
        with open('municipios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['elements']
    except FileNotFoundError:
        # Fallback de segurança caso o arquivo não seja achado localmente
        return []

def processar_lote(task):
    """
    Executa o download de um único lote e retorna o status e a mensagem de log.
    Não interage diretamente com o Streamlit (Thread-safe).
    """
    caminho_arquivo = task['caminho_arquivo']
    nome_arquivo = os.path.basename(caminho_arquivo)
    
    # Checkpoint: se o arquivo já existe, pula
    if os.path.exists(caminho_arquivo):
        return "IGNORADO", f"⏭️ Ignorado: {nome_arquivo} já existe."

    try:
        
        response = requests.get(task['url'], headers={"Accept": "application/json"}, params=task['params'], timeout=30)
        
        if response.status_code == 200:
            dados = response.json().get("elements", [])
            if dados:
                df = pd.DataFrame(dados)
                
                # ==============================================================
                # 🛡️ FILTRO DEFENSIVO CONTRA O BUG DE FALLBACK DO TCE-CE
                # ==============================================================
                ano_esperado = str(task['params']['exercicio_orcamento'])[:4]
                
                if 'exercicio_orcamento' in df.columns:
                    df['exercicio_orcamento_str'] = df['exercicio_orcamento'].astype(str)
                    # Mantém APENAS as linhas que começam com o ano correto (ex: '202500')
                    df = df[df['exercicio_orcamento_str'].str.startswith(ano_esperado)]
                    df = df.drop(columns=['exercicio_orcamento_str'])
                
                # Se o TCE só mandou lixo de outro ano, o DataFrame ficou vazio após o filtro
                if df.empty:
                    return "VAZIO", f"⚠️ Vazio: {nome_arquivo} - API retornou dados de outro ano (Descartado)."
                # ==============================================================

                # Adiciona o município de referência nas linhas válidas que restaram
                df['municipio_referencia'] = task['municipio_nome']
                
                # Salvando em Parquet o resultado limpo
                df.to_parquet(caminho_arquivo, engine='pyarrow', compression='snappy')
                return "BAIXADO", f"✅ Criado com sucesso: {nome_arquivo}"

        return "VAZIO", f"⚠️ Vazio: {nome_arquivo} - Sem registros no TCE."

    except Exception as e:
        return "ERRO_CONEXAO", f"❌ Erro em {nome_arquivo}: {str(e)}"

def gerar_tarefas(ano, mes_selecionado, municipio_selecionado):
    """Gera a lista de tarefas baseada nos filtros aplicados."""
    municipios = carregar_municipios()
    
    if municipio_selecionado:
        municipios = [m for m in municipios if m['codigo_municipio'] == municipio_selecionado['codigo_municipio']]

    exercicio = int(f"{ano}00")
    lista_de_tarefas = []

    if mes_selecionado == "Todos" or mes_selecionado is None or mes_selecionado == "":
        meses = range(1, 13)
    else:
        meses = [int(mes_selecionado)]

    endpoints_mensais = [
        ("notas_empenho", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_empenhos"),
        ("notas_fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_fiscais"),
        ("notas_pagamentos", "https://api-dados-abertos.tce.ce.gov.br/sim/notas_pagamentos"),
        ("pagamento_e_liquidacoes", "https://api-dados-abertos.tce.ce.gov.br/sim/pagamentos_liquidacoes"),
        ("liquidacoes", "https://api-dados-abertos.tce.ce.gov.br/sim/liquidacoes")
    ]
    
    endpoints_anuais = [
        ("itens_notas_fiscais", "https://api-dados-abertos.tce.ce.gov.br/sim/itens_notas_fiscais")
    ]

    # 1. Tarefas Mensais
    for mes in meses:
        data_ref = int(f"{ano}{str(mes).zfill(2)}")
        for nome, url in endpoints_mensais:
            for m in municipios:
                caminho = os.path.join('data', f"{nome}_{ano}_{mes:02d}_{m['codigo_municipio']}.parquet")
                lista_de_tarefas.append({
                    'dataset_nome': nome, 'url': url, 'municipio_nome': m['nome_municipio'],
                    'params': {"exercicio_orcamento": exercicio, "data_referencia_doc": data_ref, "$format": "json", "codigo_municipio": m['codigo_municipio']},
                    'caminho_arquivo': caminho
                })

    # 2. Tarefas Anuais
    for nome, url in endpoints_anuais:
        for m in municipios:
            caminho = os.path.join('data', f"{nome}_{ano}_{m['codigo_municipio']}.parquet")
            lista_de_tarefas.append({
                'dataset_nome': nome, 'url': url, 'municipio_nome': m['nome_municipio'],
                'params': {"exercicio_orcamento": exercicio, "$format": "json", "codigo_municipio": m['codigo_municipio']},
                'caminho_arquivo': caminho
            })
            
    return lista_de_tarefas

def executar_pipeline(ano, mes_selecionado=None, municipio_selecionado=None, log_func=print):
    os.makedirs('data', exist_ok=True)

    log_func(f"[{ano}] Iniciando extração...")
    tarefas = gerar_tarefas(ano, mes_selecionado, municipio_selecionado)
    
    if not tarefas:
        log_func(f"[{ano}] Nenhuma tarefa encontrada para os filtros atuais.")
        return

    log_func(f"[{ano}] Total de tarefas: {len(tarefas)}")

    baixados = 0
    ignorados = 0
    erros = 0
    
    # Execução Paralela Monitorada (Thread-Safe para Streamlit)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Envia as tarefas para execução
        futuros = {executor.submit(processar_lote, tarefa): tarefa for tarefa in tarefas}
        
        # Conforme cada thread conclui, pegamos o log e descarregamos na thread principal
        for futuro in tqdm(concurrent.futures.as_completed(futuros), total=len(tarefas), desc=f"Baixando {ano}"):
            try:
                status, msg_log = futuro.result()
                log_func(msg_log)  # Roda com segurança na thread mãe do Streamlit
                
                if status == "BAIXADO":
                    baixados += 1
                elif status == "IGNORADO":
                    ignorados += 1
                else:
                    erros += 1
            except Exception as e:
                log_func(f"❌ Erro crítico no processamento de uma thread: {e}")
                erros += 1

        log_func(f"[{ano}] Resumo: {baixados} novos, {ignorados} já existiam, {erros} falhas/vazios.")

# Função principal para execução direta via terminal
if __name__ == "__main__":
    ano_inicio = 2025
    ano_fim = 2025

    if len(sys.argv) == 2:
        ano_inicio = int(sys.argv[1])
        ano_fim = ano_inicio
    elif len(sys.argv) >= 3:
        ano_inicio = min(int(sys.argv[1]), int(sys.argv[2]))
        ano_fim = max(int(sys.argv[1]), int(sys.argv[2]))

    print(f"Iniciando extração paralela para o período de {ano_inicio} a {ano_fim}...")

    for ano_atual in range(ano_inicio, ano_fim + 1):
        print(f"\n[{ano_atual}] - Iniciando processamento do ano...")
        executar_pipeline(ano_atual)
        print(f"[{ano_atual}] - Processamento concluído!")

    print("\nProcesso total finalizado com sucesso!")