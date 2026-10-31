@echo off
echo ==========================================================
echo    MESA Intelligence - Atualizar via Nuvem (Power BI API)
echo ==========================================================
echo.
echo [1/3] Extraindo dados diretamente do Power BI Service (Nuvem)...
python "%~dp0scripts\pbi_cloud_api.py" --extract
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha na extracao via API da Nuvem.
    echo Certifique-se de ter configurado o scripts\cloud_config.json
    pause
    exit /b %ERRORLEVEL%
)

copy /Y "%~dp0MESA_Intelligence_Live.html" "%USERPROFILE%\Documents\antigravity\kind-shannon\MESA_Intelligence_Live.html" > nul

echo.
echo [2/3] Enviando atualizacao para o GitHub Pages...
git add index.html MESA_Intelligence_Live.html lojas > nul 2>&1
git commit -m "chore: atualizacao de dados via Power BI Cloud API" > nul 2>&1
git push origin HEAD:main > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    - GitHub Pages atualizado na nuvem!
) else (
    echo    - Aviso: Nao foi possivel sincronizar com o GitHub remoto.
)

echo.
echo [3/3] Abrindo dashboard no navegador...
start "" "%~dp0MESA_Intelligence_Live.html"

echo.
echo ==========================================================
echo    Dashboard atualizado com sucesso via Nuvem!
echo    Link Web: https://jonatasndossantos.github.io/mesa-intelligence-powerbi-gateway/
echo ==========================================================
pause
