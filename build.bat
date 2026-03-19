@echo off
setlocal enabledelayedexpansion

echo   DocPopular Editor - Build Completo (PyInstaller + Instalador)
echo   (C) 2026 DocPopular Team
echo.

:: 1. Limpeza
taskkill /F /IM DocPopularEditor.exe /T >nul 2>&1
echo   [1/6] Limpando pastas antigas...
if exist build rd /s /q build
if exist dist rd /s /q dist

:: 2. Versão
echo   [2/6] Verificando versao...
for /f %%I in ('python -c "from version import APP_VERSION; print(APP_VERSION)"') do set APP_VERSION=%%I
echo     Versao detectada: v%APP_VERSION%

:: 3. Gerar .iss a partir da versao
echo   [3/6] Gerando script Inno Setup...
python _gerar_iss.py

:: 4. PyInstaller
echo   [4/6] Executando PyInstaller...
pyinstaller DocPopularEditor.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo.
    echo   [!] ERRO: Falha na compilacao com PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo     OK - dist\DocPopularEditor

:: 5. Inno Setup (Opcional, se o ISCC estiver no PATH)
echo   [5/6] Gerando Instalador .exe...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    "%ISCC%" DocPopularEditor.iss
    if %ERRORLEVEL% neq 0 (
        echo   [!] ERRO: Falha ao gerar o instalador.
    ) else (
        echo     OK - Instalador gerado em installer\
    )
) else (
    echo     [!] AVISO: ISCC.exe nao encontrado.
    echo     Depois execute novamente ou compile manualmente: DocPopularEditor.iss
)

:: 6. Gerar ZIP para auto-update
echo   [6/6] Gerando ZIP para Auto-Update...
set ZIP_BASE_NAME=DocPopularEditor
if not exist installer mkdir installer
python -c "import shutil; shutil.make_archive('installer/%ZIP_BASE_NAME%', 'zip', 'dist', 'DocPopularEditor')"

echo.
echo ==========================================================
echo   BUILD CONCLUIDO COM SUCESSO!
echo ==========================================================
echo   Executavel: dist\DocPopularEditor\DocPopularEditor.exe
echo   Instalador:  installer\DocPopularEditor_Setup_v%APP_VERSION%.exe
echo   Auto-update: installer\DocPopularEditor.zip
echo.
echo   Lembrete para Release:
echo   1. Atualize version.json no repositório.
echo   2. Carregue o .zip no GitHub Releases como 'DocPopularEditor.zip'
echo ==========================================================
pause
