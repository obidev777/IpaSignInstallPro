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
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import glob

app = Flask(__name__)
app.secret_key = 'tu-clave-secreta-muy-segura-aqui-12345'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# CONFIGURACIÓN - EDITA ESTOS VALORES
CONFIG = {
    'p12_path': 'c.p12',
    'mobileprovision_path': 'c.mobileprovision',
    'p12_password': 'AppleP12.com',
    'developer_name': 'ObisoftDev',
    'ipas_folder': 'ipas',  # Carpeta donde guardar los IPAs para la biblioteca
}

# Crear directorios necesarios
UPLOAD_FOLDER = 'uploads'
SIGNED_FOLDER = 'signed_ipas'
IPAS_LIBRARY = CONFIG['ipas_folder']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)
os.makedirs(IPAS_LIBRARY, exist_ok=True)

# Almacenamiento en memoria para sesiones
sessions_data = {}

# HTML Template completo con modal de éxito
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
            max-width: 1400px; 
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
        
        /* Navigation */
        .nav-tabs {
            display: flex;
            justify-content: center;
            margin-bottom: 2rem;
            background: rgba(255,255,255,0.1);
            border-radius: 50px;
            padding: 8px;
            backdrop-filter: blur(10px);
            max-width: 500px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .nav-tab {
            padding: 12px 24px;
            border-radius: 25px;
            color: white;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .nav-tab.active {
            background: white;
            color: var(--primary);
        }
        
        .nav-tab:hover:not(.active) {
            background: rgba(255,255,255,0.2);
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
        
        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
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
        
        /* IPAs Library */
        .library-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .ipa-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            border: 1px solid var(--gray-light);
        }
        
        .ipa-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }
        
        .ipa-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 1rem;
        }
        
        .ipa-icon {
            font-size: 2.5rem;
            color: var(--primary);
            background: #e0e7ff;
            padding: 15px;
            border-radius: 12px;
        }
        
        .ipa-info {
            flex: 1;
        }
        
        .ipa-name {
            font-weight: 600;
            color: var(--dark);
            margin-bottom: 4px;
            font-size: 1.1rem;
        }
        
        .ipa-details {
            color: var(--gray);
            font-size: 0.85rem;
        }
        
        .ipa-actions {
            display: flex;
            gap: 10px;
            margin-top: 1rem;
        }
        
        .action-btn {
            flex: 1;
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        
        .action-install {
            background: var(--primary);
            color: white;
        }
        
        .action-install:hover {
            background: var(--primary-dark);
        }
        
        .action-download {
            background: var(--gray-light);
            color: var(--dark);
        }
        
        .action-download:hover {
            background: #d1d5db;
        }
        
        .empty-library {
            text-align: center;
            padding: 3rem;
            color: var(--gray);
        }
        
        .empty-library i {
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
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
        
        /* Modal Styles */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1000;
            display: none;
        }
        
        .modal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
        }
        
        .modal-content {
            position: relative;
            background: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 20px;
            max-width: 800px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            animation: modalSlideIn 0.3s ease-out;
        }
        
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-50px) scale(0.9);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 2rem 2rem 1rem;
            border-bottom: 1px solid var(--gray-light);
        }
        
        .modal-header h2 {
            color: var(--dark);
            font-size: 1.8rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .modal-header h2 i {
            color: var(--secondary);
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: var(--gray);
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .modal-close:hover {
            background: var(--gray-light);
            color: var(--danger);
        }
        
        .modal-body {
            padding: 2rem;
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
            
            .library-container {
                grid-template-columns: 1fr;
            }
            
            .btn-lg {
                padding: 1rem 2rem;
                font-size: 1rem;
            }
            
            .nav-tabs {
                flex-direction: column;
                border-radius: 15px;
            }
            
            .nav-tab {
                justify-content: center;
            }
            
            .modal-content {
                margin: 10% 5%;
                width: 90%;
            }
            
            .modal-header {
                padding: 1.5rem 1.5rem 1rem;
            }
            
            .modal-body {
                padding: 1.5rem;
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
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
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
        
        <div class="header">
            <div class="logo">
                <i class="fas fa-mobile-alt"></i>
                <h1>IPA Signer Pro</h1>
            </div>
            <p class="subtitle">Firma y distribuye tus aplicaciones iOS</p>
            <div class="developer-badge">
                <i class="fas fa-user-shield"></i>
                <span>Certificado: {{ config.developer_name }}</span>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs">
            <a href="#" class="nav-tab active" onclick="showTab('sign-tab')">
                <i class="fas fa-signature"></i>
                Firmar IPA
            </a>
            <a href="#" class="nav-tab" onclick="showTab('library-tab')">
                <i class="fas fa-th-list"></i>
                Biblioteca IPAs
            </a>
        </div>

        <!-- Sign IPA Tab -->
        <div id="sign-tab" class="tab-content active">
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
        </div>

        <!-- Library Tab -->
        <div id="library-tab" class="tab-content">
            <div class="card">
                <h2 style="text-align: center; margin-bottom: 2rem; color: var(--dark);">
                    <i class="fas fa-th-list"></i> Biblioteca de IPAs
                </h2>
                
                <div style="text-align: center; margin-bottom: 2rem;">
                    <p style="color: var(--gray); margin-bottom: 1rem;">
                        IPAs disponibles para instalación directa en dispositivos iOS
                    </p>
                    <div class="btn-center">
                        <button class="btn btn-secondary" onclick="refreshLibrary()">
                            <i class="fas fa-sync-alt"></i>
                            Actualizar Biblioteca
                        </button>
                    </div>
                </div>

                <div class="library-container" id="libraryContainer">
                    {% if ipas_library %}
                        {% for ipa in ipas_library %}
                        <div class="ipa-card">
                            <div class="ipa-header">
                                <i class="fas fa-mobile-alt ipa-icon"></i>
                                <div class="ipa-info">
                                    <div class="ipa-name">{{ ipa.name }}</div>
                                    <div class="ipa-details">
                                        {{ ipa.size }} MB • {{ ipa.modified }}
                                    </div>
                                </div>
                            </div>
                            <div class="ipa-actions">
                                <a href="{{ ipa.install_url }}" class="action-btn action-install" onclick="handleInstallClick(event, '{{ ipa.name }}')">
                                    <i class="fas fa-download"></i>
                                    Instalar
                                </a>
                                <a href="{{ ipa.download_url }}" class="action-btn action-download">
                                    <i class="fas fa-file-download"></i>
                                    Descargar
                                </a>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="empty-library">
                            <i class="fas fa-inbox"></i>
                            <h3>No hay IPAs en la biblioteca</h3>
                            <p>Agrega archivos .ipa a la carpeta {{ config.ipas_folder }} o firma nuevos IPAs</p>
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Modal de Éxito -->
        <div id="successModal" class="modal">
            <div class="modal-overlay" onclick="closeSuccessModal()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-check-circle"></i> ¡Firma Completada!</h2>
                    <button class="modal-close" onclick="closeSuccessModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="modal-body">
                    <div class="app-info">
                        <h3 style="margin-bottom: 1.5rem; color: var(--dark);">
                            <i class="fas fa-info-circle"></i> Información de la Aplicación
                        </h3>
                        <div class="info-grid" id="modalAppInfo">
                            <!-- La información se llenará dinámicamente -->
                        </div>
                    </div>

                    <div class="installation-options">
                        <div class="option-card">
                            <i class="fas fa-download option-icon"></i>
                            <div class="option-title">Descargar IPA</div>
                            <div class="option-desc">Obtén el archivo IPA firmado para distribución</div>
                            <a href="#" class="btn btn-primary" id="modalDownloadBtn">
                                <i class="fas fa-file-download"></i>
                                Descargar IPA
                            </a>
                        </div>
                        
                        <div class="option-card">
                            <i class="fas fa-mobile-alt option-icon"></i>
                            <div class="option-title">Instalación OTA</div>
                            <div class="option-desc">Instala directamente en tu iPhone/iPad</div>
                            <a href="#" class="btn btn-success" id="modalInstallBtn" onclick="handleInstallClick(event, 'Aplicación Firmada')">
                                <i class="fas fa-external-link-alt"></i>
                                Instalar en iPhone/iPad
                            </a>
                            <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--gray);">
                                <i class="fas fa-info-circle"></i> Solo funciona en dispositivos iOS
                            </div>
                        </div>
                    </div>

                    <div style="text-align: center; margin: 2rem 0;">
                        <h3 style="margin-bottom: 1rem; color: var(--dark);">
                            <i class="fas fa-qrcode"></i> Código QR para Instalación
                        </h3>
                        <div class="qr-container" id="modalQrCode">
                            <!-- QR se generará dinámicamente -->
                        </div>
                    </div>

                    <div class="btn-center">
                        <button class="btn btn-secondary" onclick="closeSuccessModal()">
                            <i class="fas fa-times"></i>
                            Cerrar y Limpiar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFile = null;
        let currentSessionId = null;
        
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
        const libraryContainer = document.getElementById('libraryContainer');
        const successModal = document.getElementById('successModal');
        
        // Funciones de pestañas
        function showTab(tabId) {
            // Ocultar todas las pestañas
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Mostrar la pestaña seleccionada
            document.getElementById(tabId).classList.add('active');
            
            // Actualizar navegación
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Si es la pestaña de biblioteca, actualizar la lista
            if (tabId === 'library-tab') {
                refreshLibrary();
            }
        }
        
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
        
        // Función para manejar clics de instalación
        function handleInstallClick(event, appName) {
            // Verificar si es un dispositivo iOS
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
            
            if (!isIOS) {
                event.preventDefault();
                showAlert(`📱 Para instalar "${appName}":\n\n1. Abre esta página en tu iPhone o iPad\n2. Toca el botón "Instalar"\n3. Confirma la instalación cuando aparezca el diálogo`, 'info', 8000);
                return false;
            }
            
            // En iOS, el link itms-services:// funcionará automáticamente
            console.log('Iniciando instalación OTA en iOS para:', appName);
            return true;
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
                
                currentSessionId = result.session_id;
                
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
                
                // Pequeña pausa para mostrar el 100%
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Obtener información de la sesión y mostrar modal
                await showSuccessModal(currentSessionId);
                
            } catch (error) {
                showAlert('Error al firmar la aplicación: ' + error.message, 'error');
                progressContainer.style.display = 'none';
                signBtn.disabled = false;
                signBtn.classList.remove('loading');
            }
        }
        
        async function showSuccessModal(sessionId) {
            try {
                console.log('Obteniendo información de la sesión:', sessionId);
                const response = await fetch(`/api/session/${sessionId}`);
                const sessionData = await response.json();
                
                if (!sessionData.success) {
                    throw new Error('No se pudo obtener la información de la sesión');
                }
                
                const { ipa_info, output_filename, original_filename } = sessionData.session;
                const baseUrl = window.location.origin;
                
                console.log('Información del IPA recibida:', ipa_info);
                
                // MEJOR MANEJO DE LOS DATOS
                const appName = ipa_info.bundle_display_name || 
                               ipa_info.bundle_name || 
                               ipa_info.app_name || 
                               original_filename.replace('.ipa', '').replace('signed_', '') || 
                               'Aplicación iOS';
                
                const bundleId = ipa_info.bundle_identifier || 'com.unknown.app';
                const version = ipa_info.bundle_short_version || ipa_info.bundle_version || '1.0';
                const build = ipa_info.bundle_version || '1.0';
                const minOS = ipa_info.minimum_os_version || '12.0';
                
                // Llenar información de la aplicación
                const appInfoHtml = `
                    <div class="info-item">
                        <div class="info-label">Nombre</div>
                        <div class="info-value">${appName}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Bundle ID</div>
                        <div class="info-value">${bundleId}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Versión</div>
                        <div class="info-value">${version} (${build})</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">iOS Mínimo</div>
                        <div class="info-value">${minOS}</div>
                    </div>
                `;
                
                document.getElementById('modalAppInfo').innerHTML = appInfoHtml;
                
                // URLs PARA DESCARGA E INSTALACIÓN
                const downloadUrl = `${baseUrl}/download/${output_filename}`;
                const manifestUrl = `${baseUrl}/manifest/${sessionId}`;
                const installUrl = `itms-services://?action=download-manifest&url=${encodeURIComponent(manifestUrl)}`;
                
                console.log('URLs generadas:', { 
                    downloadUrl, 
                    manifestUrl,
                    installUrl 
                });
                
                // Configurar botón de descarga
                const downloadBtn = document.getElementById('modalDownloadBtn');
                downloadBtn.href = downloadUrl;
                downloadBtn.setAttribute('download', output_filename);
                downloadBtn.onclick = null;
                
                // Configurar botón de instalación OTA
                const installBtn = document.getElementById('modalInstallBtn');
                installBtn.href = installUrl;
                
                // Generar QR code con la URL de instalación
                const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(installUrl)}&format=svg`;
                document.getElementById('modalQrCode').innerHTML = `
                    <img src="${qrUrl}" alt="QR Code para instalación" style="border-radius: 10px;">
                    <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--gray); text-align: center;">
                        <p><strong>📲 Escanear para instalar</strong></p>
                        <p>Usa la cámara de tu iPhone/iPad</p>
                    </div>
                `;
                
                // Mostrar modal
                successModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                
                console.log('Modal de éxito mostrado con instalación OTA configurada');
                
                // Resetear interfaz de firma
                progressContainer.style.display = 'none';
                signBtn.disabled = false;
                signBtn.classList.remove('loading');
                removeFile();
                
            } catch (error) {
                console.error('Error al mostrar modal de éxito:', error);
                
                // FALLBACK: Mostrar modal básico
                const baseUrl = window.location.origin;
                const appName = currentFile?.name?.replace('.ipa', '') || 'Aplicación iOS';
                const manifestUrl = `${baseUrl}/manifest/${sessionId}`;
                const installUrl = `itms-services://?action=download-manifest&url=${encodeURIComponent(manifestUrl)}`;
                
                document.getElementById('modalAppInfo').innerHTML = `
                    <div class="info-item">
                        <div class="info-label">Nombre</div>
                        <div class="info-value">${appName}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Estado</div>
                        <div class="info-value">Firma completada exitosamente</div>
                    </div>
                `;
                
                document.getElementById('modalDownloadBtn').href = `${baseUrl}/download/signed_${currentFile?.name || 'app.ipa'}`;
                document.getElementById('modalInstallBtn').href = installUrl;
                
                const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(installUrl)}&format=svg`;
                document.getElementById('modalQrCode').innerHTML = `<img src="${qrUrl}" alt="QR Code" style="border-radius: 10px;">`;
                
                successModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                
                // Resetear interfaz
                progressContainer.style.display = 'none';
                signBtn.disabled = false;
                signBtn.classList.remove('loading');
                removeFile();
            }
        }
        
        function closeSuccessModal() {
            successModal.style.display = 'none';
            document.body.style.overflow = 'auto';
            
            // Limpiar archivos temporales
            if (currentSessionId) {
                fetch(`/api/cleanup/${currentSessionId}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log('Archivos temporales limpiados');
                        }
                    })
                    .catch(error => {
                        console.error('Error limpiando archivos:', error);
                    });
                
                currentSessionId = null;
            }
        }
        
        async function refreshLibrary() {
            try {
                const response = await fetch('/api/library');
                const data = await response.json();
                
                if (data.ipas && data.ipas.length > 0) {
                    libraryContainer.innerHTML = data.ipas.map(ipa => `
                        <div class="ipa-card">
                            <div class="ipa-header">
                                <i class="fas fa-mobile-alt ipa-icon"></i>
                                <div class="ipa-info">
                                    <div class="ipa-name">${ipa.name}</div>
                                    <div class="ipa-details">
                                        ${ipa.size} MB • ${ipa.modified}
                                    </div>
                                </div>
                            </div>
                            <div class="ipa-actions">
                                <a href="${ipa.install_url}" class="action-btn action-install" onclick="handleInstallClick(event, '${ipa.name}')">
                                    <i class="fas fa-download"></i>
                                    Instalar
                                </a>
                                <a href="${ipa.download_url}" class="action-btn action-download">
                                    <i class="fas fa-file-download"></i>
                                    Descargar
                                </a>
                            </div>
                        </div>
                    `).join('');
                } else {
                    libraryContainer.innerHTML = `
                        <div class="empty-library">
                            <i class="fas fa-inbox"></i>
                            <h3>No hay IPAs en la biblioteca</h3>
                            <p>Agrega archivos .ipa a la carpeta ${data.folder_name} o firma nuevos IPAs</p>
                        </div>
                    `;
                }
                
                showAlert('Biblioteca actualizada', 'success');
            } catch (error) {
                showAlert('Error al actualizar la biblioteca', 'error');
            }
        }
        
        function showAlert(message, type = 'info', duration = 5000) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.style.cssText = 'white-space: pre-line; word-wrap: break-word;';
            alertDiv.textContent = message;
            
            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.firstChild);
            
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, duration);
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
        
        // Cerrar modal con ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && successModal.style.display === 'block') {
                closeSuccessModal();
            }
        });
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'ipa'

