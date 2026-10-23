@echo off
cd /d "%~dp0"
title WhatsApp Backup ^& Visor - Panel de Control

python -c "import cryptography" >nul 2>&1
if %errorlevel% neq 0 (
    echo ========================================================
    echo   Configurando dependencias necesarias de Python...
    echo ========================================================
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Error instalando dependencias. Verifica tu conexion y version de Python.
        pause
        exit /b %errorlevel%
    )
)

echo Iniciando servidor WhatsApp Backup...
python whatsapp_viewer.py
pause
