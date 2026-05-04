@echo off
title Painel de Automacao TCE-CE (Portatil)

:: Define o caminho do Python local (agora apontando para a subpasta 'python')
set PYTHON_EXE=.\Python\python\python.exe

:: Verifica se o Python local existe
if not exist "%PYTHON_EXE%" (
    echo [ERRO] Python nao encontrado no caminho: %PYTHON_EXE%
    echo Verifique se a pasta 'python' existe dentro da sua pasta 'Python'.
    pause
    exit /b
)

:: Verifica se a pasta venv existe, se nao, cria usando o Python local
if not exist "venv" (
    echo [INFO] Criando ambiente virtual com Python Portatil...
    "%PYTHON_EXE%" -m venv venv
    
    echo [INFO] Instalando bibliotecas...
    :: Usamos o executavel da pasta venv recem criada
    .\venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: Ativa e roda
echo [INFO] Iniciando o sistema...
call .\venv\Scripts\activate.bat
streamlit run app.py

pause