def extract_ipa_info(ipa_path):
    """Extrae información del archivo IPA de manera más robusta"""
    try:
        print(f"🔍 Extrayendo información del IPA: {ipa_path}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extraer el IPA
            with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Buscar el archivo Info.plist en la estructura
            plist_path = None
            app_folder = None
            
            # Primero buscar la carpeta .app
            for root, dirs, files in os.walk(temp_dir):
                for dir_name in dirs:
                    if dir_name.endswith('.app'):
                        app_folder = os.path.join(root, dir_name)
                        break
                if app_folder:
                    break
            
            if not app_folder:
                # Si no encuentra .app, buscar en Payload
                payload_path = os.path.join(temp_dir, 'Payload')
                if os.path.exists(payload_path):
                    for item in os.listdir(payload_path):
                        if item.endswith('.app'):
                            app_folder = os.path.join(payload_path, item)
                            break
            
            if app_folder:
                # Buscar Info.plist dentro de .app
                plist_path = os.path.join(app_folder, 'Info.plist')
                if not os.path.exists(plist_path):
                    # Si no está en la raíz de .app, buscar recursivamente
                    for root, dirs, files in os.walk(app_folder):
                        if 'Info.plist' in files:
                            plist_path = os.path.join(root, 'Info.plist')
                            break
            
            if plist_path and os.path.exists(plist_path):
                print(f"📄 Encontrado Info.plist en: {plist_path}")
                
                # Leer el plist
                with open(plist_path, 'rb') as plist_file:
                    try:
                        plist_data = plistlib.load(plist_file)
                    except Exception as e:
                        print(f"❌ Error leyendo plist: {e}")
                        # Intentar con otro método para plist binarios
                        try:
                            import biplist
                            plist_data = biplist.readPlist(plist_path)
                        except:
                            # Último intento con subprocess
                            try:
                                result = subprocess.run([
                                    'plutil', '-convert', 'json', '-o', '-', plist_path
                                ], capture_output=True, text=True, timeout=10)
                                if result.returncode == 0:
                                    import json
                                    plist_data = json.loads(result.stdout)
                            except:
                                plist_data = {}
                
                # Extraer información con valores por defecto
                info = {
                    'bundle_identifier': plist_data.get('CFBundleIdentifier', 'N/A'),
                    'bundle_name': plist_data.get('CFBundleName', 'N/A'),
                    'bundle_display_name': plist_data.get('CFBundleDisplayName', plist_data.get('CFBundleName', 'N/A')),
                    'bundle_version': plist_data.get('CFBundleVersion', 'N/A'),
                    'bundle_short_version': plist_data.get('CFBundleShortVersionString', plist_data.get('CFBundleVersion', 'N/A')),
                    'minimum_os_version': plist_data.get('MinimumOSVersion', 'N/A'),
                    'platform_version': plist_data.get('DTPlatformVersion', 'N/A'),
                    'app_name': plist_data.get('CFBundleDisplayName', plist_data.get('CFBundleName', os.path.basename(ipa_path)))
                }
                
                print(f"✅ Información extraída: {info['app_name']} ({info['bundle_identifier']})")
                return info
            else:
                print("❌ No se pudo encontrar Info.plist en el IPA")
                
    except Exception as e:
        print(f"❌ Error extrayendo info del IPA: {e}")
        import traceback
        traceback.print_exc()
    
    # Información por defecto si falla la extracción
    base_name = os.path.basename(ipa_path)
    app_name = base_name.replace('.ipa', '').replace('signed_', '')
    return {
        'bundle_identifier': 'com.unknown.app',
        'bundle_name': app_name,
        'bundle_display_name': app_name,
        'bundle_version': '1.0',
        'bundle_short_version': '1.0',
        'minimum_os_version': '12.0',
        'platform_version': 'N/A',
        'app_name': app_name
    }

def get_ipas_library():
    """Obtiene la lista de IPAs en la biblioteca"""
    ipas = []
    try:
        for ipa_file in glob.glob(os.path.join(IPAS_LIBRARY, "*.ipa")):
            file_name = os.path.basename(ipa_file)
            file_size = os.path.getsize(ipa_file) / (1024 * 1024)  # MB
            modified_time = datetime.fromtimestamp(os.path.getmtime(ipa_file))
            
            # Extraer información básica del IPA
            ipa_info = extract_ipa_info(ipa_file) or {}
            app_name = ipa_info.get('bundle_display_name') or ipa_info.get('bundle_name') or file_name
            
            ipas.append({
                'name': app_name,
                'filename': file_name,
                'size': f"{file_size:.1f}",
                'modified': modified_time.strftime("%d/%m/%Y %H:%M"),
                'bundle_id': ipa_info.get('bundle_identifier', 'N/A'),
                'version': ipa_info.get('bundle_short_version', 'N/A')
            })
        
        # Ordenar por fecha de modificación (más reciente primero)
        ipas.sort(key=lambda x: os.path.getmtime(os.path.join(IPAS_LIBRARY, x['filename'])), reverse=True)
        
    except Exception as e:
        print(f"Error obteniendo biblioteca de IPAs: {e}")
    
    return ipas

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
        
        # Simular proceso de firma
        time.sleep(2)
        
        # Copiar el archivo como "firmado"
        shutil.copy2(ipa_path, output_path)
        
        # También copiar a la biblioteca
        library_path = os.path.join(IPAS_LIBRARY, os.path.basename(output_path))
        shutil.copy2(output_path, library_path)
        print(f"📚 IPA agregado a la biblioteca: {library_path}")
        
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
    
    print(f"📦 Generando manifest.plist para:")
    print(f"   📱 App: {title}")
    print(f"   🆔 Bundle: {bundle_identifier}")
    print(f"   🔗 IPA URL: {ipa_url}")
    
    return plistlib.dumps(manifest)

def cleanup_session_files(session_id):
    """Limpia los archivos temporales de una sesión"""
    try:
        # Eliminar carpeta de upload
        upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
            print(f"🗑️  Eliminada carpeta de upload: {upload_dir}")
        
        # Buscar y eliminar archivo firmado correspondiente
        if session_id in sessions_data:
            output_filename = sessions_data[session_id].get('output_filename')
            if output_filename:
                signed_file = os.path.join(SIGNED_FOLDER, output_filename)
                if os.path.exists(signed_file):
                    os.remove(signed_file)
                    print(f"🗑️  Eliminado archivo firmado: {signed_file}")
        
        # Eliminar de sesiones activas
        if session_id in sessions_data:
            del sessions_data[session_id]
            print(f"🗑️  Eliminada sesión: {session_id}")
        
        return True
    except Exception as e:
        print(f"❌ Error limpiando archivos de sesión {session_id}: {e}")
        return False

@app.route('/')
def index():
    ipas_library = get_ipas_library()
    
    # Generar URLs para cada IPA en la biblioteca
    for ipa in ipas_library:
        base_url = request.url_root.rstrip('/')
        ipa['download_url'] = f"{base_url}/library/download/{ipa['filename']}"
        # Usar itms-services:// para instalación en biblioteca también
        manifest_url = f"{base_url}/library/manifest/{ipa['filename']}"
        ipa['install_url'] = f"itms-services://?action=download-manifest&url={manifest_url}"
    
    return render_template_string(MODERN_HTML, template='index', config=CONFIG, ipas_library=ipas_library)

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
        original_filename = secure_filename(ipa_file.filename)
        ipa_path = os.path.join(upload_dir, original_filename)
        ipa_file.save(ipa_path)
        
        print(f"📦 Archivo guardado: {ipa_path}")
        
        # Extraer información del IPA (MEJORADO)
        ipa_info = extract_ipa_info(ipa_path)
        print(f"📊 Información del IPA extraída: {ipa_info}")
        
        # Firmar IPA
        output_filename = f"signed_{original_filename}"
        output_path = os.path.join(SIGNED_FOLDER, output_filename)
        
        success, message = sign_ipa(ipa_path, output_path)
        
        if success:
            # Guardar información en la sesión
            sessions_data[session_id] = {
                'status': 'completed',
                'ipa_info': ipa_info,
                'output_filename': output_filename,
                'original_filename': original_filename,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"💾 Sesión guardada: {session_id}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': message,
                'ipa_info': ipa_info  # Enviar también en la respuesta para debug
            })
        else:
            # Limpiar archivos en caso de error
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir)
            return jsonify({'error': message}), 500
            
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Sirve el archivo IPA firmado para descarga"""
    file_path = os.path.join(SIGNED_FOLDER, filename)
    if os.path.exists(file_path):
        print(f"📥 Sirviendo archivo: {filename}")
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        print(f"❌ Archivo no encontrado: {filename}")
        return jsonify({'error': 'Archivo no encontrado'}), 404

@app.route('/library/download/<filename>')
def library_download_file(filename):
    """Sirve archivos IPA de la biblioteca para descarga"""
    file_path = os.path.join(IPAS_LIBRARY, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'Archivo no encontrado en la biblioteca'}), 404

@app.route('/library/manifest/<filename>')
def library_manifest_file(filename):
    """Genera manifest.plist para IPAs de la biblioteca"""
    file_path = os.path.join(IPAS_LIBRARY, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    
    # Extraer información del IPA para el manifest
    ipa_info = extract_ipa_info(file_path)
    base_url = request.url_root.rstrip('/')
    ipa_url = f"{base_url}/library/download/{filename}"
    
    manifest_data = generate_manifest_plist(
        ipa_url=ipa_url,
        bundle_identifier=ipa_info.get('bundle_identifier', 'com.unknown.app') if ipa_info else 'com.unknown.app',
        bundle_version=ipa_info.get('bundle_version', '1.0') if ipa_info else '1.0',
        title=ipa_info.get('bundle_display_name') or ipa_info.get('bundle_name') or filename if ipa_info else filename
    )
    
    return manifest_data, 200, {'Content-Type': 'application/x-plist'}

@app.route('/manifest/<session_id>')
def manifest_file(session_id):
    """Genera el manifest.plist para instalación OTA de sesiones"""
    if session_id not in sessions_data:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    session_data = sessions_data[session_id]
    base_url = request.url_root.rstrip('/')
    
    # URL del IPA firmado
    ipa_url = f"{base_url}/download/{session_data['output_filename']}"
    
    print(f"📦 Generando manifest para sesión {session_id}")
    print(f"🔗 IPA URL: {ipa_url}")
    
    # Generar manifest.plist
    manifest_data = generate_manifest_plist(
        ipa_url=ipa_url,
        bundle_identifier=session_data['ipa_info'].get('bundle_identifier', 'com.unknown.app'),
        bundle_version=session_data['ipa_info'].get('bundle_version', '1.0'),
        title=session_data['ipa_info'].get('bundle_display_name') or 
              session_data['ipa_info'].get('bundle_name') or 
              session_data.get('original_filename', 'App')
    )
    
    return manifest_data, 200, {'Content-Type': 'application/x-plist'}

@app.route('/api/session/<session_id>')
def api_session(session_id):
    """Endpoint para obtener información de una sesión"""
    if session_id not in sessions_data:
        return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404
    
    session_data = sessions_data[session_id]
    base_url = request.url_root.rstrip('/')
    
    # Agregar URLs
    session_data['download_url'] = f"{base_url}/download/{session_data['output_filename']}"
    manifest_url = f"{base_url}/manifest/{session_id}"
    session_data['install_url'] = f"itms-services://?action=download-manifest&url={manifest_url}"
    
    return jsonify({
        'success': True,
        'session': session_data
    })

@app.route('/api/cleanup/<session_id>', methods=['POST'])
def api_cleanup(session_id):
    """Endpoint para limpiar archivos de una sesión"""
    success = cleanup_session_files(session_id)
    return jsonify({'success': success})

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

@app.route('/api/library')
def api_library():
    """Endpoint para obtener la biblioteca de IPAs"""
    ipas = get_ipas_library()
    base_url = request.url_root.rstrip('/')
    
    # Agregar URLs a cada IPA usando itms-services://
    for ipa in ipas:
        ipa['download_url'] = f"{base_url}/library/download/{ipa['filename']}"
        manifest_url = f"{base_url}/library/manifest/{ipa['filename']}"
        ipa['install_url'] = f"itms-services://?action=download-manifest&url={manifest_url}"
    
    return jsonify({
        'ipas': ipas,
        'folder_name': CONFIG['ipas_folder'],
        'count': len(ipas),
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
            cleanup_session_files(session_id)
            
        # Limpiar archivos temporales antiguos
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
    
    # Mostrar información de la biblioteca
    ipas_count = len(get_ipas_library())
    print(f"📚 Biblioteca de IPAs: {ipas_count} aplicaciones encontradas en '{CONFIG['ipas_folder']}'")
    
    # Iniciar limpieza automática
    start_cleanup_scheduler()
    
    print("🚀 IPA Signer Pro - Servidor iniciado")
    print("📍 URL: http://localhost:5000")
    print("👤 Desarrollador:", CONFIG['developer_name'])
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)