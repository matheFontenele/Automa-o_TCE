import os
import sys
import requests
import pandas as pd
import concurrent.futures
import json
from tqdm import tqdm

# --- CONFIGURAÇÕES GERAIS ---
def carregar_municipios():
    with open('municipios.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['elements']

def processar_lote(task):
    """Executa o download e salvamento de um único lote."""
    caminho_arquivo = task['caminho_arquivo']
    
    # Checkpoint: se o arquivo já existe, pula
    if os.path.exists(caminho_arquivo):
        return None

    try:
        response = requests.get(task['url'], headers={"Accept": "application/json"}, params=task['params'], timeout=30)
        if response.status_code == 200:
            dados = response.json().get("elements", [])
            if dados:
                # Adiciona metadado de município se necessário
                for item in dados:
                    item['municipio_referencia'] = task['municipio_nome']
                
                df = pd.DataFrame(dados)
                df.to_parquet(caminho_arquivo, engine='pyarrow', compression='snappy')
                return True
        return False
    except Exception:
        return False

def gerar_tarefas(ano, mes_selecionado, municipio_selecionado):
    """Gera a lista de tarefas baseada nos filtros aplicados."""
    municipios = carregar_municipios()
    
    # Filtra municípios se solicitado
    if municipio_selecionado:
        municipios = [m for m in municipios if m['codigo_municipio'] == municipio_selecionado['codigo_municipio']]

    exercicio = int(f"{ano}00")
    lista_de_tarefas = []

    if mes_selecionado == "Todos" or mes_selecionado is None or mes_selecionado == "":
        meses = range(1, 13)
    else:
        # Garante que seja um inteiro (caso o Streamlit passe string)
        meses = [int(mes_selecionado)]
    # -------------------------------

    # Configuração dos endpoints
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
    
    # Execução Paralela
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(processar_lote, tarefas), total=len(tarefas), desc=f"Baixando {ano}"))


# Função principal para execução direta
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        anos = [2025]
    elif len(args) == 1:
        anos = [int(args[0])]
    else:
        anos = range(min(int(args[0]), int(args[1])), max(int(args[0]), int(args[1])) + 1)

    print(f"Iniciando extração para: {list(anos)}")

    for ano in anos:
        executar_pipeline(ano)
        print(f"[{ano}] Processamento concluído!")