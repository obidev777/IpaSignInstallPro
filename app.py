import os
import subprocess
import tempfile
import shutil
import plistlib
import uuid
import zipfile
import threading
import time
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'tu-clave-secreta-muy-segura-aqui-12345'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# CONFIGURACIÓN - EDITA ESTOS VALORES CON TUS RUTAS Y CONTRASEÑA
CONFIG = {
    'p12_path': 'c.p12',  # Cambia por la ruta real de tu .p12
    'mobileprovision_path': 'c.mobileprovision',  # Cambia por la ruta real de tu .mobileprovision
    'p12_password': 'AppleP12.com',  # Cambia por tu contraseña real
    'developer_name': 'ObisoftDev',  # Opcional: nombre para mostrar
}

# Crear directorios necesarios
UPLOAD_FOLDER = 'uploads'
SIGNED_FOLDER = 'signed_ipas'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)

# Almacenamiento en memoria para sesiones (en producción usa Redis o base de datos)
sessions_data = {}

# HTML Template completo moderno y responsive
MODERN_HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% if title %}{{ title }}{% else %}IPA Signer Pro{% endif %}</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --dark: #1f2937;
            --light: #f8fafc;
            --gray: #6b7280;
            --gray-light: #e5e7eb;
        }
        
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            padding: 20px;
            color: var(--dark);
        }
        
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        
        /* Header Styles */
        .header { 
            text-align: center; 
            margin-bottom: 3rem; 
            color: white; 
        }
        
        .logo { 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 15px; 
            margin-bottom: 10px; 
        }
        
        .logo i { 
            font-size: 2.5rem; 
            background: linear-gradient(135deg, #ff6b6b, #feca57);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .logo h1 { 
            font-size: 2.5rem; 
            font-weight: 700; 
            background: linear-gradient(135deg, #fff, #e0e7ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle { 
            font-size: 1.2rem; 
            opacity: 0.9; 
            font-weight: 300; 
            margin-bottom: 1rem;
        }
        
        .developer-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            backdrop-filter: blur(10px);
        }
        
        /* Card Styles */
        .card {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
        }
        
        /* Upload Area */
        .upload-area {
            border: 3px dashed var(--gray-light);
            border-radius: 15px;
            padding: 3rem 2rem;
            text-align: center;
            transition: all 0.3s ease;
            background: var(--light);
            cursor: pointer;
            position: relative;
        }
        
        .upload-area:hover {
            border-color: var(--primary);
            background: #f0f4ff;
        }
        
        .upload-area.dragover {
            border-color: var(--primary);
            background: #e0e7ff;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 4rem;
            color: var(--gray);
            margin-bottom: 1rem;
        }
        
        .upload-text {
            color: var(--dark);
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .upload-subtext {
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .file-input {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            opacity: 0;
            cursor: pointer;
        }
        
        /* File Preview */
        .file-preview {
            margin-top: 1.5rem;
            padding: 1.5rem;
            background: var(--light);
            border-radius: 12px;
            border-left: 4px solid var(--secondary);
            display: none;
        }
        
        .file-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .file-icon {
            font-size: 2rem;
            color: var(--secondary);
        }
        
        .file-details {
            flex: 1;
        }
        
        .file-name {
            font-weight: 600;
            color: var(--dark);
            margin-bottom: 4px;
        }
        
        .file-size {
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .remove-btn {
            background: none;
            border: none;
            color: var(--danger);
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            transition: background 0.3s ease;
        }
        
        .remove-btn:hover {
            background: #fee2e2;
        }
        
        /* Progress Bar */
        .progress-container {
            margin: 2rem 0;
            display: none;
        }
        
        .progress-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .progress-label {
            font-weight: 600;
            color: var(--dark);
        }
        
        .progress-percentage {
            color: var(--primary);
            font-weight: 600;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--gray-light);
            border-radius: 10px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 10px;
            transition: width 0.3s ease;
            width: 0%;
        }
        
        .progress-steps {
            display: flex;
            justify-content: space-between;
            margin-top: 0.5rem;
            font-size: 0.8rem;
            color: var(--gray);
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 1rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            font-size: 1rem;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
        }
        
        .btn-success {
            background: linear-gradient(135deg, var(--secondary), #059669);
            color: white;
        }
        
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4);
        }
        
        .btn-secondary {
            background: var(--gray-light);
            color: var(--dark);
        }
        
        .btn-secondary:hover {
            background: #d1d5db;
            transform: translateY(-2px);
        }
        
        .btn-lg {
            padding: 1.2rem 3rem;
            font-size: 1.1rem;
        }
        
        .btn-center {
            display: flex;
            justify-content: center;
            margin-top: 2rem;
        }
        
        /* Features Grid */
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
            margin-top: 3rem;
        }
        
        .feature-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
            color: white;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
        }
        
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            opacity: 0.9;
        }
        
        .feature-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .feature-desc {
            opacity: 0.8;
            line-height: 1.6;
        }
        
        /* Success Page */
        .success-container {
            text-align: center;
        }
        
        .success-icon {
            font-size: 5rem;
            color: var(--secondary);
            margin-bottom: 1rem;
        }
        
        .success-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .success-subtitle {
            color: var(--gray);
            font-size: 1.2rem;
            margin-bottom: 3rem;
        }
        
        .app-info {
            background: var(--light);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: left;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }
        
        .info-item {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .info-label {
            font-weight: 600;
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .info-value {
            color: var(--dark);
            font-weight: 500;
        }
        
        .installation-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .option-card {
            background: var(--light);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
        }
        
        .option-icon {
            font-size: 3rem;
            color: var(--primary);
            margin-bottom: 1rem;
        }
        
        .option-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--dark);
        }
        
        .option-desc {
            color: var(--gray);
            margin-bottom: 1.5rem;
        }
        
        .qr-container {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            display: inline-block;
            margin: 1rem 0;
        }
        
        /* Alerts */
        .alert {
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            font-weight: 500;
            border-left: 4px solid;
        }
        
        .alert-error {
            background: #fef2f2;
            color: var(--danger);
            border-left-color: var(--danger);
        }
        
        .alert-success {
            background: #f0fdf4;
            color: #166534;
            border-left-color: var(--secondary);
        }
        
        .alert-info {
            background: #f0f9ff;
            color: #0369a1;
            border-left-color: #0ea5e9;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            body { 
                padding: 10px; 
            }
            
            .logo h1 { 
                font-size: 2rem; 
            }
            
            .card {
                padding: 1.5rem;
            }
            
            .upload-area {
                padding: 2rem 1rem;
            }
            
            .features {
                grid-template-columns: 1fr;
            }
            
            .installation-options {
                grid-template-columns: 1fr;
            }
            
            .info-grid {
                grid-template-columns: 1fr;
            }
            
            .btn-lg {
                padding: 1rem 2rem;
                font-size: 1rem;
            }
        }
        
        /* Loading Animation */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% if template == 'index' %}
        <!-- Página Principal -->
        <div class="header">
            <div class="logo">
                <i class="fas fa-mobile-alt"></i>
                <h1>IPA Signer Pro</h1>
            </div>
            <p class="subtitle">Firma tus aplicaciones iOS de forma rápida y segura</p>
            <div class="developer-badge">
                <i class="fas fa-user-shield"></i>
                <span>Certificado: {{ config.developer_name }}</span>
            </div>
        </div>

        <div class="card">
            <h2 style="text-align: center; margin-bottom: 2rem; color: var(--dark);">
                <i class="fas fa-upload"></i> Subir Archivo IPA
            </h2>
            
            <div class="upload-area" id="uploadArea">
                <input type="file" class="file-input" id="fileInput" accept=".ipa" required>
                <div class="upload-content">
                    <i class="fas fa-cloud-upload-alt upload-icon"></i>
                    <div class="upload-text">Arrastra tu archivo .ipa aquí</div>
                    <div class="upload-subtext">o haz clic para seleccionar</div>
                    <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--gray);">
                        <i class="fas fa-info-circle"></i> Tamaño máximo: 500MB
                    </div>
                </div>
            </div>

            <div class="file-preview" id="filePreview">
                <div class="file-info">
                    <i class="fas fa-file-archive file-icon"></i>
                    <div class="file-details">
                        <div class="file-name" id="fileName">Archivo seleccionado</div>
                        <div class="file-size" id="fileSize">0 MB</div>
                    </div>
                    <button class="remove-btn" onclick="removeFile()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>

            <!-- Progress Bar -->
            <div class="progress-container" id="progressContainer">
                <div class="progress-header">
                    <div class="progress-label" id="progressLabel">Preparando firma...</div>
                    <div class="progress-percentage" id="progressPercentage">0%</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-steps">
                    <span id="step1">Subiendo</span>
                    <span id="step2">Verificando</span>
                    <span id="step3">Firmando</span>
                    <span id="step4">Finalizando</span>
                </div>
            </div>

            <div class="btn-center">
                <button class="btn btn-primary btn-lg" id="signBtn" onclick="startSigning()" disabled>
                    <i class="fas fa-signature"></i>
                    <span id="btnText">Firmar IPA</span>
                </button>
            </div>
        </div>

        <div class="features">
            <div class="feature-card">
                <i class="fas fa-shield-alt feature-icon"></i>
                <div class="feature-title">Firma Segura</div>
                <div class="feature-desc">Usamos tu certificado oficial para firmar las aplicaciones</div>
            </div>
            <div class="feature-card">
                <i class="fas fa-bolt feature-icon"></i>
                <div class="feature-title">Proceso Rápido</div>
                <div class="feature-desc">Firma automática en segundos con progreso en tiempo real</div>
            </div>
            <div class="feature-card">
                <i class="fas fa-download feature-icon"></i>
                <div class="feature-title">Descarga Inmediata</div>
                <div class="feature-desc">Obtén tu IPA firmado listo para instalar al instante</div>
            </div>
        </div>

        {% elif template == 'success' %}
        <!-- Página de Éxito -->
        <div class="success-container">
            <div class="card">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h1 class="success-title">¡Firma Completada!</h1>
                <p class="success-subtitle">Tu aplicación ha sido firmada exitosamente</p>

                {% if ipa_info %}
                <div class="app-info">
                    <h3 style="margin-bottom: 1.5rem; color: var(--dark);">
                        <i class="fas fa-info-circle"></i> Información de la Aplicación
                    </h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Nombre</div>
                            <div class="info-value">{{ ipa_info.bundle_display_name or ipa_info.bundle_name }}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Bundle ID</div>
                            <div class="info-value">{{ ipa_info.bundle_identifier }}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Versión</div>
                            <div class="info-value">{{ ipa_info.bundle_short_version }} ({{ ipa_info.bundle_version }})</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">iOS Mínimo</div>
                            <div class="info-value">{{ ipa_info.minimum_os_version }}</div>
                        </div>
                    </div>
                </div>
                {% endif %}

                <div class="installation-options">
                    <div class="option-card">
                        <i class="fas fa-download option-icon"></i>
                        <div class="option-title">Descargar IPA</div>
                        <div class="option-desc">Obtén el archivo IPA firmado para distribución</div>
                        <a href="{{ ipa_url }}" class="btn btn-primary">
                            <i class="fas fa-file-download"></i>
                            Descargar IPA
                        </a>
                    </div>
                    
                    <div class="option-card">
                        <i class="fas fa-mobile-alt option-icon"></i>
                        <div class="option-title">Instalación Directa</div>
                        <div class="option-desc">Instala directamente en tu dispositivo iOS</div>
                        <a href="{{ install_url }}" class="btn btn-success">
                            <i class="fas fa-external-link-alt"></i>
                            Instalar en Dispositivo
                        </a>
                        <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--gray);">
                            <i class="fas fa-info-circle"></i> Abre esta página en tu iPhone/iPad
                        </div>
                    </div>
                </div>

                <div style="margin: 2rem 0;">
                    <h3 style="margin-bottom: 1rem; color: var(--dark);">
                        <i class="fas fa-qrcode"></i> Código QR para Instalación
                    </h3>
                    <div class="qr-container">
                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={{ install_url | urlencode }}&format=svg" 
                             alt="QR Code" style="border-radius: 10px;">
                    </div>
                </div>

                <div class="btn-center">
                    <a href="/" class="btn btn-secondary">
                        <i class="fas fa-plus"></i>
                        Firmar Otra App
                    </a>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <script>
        let currentFile = null;
        
        // Elementos del DOM
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const signBtn = document.getElementById('signBtn');
        const btnText = document.getElementById('btnText');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressPercentage = document.getElementById('progressPercentage');
        const progressLabel = document.getElementById('progressLabel');
        
        // Configurar drag and drop
        ['dragover', 'dragenter'].forEach(event => {
            uploadArea.addEventListener(event, (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
        });
        
        ['dragleave', 'drop'].forEach(event => {
            uploadArea.addEventListener(event, (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        function handleFileSelect(file) {
            if (!file.name.toLowerCase().endsWith('.ipa')) {
                showAlert('Por favor, selecciona un archivo .ipa válido', 'error');
                return;
            }
            
            currentFile = file;
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
            
            fileName.textContent = file.name;
            fileSize.textContent = `${fileSizeMB} MB`;
            filePreview.style.display = 'block';
            signBtn.disabled = false;
            
            // Actualizar texto del botón
            btnText.innerHTML = `Firmar <strong>${file.name}</strong>`;
        }
        
        function removeFile() {
            currentFile = null;
            fileInput.value = '';
            filePreview.style.display = 'none';
            signBtn.disabled = true;
            btnText.textContent = 'Firmar IPA';
        }
        
        function updateProgress(percent, message) {
            progressFill.style.width = percent + '%';
            progressPercentage.textContent = percent + '%';
            progressLabel.textContent = message;
            
            // Actualizar estados de los pasos
            const steps = ['step1', 'step2', 'step3', 'step4'];
            const stepIndex = Math.floor(percent / 25);
            
            steps.forEach((step, index) => {
                const element = document.getElementById(step);
                if (index < stepIndex) {
                    element.style.color = 'var(--secondary)';
                    element.style.fontWeight = '600';
                } else if (index === stepIndex) {
                    element.style.color = 'var(--primary)';
                    element.style.fontWeight = '600';
                }
            });
        }
        
        async function startSigning() {
            if (!currentFile) return;
            
            // Mostrar progreso
            progressContainer.style.display = 'block';
            signBtn.disabled = true;
            signBtn.classList.add('loading');
            
            try {
                // Subir archivo
                updateProgress(10, 'Subiendo archivo...');
                const formData = new FormData();
                formData.append('ipa_file', currentFile);
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || 'Error en la subida del archivo');
                }
                
                if (!result.success) {
                    throw new Error(result.error || 'Error en el servidor');
                }
                
                // Simular progreso de firma
                const progressStages = [
                    { percent: 30, message: 'Verificando archivo...' },
                    { percent: 50, message: 'Aplicando certificado...' },
                    { percent: 70, message: 'Firmando aplicación...' },
                    { percent: 90, message: 'Generando IPA firmado...' },
                    { percent: 100, message: '¡Firma completada!' }
                ];
                
                for (const stage of progressStages) {
                    await new Promise(resolve => setTimeout(resolve, 800));
                    updateProgress(stage.percent, stage.message);
                }
                
                // Redirigir a la página de éxito con el session_id
                setTimeout(() => {
                    window.location.href = '/success?session_id=' + result.session_id;
                }, 1000);
                
            } catch (error) {
                showAlert('Error al firmar la aplicación: ' + error.message, 'error');
                progressContainer.style.display = 'none';
                signBtn.disabled = false;
                signBtn.classList.remove('loading');
            }
        }
        
        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
        
        // Verificar estado del servidor al cargar la página
        window.addEventListener('load', async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (!data.certificate_configured) {
                    showAlert('Configuración del certificado no encontrada. Contacta al administrador.', 'error');
                }
            } catch (error) {
                console.log('No se pudo verificar el estado del servidor');
            }
        });
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'ipa'

def extract_ipa_info(ipa_path):
    """Extrae información del archivo IPA"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            plist_path = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file == 'Info.plist':
                        plist_path = os.path.join(root, file)
                        break
                if plist_path:
                    break
            
            if plist_path:
                with open(plist_path, 'rb') as plist_file:
                    plist_data = plistlib.load(plist_file)
                    
                    info = {
                        'bundle_identifier': plist_data.get('CFBundleIdentifier', 'N/A'),
                        'bundle_name': plist_data.get('CFBundleName', 'N/A'),
                        'bundle_display_name': plist_data.get('CFBundleDisplayName', 'N/A'),
                        'bundle_version': plist_data.get('CFBundleVersion', 'N/A'),
                        'bundle_short_version': plist_data.get('CFBundleShortVersionString', 'N/A'),
                        'minimum_os_version': plist_data.get('MinimumOSVersion', 'N/A'),
                        'platform_version': plist_data.get('DTPlatformVersion', 'N/A')
                    }
                    return info
    except Exception as e:
        print(f"Error extrayendo info del IPA: {e}")
    return None

def sign_ipa(ipa_path, output_path):
    """Firma el archivo IPA usando la configuración predefinida"""
    try:
        # Verificar que los archivos de configuración existen
        if not os.path.exists(CONFIG['p12_path']):
            raise FileNotFoundError(f"Certificado P12 no encontrado: {CONFIG['p12_path']}")
        
        if not os.path.exists(CONFIG['mobileprovision_path']):
            raise FileNotFoundError(f"Profile de provisioning no encontrado: {CONFIG['mobileprovision_path']}")
        
        print("🔐 Iniciando proceso de firma...")
        print(f"📱 IPA: {ipa_path}")
        print(f"🔑 Certificado: {CONFIG['p12_path']}")
        print(f"📄 Profile: {CONFIG['mobileprovision_path']}")
        print(f"👤 Desarrollador: {CONFIG['developer_name']}")
        
        # Simular proceso de firma (en producción aquí iría la lógica real)
        # Esto es solo para demostración - reemplaza con tu lógica de firma real
        
        time.sleep(2)  # Simular tiempo de procesamiento
        
        # Copiar el archivo como "firmado" (en producción, aquí se firmaría realmente)
        shutil.copy2(ipa_path, output_path)
        
        print("✅ Firma completada exitosamente")
        return True, "Firma completada exitosamente"
        
    except Exception as e:
        print(f"❌ Error en la firma: {str(e)}")
        return False, f"Error en la firma: {str(e)}"

def generate_manifest_plist(ipa_url, bundle_identifier, bundle_version, title):
    """Genera un archivo manifest.plist para instalación OTA"""
    manifest = {
        'items': [
            {
                'assets': [
                    {
                        'kind': 'software-package',
                        'url': ipa_url
                    }
                ],
                'metadata': {
                    'bundle-identifier': bundle_identifier,
                    'bundle-version': bundle_version,
                    'kind': 'software',
                    'title': title
                }
            }
        ]
    }
    return plistlib.dumps(manifest)

@app.route('/')
def index():
    return render_template_string(MODERN_HTML, template='index', config=CONFIG)

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if 'ipa_file' not in request.files:
            return jsonify({'error': 'No se seleccionó archivo IPA'}), 400
        
        ipa_file = request.files['ipa_file']
        
        if ipa_file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo IPA'}), 400
        
        if not allowed_file(ipa_file.filename):
            return jsonify({'error': 'Archivo IPA no válido'}), 400
        
        # Generar session_id único
        session_id = str(uuid.uuid4())
        upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Guardar archivo
        ipa_path = os.path.join(upload_dir, secure_filename(ipa_file.filename))
        ipa_file.save(ipa_path)
        
        # Extraer información del IPA
        ipa_info = extract_ipa_info(ipa_path)
        
        # Firmar IPA
        output_filename = f"signed_{secure_filename(ipa_file.filename)}"
        output_path = os.path.join(SIGNED_FOLDER, output_filename)
        
        success, message = sign_ipa(ipa_path, output_path)
        
        if success:
            # Guardar información en la sesión
            sessions_data[session_id] = {
                'status': 'completed',
                'ipa_info': ipa_info,
                'output_filename': output_filename,
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': message
            })
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/success')
def success_page():
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('No se proporcionó ID de sesión', 'error')
        return redirect('/')
    
    if session_id not in sessions_data:
        flash('Sesión no válida o expirada', 'error')
        return redirect('/')
    
    session_data = sessions_data[session_id]
    
    if session_data['status'] != 'completed':
        flash('La firma aún no ha sido completada', 'error')
        return redirect('/')
    
    # Generar URLs para instalación
    base_url = request.url_root.rstrip('/')
    ipa_url = f"{base_url}/download/{session_data['output_filename']}"
    manifest_url = f"{base_url}/manifest/{session_id}"
    install_url = f"itms-services://?action=download-manifest&url={manifest_url}"
    
    return render_template_string(MODERN_HTML, 
                                template='success',
                                ipa_info=session_data['ipa_info'],
                                ipa_url=ipa_url,
                                manifest_url=manifest_url,
                                install_url=install_url)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(SIGNED_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('Archivo no encontrado', 'error')
        return redirect('/')

@app.route('/manifest/<session_id>')
def manifest_file(session_id):
    if session_id not in sessions_data:
        return 'Sesión no válida', 404
    
    session_data = sessions_data[session_id]
    base_url = request.url_root.rstrip('/')
    ipa_url = f"{base_url}/download/{session_data['output_filename']}"
    
    manifest_data = generate_manifest_plist(
        ipa_url=ipa_url,
        bundle_identifier=session_data['ipa_info']['bundle_identifier'],
        bundle_version=session_data['ipa_info']['bundle_version'],
        title=session_data['ipa_info']['bundle_display_name'] or session_data['ipa_info']['bundle_name']
    )
    
    return manifest_data, 200, {'Content-Type': 'application/x-plist'}

@app.route('/api/status')
def api_status():
    """Endpoint para verificar el estado del servidor"""
    certificate_configured = os.path.exists(CONFIG['p12_path']) and os.path.exists(CONFIG['mobileprovision_path'])
    
    return jsonify({
        'status': 'running',
        'certificate_configured': certificate_configured,
        'developer': CONFIG['developer_name'],
        'sessions_active': len(sessions_data),
        'timestamp': datetime.now().isoformat()
    })

def cleanup_old_sessions():
    """Limpia sesiones antiguas"""
    try:
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in sessions_data.items():
            session_time = datetime.fromisoformat(session_data['timestamp'])
            if (current_time - session_time).total_seconds() > 3600:  # 1 hora
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del sessions_data[session_id]
            
        # Limpiar archivos temporales
        current_time_ts = time.time()
        for folder in os.listdir(UPLOAD_FOLDER):
            folder_path = os.path.join(UPLOAD_FOLDER, folder)
            if os.path.isdir(folder_path):
                folder_time = os.path.getctime(folder_path)
                if current_time_ts - folder_time > 3600:
                    shutil.rmtree(folder_path)
        
        # Limpiar archivos firmados antiguos (24 horas)
        for file in os.listdir(SIGNED_FOLDER):
            file_path = os.path.join(SIGNED_FOLDER, file)
            if os.path.isfile(file_path):
                file_time = os.path.getctime(file_path)
                if current_time_ts - file_time > 86400:
                    os.remove(file_path)
                    
    except Exception as e:
        print(f"Error en limpieza: {e}")

def start_cleanup_scheduler():
    """Inicia el programador de limpieza automática"""
    def cleanup_job():
        while True:
            time.sleep(1800)  # Ejecutar cada 30 minutos
            cleanup_old_sessions()
    
    thread = threading.Thread(target=cleanup_job, daemon=True)
    thread.start()

if __name__ == '__main__':
    # Verificar configuración
    print("🔍 Verificando configuración...")
    if not os.path.exists(CONFIG['p12_path']):
        print(f"❌ ERROR: No se encuentra el certificado P12 en: {CONFIG['p12_path']}")
        print("   Por favor, edita la variable CONFIG['p12_path'] con la ruta correcta")
    
    if not os.path.exists(CONFIG['mobileprovision_path']):
        print(f"❌ ERROR: No se encuentra el profile de provisioning en: {CONFIG['mobileprovision_path']}")
        print("   Por favor, edita la variable CONFIG['mobileprovision_path'] con la ruta correcta")
    
    if CONFIG['p12_password'] == 'tu_password_aqui':
        print("❌ ERROR: No has configurado la contraseña del certificado P12")
        print("   Por favor, edita la variable CONFIG['p12_password'] con tu contraseña real")
    
    # Iniciar limpieza automática
    start_cleanup_scheduler()
    
    print("🚀 IPA Signer Pro - Servidor iniciado")
    print("📍 URL: http://localhost:5000")
    print("👤 Desarrollador:", CONFIG['developer_name'])
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)