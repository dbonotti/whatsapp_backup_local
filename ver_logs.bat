@echo off
cd /d "%~dp0"
title Logs de Sincronizacion - WhatsApp Backup
cls
echo ========================================================================
echo         WHATSAPP BACKUP - LOGS DE SINCRONIZACION EN VIVO
echo ========================================================================
echo   Presiona Ctrl + C para cerrar esta ventana de logs en cualquier momento.
echo ========================================================================
echo.

if not exist "logs" mkdir "logs"
if not exist "logs\sync.log" (
    echo [%date% %time%] Servidor iniciado. Esperando sincronizaciones... > "logs\sync.log"
)

powershell -NoExit -ExecutionPolicy Bypass -Command "$Host.UI.RawUI.WindowTitle = 'Logs de Sincronizacion - WhatsApp Backup'; Get-Content -Path 'logs\sync.log' -Wait -Tail 50"
