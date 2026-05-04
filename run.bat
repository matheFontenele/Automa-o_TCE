@echo off
setlocal enabledelayedexpansion

:: 1. TENTA OBTER PRIVILÉGIOS DE ADMINISTRADOR
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando permissao de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 2. FORÇA O DIRETÓRIO PARA A PASTA DO PROJETO (Corrige o erro do System32)
cd /d "%~dp0"

:: Define o caminho onde o Python será instalado silenciosamente
set PYTHON_INSTALL_PATH=C:\Program Files\Python312\python.exe
set PYTHON_EXE=python

:: 3. VERIFICA E INSTALA O PYTHON SE NECESSÁRIO
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Python nao encontrado. Baixando o instalador...
    powershell -Command "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -OutFile 'python_installer.exe'"
    
    echo [INFO] Instalando Python silenciosamente...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    
    set PYTHON_EXE="%PYTHON_INSTALL_PATH%"
    echo [INFO] Python instalado com sucesso!
)

:: 4. CRIA AMBIENTE VIRTUAL
if not exist "venv" (
    echo [INFO] Criando ambiente virtual...
    %PYTHON_EXE% -m venv venv
)

:: 5. INSTALA DEPENDÊNCIAS DIRETO PELO EXECUTÁVEL DO VENV
echo [INFO] Instalando dependencias...
.\venv\Scripts\python.exe -m pip install --upgrade pip >nul
.\venv\Scripts\pip.exe install -q streamlit pandas requests

:: 6. INICIA O SISTEMA DIRETO PELO EXECUTÁVEL DO VENV
echo [INFO] Abrindo o sistema no navegador...
.\venv\Scripts\streamlit.exe run app.py

pause