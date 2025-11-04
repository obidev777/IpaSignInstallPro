@echo off
chcp 65001 >nul
title IPA Signer Pro

echo.
echo 🚀 Iniciando IPA Signer Pro...
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no encontrado
    echo Instala Python desde https://python.org
    pause
    exit /b 1
)

echo ✅ Python detectado

:: Verificar e instalar Flask
python -c "import Flask" 2>nul
if errorlevel 1 (
    echo 📦 Instalando Flask...
    python -m pip install Flask --quiet
    if errorlevel 1 (
        echo ❌ Error instalando Flask
        pause
        exit /b 1
    )
    echo ✅ Flask instalado
) else (
    echo ✅ Flask ya está instalado
)

:: Verificar e instalar Werkzeug
python -c "import werkzeug" 2>nul
if errorlevel 1 (
    echo 📦 Instalando Werkzeug...
    python -m pip install Werkzeug --quiet
    if errorlevel 1 (
        echo ❌ Error instalando Werkzeug
        pause
        exit /b 1
    )
    echo ✅ Werkzeug instalado
) else (
    echo ✅ Werkzeug ya está instalado
)

echo.
echo 🎉 Todas las dependencias listas!
echo 🌐 Iniciando servidor en http://localhost:5000
echo ⏹️  Presiona Ctrl+C para detener
echo.

:: Ejecutar la aplicación
python app.py

echo.
echo ❌ Servidor detenido
pause