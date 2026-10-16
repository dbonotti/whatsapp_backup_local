@echo off
cd /d "%~dp0"
title Instalador de Dependencias - WhatsApp Backup
echo ========================================================
echo   Instalando dependencias de Python (cryptography)...
echo ========================================================
python -m pip install -r requirements.txt
echo.
echo Proceso finalizado. Puedes iniciar el visor ejecutando 'iniciar_visor.bat'.
pause
