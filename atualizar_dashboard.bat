@echo off
echo ==========================================================
echo    MESA Intelligence - Atualizar Dashboard
echo ==========================================================
echo.
echo [1/3] Extraindo dados do Power BI Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\exportar_dados_pbi.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha na extracao de dados do Power BI.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Gerando arquivo HTML atualizado...
python "%~dp0scripts\gerar_html_live.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao injetar os dados no HTML.
    pause
    exit /b %ERRORLEVEL%
)

copy /Y "%~dp0MESA_Intelligence_Live.html" "%USERPROFILE%\Documents\antigravity\kind-shannon\MESA_Intelligence_Live.html" > nul

echo.
echo [3/3] Abrindo dashboard no navegador...
start "" "%~dp0MESA_Intelligence_Live.html"

echo.
echo ==========================================================
echo    Dashboard atualizado com sucesso!
echo ==========================================================
pause
