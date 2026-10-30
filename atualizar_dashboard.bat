@echo off
echo ==========================================================
echo    MESA Intelligence - Atualizar Dashboard e Publicar Web
echo ==========================================================
echo.
echo [1/4] Extraindo dados do Power BI Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\exportar_dados_pbi.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha na extracao de dados do Power BI.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Gerando arquivo HTML e index.html atualizados...
python "%~dp0scripts\gerar_html_live.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao injetar os dados no HTML.
    pause
    exit /b %ERRORLEVEL%
)

copy /Y "%~dp0MESA_Intelligence_Live.html" "%USERPROFILE%\Documents\antigravity\kind-shannon\MESA_Intelligence_Live.html" > nul

echo.
echo [3/4] Enviando atualizacao para o GitHub Pages...
git add index.html MESA_Intelligence_Live.html > nul 2>&1
git commit -m "chore: atualizacao automatica dos dados do dashboard" > nul 2>&1
git push origin main > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    - GitHub Pages atualizado na nuvem!
) else (
    echo    - Aviso: Nao foi possivel sincronizar com o GitHub remoto no momento.
)

echo.
echo [4/4] Abrindo dashboard local no navegador...
start "" "%~dp0MESA_Intelligence_Live.html"

echo.
echo ==========================================================
echo    Dashboard atualizado com sucesso!
echo    Link Web: https://jonatasndossantos.github.io/mesa-intelligence-powerbi-gateway/
echo ==========================================================
pause
