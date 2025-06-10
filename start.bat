@ECHO OFF
TITLE Me Ensina A.I. - Inicializador

ECHO =======================================================
ECHO    INICIALIZADOR DA APLICACAO ME ENSINA A.I.
ECHO =======================================================
ECHO.

REM Verifica se o Python está disponível no sistema
python --version >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERRO: O Python nao foi encontrado.
    ECHO Por favor, instale o Python e marque a opcao "Add Python to PATH" durante a instalacao.
    ECHO.
    PAUSE
    EXIT /B
)

REM Verifica a existência do ambiente virtual "venv"
IF NOT EXIST "venv" (
    ECHO.
    ECHO -> Ambiente virtual nao encontrado. Criando agora...
    python -m venv venv
    ECHO.
    ECHO -> Ambiente virtual criado com sucesso!
    ECHO.
    
    REM Ativa o ambiente e instala as dependências
    ECHO -> Ativando o ambiente e instalando dependencias. Aguarde...
    CALL "venv\Scripts\activate.bat"
    pip install -r requirements.txt
    ECHO.
    ECHO -> Dependencias instaladas!
    ECHO.
) ELSE (
    ECHO.
    ECHO -> Ambiente virtual encontrado. Ativando...
    CALL "venv\Scripts\activate.bat"
    ECHO.
)

ECHO =======================================================
ECHO    INICIANDO APLICACAO...
ECHO =======================================================
ECHO.

python desktop_app.py

ECHO.
ECHO A aplicacao foi encerrada. Pressione qualquer tecla para fechar esta janela.
PAUSE