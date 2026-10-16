import sqlite3
import json
import os
import mimetypes
import webbrowser
import traceback
import html
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import db_manager
import media_manager

PORT = 8080

HTML_UI = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WhatsApp Backup - Visor Local Avanzado</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
      background-color: #111b21; 
      height: 100vh; 
      display: flex; 
      justify-content: center; 
      align-items: center;
      color: #111b21;
    }
    #app-container { display: flex; width: 100vw; height: 100vh; background-color: #fff; overflow: hidden; }

    /* Scrollbars modernos estilo WhatsApp */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(11,20,26,0.18); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(11,20,26,0.28); }

    /* Panel izquierdo (Sidebar) */
    #sidebar { width: 410px; min-width: 340px; border-right: 1px solid #e9edef; display: flex; flex-direction: column; background: #ffffff; }
    .sidebar-header { 
      height: 60px; 
      background: #f0f2f5; 
      display: flex; 
      align-items: center; 
      justify-content: space-between; 
      padding: 0 16px; 
      font-weight: 600; 
      font-size: 15px;
      color: #111b21; 
      border-bottom: 1px solid #e9edef; 
    }
    .brand-title { display: flex; align-items: center; gap: 8px; }
    .brand-title svg { fill: #25d366; }
    
    .sidebar-actions { display: flex; align-items: center; gap: 6px; }
    .btn-header-action {
      border: none;
      background: #ffffff;
      border: 1px solid #d1d7db;
      border-radius: 14px;
      padding: 4px 10px;
      font-size: 11.5px;
      font-weight: 600;
      color: #111b21;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s;
    }
    .btn-header-action:hover { background: #f5f6f6; border-color: #00a884; color: #00a884; }

    .sync-badge { 
      font-size: 11.5px; 
      padding: 4px 10px; 
      border-radius: 14px; 
      background: #e7fce3; 
      color: #075e54; 
      font-weight: 600; 
      display: flex; 
      align-items: center; 
      gap: 6px; 
    }
    .sync-dot { width: 7px; height: 7px; border-radius: 50%; background: #25d366; }

    .search-section { padding: 8px 12px; background: #ffffff; border-bottom: 1px solid #f0f2f5; display: flex; flex-direction: column; gap: 6px; }
    .search-box-wrapper { display: flex; position: relative; align-items: center; }
    .search-box { 
      width: 100%; 
      padding: 8px 12px 8px 36px; 
      border-radius: 8px; 
      border: 1px solid #e9edef; 
      background: #f0f2f5; 
      font-size: 14px; 
      outline: none; 
      transition: all 0.2s;
    }
    .search-box:focus { background: #ffffff; border-color: #00a884; box-shadow: 0 0 0 1px #00a884; }
    .search-icon-svg { position: absolute; left: 10px; fill: #54656f; width: 16px; height: 16px; pointer-events: none; }
    
    .search-mode-tabs { display: flex; gap: 6px; font-size: 12px; }
    .tab-btn { 
      border: none; 
      background: none; 
      padding: 4px 10px; 
      cursor: pointer; 
      color: #54656f; 
      border-radius: 12px; 
      font-weight: 500; 
      transition: all 0.15s;
    }
    .tab-btn.active { background: #00a884; color: #ffffff; font-weight: 600; }

    #chat-list, #search-results-list { flex: 1; overflow-y: auto; list-style: none; }
    .chat-item, .search-item { 
      display: flex; 
      align-items: center; 
      padding: 10px 16px; 
      cursor: pointer; 
      border-bottom: 1px solid #f5f6f6; 
      transition: background 0.15s; 
    }
    .chat-item:hover, .search-item:hover { background: #f5f6f6; }
    .chat-item.active { background: #f0f2f5; border-left: 4px solid #00a884; }
    
    .chat-avatar { 
      width: 46px; 
      height: 46px; 
      border-radius: 50%; 
      display: flex; 
      align-items: center; 
      justify-content: center; 
      font-weight: 600; 
      color: #ffffff; 
      margin-right: 12px; 
      flex-shrink: 0; 
      font-size: 17px;
    }
    .chat-info { flex: 1; overflow: hidden; }
    .chat-header-row { display: flex; justify-content: space-between; align-items: baseline; }
    .chat-name { font-size: 15px; font-weight: 600; color: #111b21; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .chat-time { font-size: 11px; color: #8696a0; flex-shrink: 0; margin-left: 6px; }
    .chat-preview { font-size: 13.5px; color: #667781; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 3px; }

    /* Resultados Búsqueda FTS5 */
    .search-item { flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 16px; }
    .search-chat-title { font-size: 12.5px; color: #00a884; font-weight: 600; }
    .search-snippet { font-size: 14px; color: #111b21; line-height: 19px; }
    .search-snippet mark { background-color: #ffe082; padding: 1px 3px; border-radius: 2px; font-weight: 600; }
    .search-date { font-size: 11px; color: #8696a0; align-self: flex-end; }

    /* Panel derecho (Conversación) */
    #main-chat { flex: 1; display: flex; flex-direction: column; background: #efeae2; position: relative; }
    #chat-header { 
      height: 60px; 
      background: #f0f2f5; 
      display: flex; 
      align-items: center; 
      justify-content: space-between;
      padding: 0 20px; 
      border-bottom: 1px solid #d1d7db; 
      z-index: 2; 
    }
    .header-left { display: flex; align-items: center; }
    #header-info h3 { font-size: 16px; color: #111b21; font-weight: 600; }
    #header-info p { font-size: 12px; color: #667781; margin-top: 1px; }

    .header-actions { display: flex; align-items: center; gap: 8px; }
    .btn-chat-action {
      border: none;
      background: #ffffff;
      border: 1px solid #d1d7db;
      border-radius: 14px;
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 600;
      color: #111b21;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s;
    }
    .btn-chat-action:hover { background: #f5f6f6; border-color: #00a884; color: #00a884; }

    /* Barra de filtros dentro del chat */
    #chat-filter-bar {
      background: #ffffff;
      border-bottom: 1px solid #e9edef;
      padding: 6px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      gap: 10px;
      z-index: 1;
    }
    .filter-pills { display: flex; gap: 6px; }
    .filter-pill {
      border: 1px solid #e9edef;
      background: #f0f2f5;
      padding: 3px 9px;
      border-radius: 12px;
      cursor: pointer;
      color: #54656f;
      font-weight: 500;
      transition: all 0.15s;
    }
    .filter-pill.active { background: #00a884; color: #ffffff; border-color: #00a884; font-weight: 600; }
    .filter-dates { display: flex; align-items: center; gap: 6px; color: #667781; }
    .date-input {
      border: 1px solid #e9edef;
      background: #f0f2f5;
      padding: 3px 6px;
      border-radius: 6px;
      font-size: 11.5px;
      outline: none;
      color: #111b21;
    }
    .date-input:focus { border-color: #00a884; background: #fff; }

    #messages-container { 
      flex: 1; 
      overflow-y: auto; 
      padding: 16px 5%; 
      display: flex; 
      flex-direction: column; 
      gap: 4px; 
    }

    /* Burbujas de chat */
    .date-badge { 
      align-self: center; 
      background: #ffffff; 
      color: #54656f; 
      font-size: 11.5px; 
      font-weight: 500; 
      padding: 5px 12px; 
      border-radius: 7px; 
      box-shadow: 0 1px 0.5px rgba(11,20,26,0.13); 
      margin: 12px 0 6px 0; 
      user-select: none;
    }
    .msg-bubble { 
      max-width: 65%; 
      padding: 6px 9px 6px 9px; 
      border-radius: 7.5px; 
      font-size: 14.2px; 
      line-height: 19px; 
      position: relative; 
      word-wrap: break-word; 
      box-shadow: 0 1px 0.5px rgba(11,20,26,0.13); 
      display: flex; 
      flex-direction: column; 
    }
    .msg-incoming { 
      align-self: flex-start; 
      background: #ffffff; 
      color: #111b21; 
      border-top-left-radius: 0; 
    }
    .msg-outgoing { 
      align-self: flex-end; 
      background: #d9fdd3; 
      color: #111b21; 
      border-top-right-radius: 0; 
    }
    
    .msg-sender { 
      font-size: 12px; 
      font-weight: 600; 
      margin-bottom: 2px; 
    }
    .msg-text { white-space: pre-wrap; font-size: 14.2px; word-break: break-word; }
    .msg-footer { 
      align-self: flex-end; 
      font-size: 10.5px; 
      color: #667781; 
      margin-top: 3px; 
      margin-left: 16px; 
      display: flex; 
      align-items: center; 
      gap: 3px;
    }
    .msg-check { color: #53bdeb; font-size: 12px; font-weight: bold; }

    /* Multimedia */
    .media-container { margin-bottom: 4px; border-radius: 6px; overflow: hidden; }
    .media-img { 
      max-width: 320px; 
      max-height: 320px; 
      object-fit: cover; 
      border-radius: 6px; 
      cursor: pointer; 
      display: block; 
      transition: opacity 0.15s;
    }
    .media-img:hover { opacity: 0.95; }
    
    /* Contenedor de audio con control de velocidad */
    .audio-wrapper {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(0,0,0,0.03);
      padding: 4px 6px;
      border-radius: 8px;
    }
    .media-audio { width: 250px; height: 36px; outline: none; }
    .btn-speed {
      border: 1px solid #d1d7db;
      background: #ffffff;
      border-radius: 10px;
      padding: 3px 6px;
      font-size: 10.5px;
      font-weight: 700;
      color: #54656f;
      cursor: pointer;
      user-select: none;
      transition: all 0.15s;
    }
    .btn-speed:hover { background: #e9edef; color: #111b21; }

    .media-video { max-width: 340px; border-radius: 6px; display: block; }
    .media-doc { 
      display: flex; 
      align-items: center; 
      gap: 10px; 
      padding: 8px 12px; 
      background: rgba(0,0,0,0.04); 
      border-radius: 6px; 
      text-decoration: none; 
      color: #111b21; 
      font-size: 13.5px; 
      transition: background 0.15s; 
    }
    .media-doc:hover { background: rgba(0,0,0,0.08); }
    .media-doc-icon { font-size: 24px; }
    .media-expired {
      font-size: 12px;
      color: #8696a0;
      font-style: italic;
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 3px 0;
    }

    /* Modal Visor Imagen */
    #image-modal { 
      display: none; 
      position: fixed; 
      z-index: 1000; 
      left: 0; 
      top: 0; 
      width: 100vw; 
      height: 100vh; 
      background: rgba(0,0,0,0.85); 
      align-items: center; 
      justify-content: center; 
      cursor: zoom-out; 
    }
    #image-modal img { max-width: 90vw; max-height: 90vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.6); }

    /* Modal de Backups */
    #backup-modal {
      display: none;
      position: fixed;
      z-index: 1000;
      left: 0;
      top: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0,0,0,0.5);
      align-items: center;
      justify-content: center;
    }
    .modal-card {
      background: #ffffff;
      border-radius: 12px;
      width: 480px;
      max-width: 90vw;
      padding: 20px 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .modal-card h3 { font-size: 17px; color: #111b21; }
    .modal-card p { font-size: 13.5px; color: #54656f; line-height: 19px; }
    .backup-list { max-height: 200px; overflow-y: auto; list-style: none; border: 1px solid #e9edef; border-radius: 8px; }
    .backup-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid #f5f6f6; font-size: 12.5px; }
    .backup-item:last-child { border-bottom: none; }
    .modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }
    .btn-modal-cancel { border: 1px solid #d1d7db; background: #fff; padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
    .btn-modal-confirm { border: none; background: #00a884; color: #fff; padding: 6px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }

    /* Estado vacío */
    #empty-state { 
      flex: 1; 
      display: flex; 
      flex-direction: column; 
      align-items: center; 
      justify-content: center; 
      color: #667781; 
      background: #f0f2f5; 
      text-align: center;
      padding: 20px;
    }
    #empty-state h2 { color: #41525d; margin-bottom: 8px; font-weight: 400; font-size: 26px; }
    #empty-state p { font-size: 14px; max-width: 480px; line-height: 20px; }

    /* Notificación Toast */
    #toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #111b21;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 500;
      box-shadow: 0 4px 14px rgba(0,0,0,0.25);
      display: none;
      z-index: 2000;
      animation: fadeIn 0.2s ease;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  </style>
</head>
<body>
  <div id="app-container">
    <!-- Panel izquierdo (Sidebar) -->
    <div id="sidebar">
      <div class="sidebar-header">
        <div class="brand-title">
          <svg width="22" height="22" viewBox="0 0 24 24"><path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-5.46-4.45-9.92-9.91-9.92z"/></svg>
          <span>WhatsApp Backup</span>
        </div>
        <div class="sidebar-actions">
          <button class="btn-header-action" onclick="openBackupModal()" title="Gestionar copias de respaldo de SQLite">💾 Backup</button>
          <div class="sync-badge" id="syncStatusBadge">
            <div class="sync-dot"></div>
            <span id="syncStatusText">Conectado</span>
          </div>
        </div>
      </div>

      <div class="search-section">
        <div class="search-box-wrapper">
          <svg class="search-icon-svg" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
          <input type="text" id="searchInput" class="search-box" placeholder="Buscar un chat o iniciar uno nuevo..." oninput="handleSearchInput()">
        </div>
        <div class="search-mode-tabs">
          <button class="tab-btn active" id="tabChats" onclick="setSearchMode('chats')">Chats</button>
          <button class="tab-btn" id="tabGlobal" onclick="setSearchMode('global')">Búsqueda Global (FTS5)</button>
        </div>
      </div>

      <ul id="chat-list"></ul>
      <ul id="search-results-list" style="display: none;"></ul>
    </div>

    <!-- Panel derecho (Chat) -->
    <div id="main-chat">
      <div id="chat-header" style="display: none;">
        <div class="header-left">
          <div class="chat-avatar" id="headerAvatar"></div>
          <div id="header-info">
            <h3 id="headerTitle">Contacto</h3>
            <p id="headerSub">Identificador</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn-chat-action" onclick="exportCurrentChat()" title="Exportar chat completo a archivo HTML">📥 Exportar Chat</button>
        </div>
      </div>

      <!-- Barra de Filtros del Chat -->
      <div id="chat-filter-bar" style="display: none;">
        <div class="filter-pills">
          <span class="filter-pill active" onclick="setMediaFilter(null, this)">Todos</span>
          <span class="filter-pill" onclick="setMediaFilter('image', this)">📷 Fotos</span>
          <span class="filter-pill" onclick="setMediaFilter('audio', this)">🎤 Audios</span>
          <span class="filter-pill" onclick="setMediaFilter('document', this)">📄 Documentos</span>
          <span class="filter-pill" onclick="setMediaFilter('video', this)">🎬 Videos</span>
        </div>
        <div class="filter-dates">
          <span>Desde:</span>
          <input type="date" id="filterDateFrom" class="date-input" onchange="applyDateFilter()">
          <span>Hasta:</span>
          <input type="date" id="filterDateTo" class="date-input" onchange="applyDateFilter()">
        </div>
      </div>
      
      <div id="messages-container" style="display: none;"></div>

      <div id="empty-state">
        <h2>WhatsApp Business Backup</h2>
        <p>Selecciona una conversación a la izquierda o utiliza el buscador indexado de texto completo.</p>
        <p id="dbStatsText" style="margin-top: 14px; font-size: 13px; color: #8696a0;"></p>
      </div>
    </div>
  </div>

  <!-- Modal Visor Imagen -->
  <div id="image-modal" onclick="this.style.display='none'">
    <img id="modalImg" src="">
  </div>

  <!-- Modal de Gestión de Backups -->
  <div id="backup-modal" onclick="if(event.target===this) closeBackupModal()">
    <div class="modal-card">
      <h3>Copias de Seguridad de Base de Datos</h3>
      <p>Crea copias manuales puntuales de tu archivo SQLite sin interrumpir el funcionamiento del servidor.</p>
      <div class="backup-list" id="backupListContainer">
        <p style="padding: 14px; color: #8696a0; text-align: center;">Cargando respaldos...</p>
      </div>
      <div class="modal-actions">
        <button class="btn-modal-cancel" onclick="closeBackupModal()">Cerrar</button>
        <button class="btn-modal-confirm" onclick="triggerManualBackup()">+ Crear Nuevo Backup</button>
      </div>
    </div>
  </div>

  <div id="toast"></div>

  <script>
    let allChats = [];
    let currentMode = 'chats';
    let searchDebounceTimer = null;
    let selectedChatId = null;
    let activeMediaFilter = null;
    let currentMessages = [];

    const AVATAR_COLORS = [
      '#00a884', '#0284c7', '#7c3aed', '#db2777', 
      '#ea580c', '#16a34a', '#059669', '#4f46e5'
    ];
    const SENDER_COLORS = [
      '#1f7a63', '#1e88e5', '#8e24aa', '#e53935', 
      '#fb8c00', '#00acc1', '#43a047', '#3949ab'
    ];

    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3500);
    }

    function getColorForName(name, palette = AVATAR_COLORS) {
      if (!name) return palette[0];
      let hash = 0;
      for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
      return palette[Math.abs(hash) % palette.length];
    }

    function isBinaryOrBase64(text) {
      if (!text) return false;
      const t = text.trim();
      if (t.startsWith('data:image') || t.includes('/9j/')) return true;
      if (t.length > 40 && !/\\s/.test(t) && /^[-A-Za-z0-9+/=_*&\"'()%:;$^]+$/.test(t)) return true;
      return false;
    }

    function cleanText(text) {
      if (!text) return '';
      if (isBinaryOrBase64(text)) return '';
      return text.replace(/\\ufffd/g, '').replace(/[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]/g, '').trim();
    }

    function formatFriendlyName(name, jid) {
      if (name && !name.endsWith('@c.us') && !name.endsWith('@g.us') && !name.endsWith('@lid') && !name.endsWith('@broadcast')) {
        return name;
      }
      const raw = (name || jid || '').split('@')[0];
      if (/^549\\d{10}$/.test(raw)) {
        return `+54 9 ${raw.substring(3, 6)} ${raw.substring(6, 9)}-${raw.substring(9)}`;
      }
      if (/^\\d{10,}$/.test(raw)) {
        return `+${raw}`;
      }
      return raw || 'Desconocido';
    }

    function formatPreview(lastMsg, lastTipo) {
      const clean = cleanText(lastMsg);
      if (clean) return clean;
      if (lastTipo === 'image') return '📷 Foto';
      if (lastTipo === 'video') return '🎬 Video';
      if (lastTipo === 'ptt') return '🎤 Mensaje de voz';
      if (lastTipo === 'audio') return '🎵 Audio';
      if (lastTipo === 'document') return '📄 Documento';
      if (lastTipo === 'sticker') return '💟 Sticker';
      return 'Sin mensajes';
    }

    async function init() {
      await updateSyncStatus();
      await loadChats();
      setInterval(updateSyncStatus, 15000);
    }

    async function updateSyncStatus() {
      try {
        const res = await fetch('/api/sync/status');
        const data = await res.json();
        document.getElementById('syncStatusText').textContent = `${data.total_messages.toLocaleString()} msgs`;
        document.getElementById('dbStatsText').textContent = 
          `Base de datos: ${data.total_messages.toLocaleString()} mensajes | ${data.total_chats} chats | ${data.downloaded_media || 0} archivos multimedia`;
      } catch (e) {
        document.getElementById('syncStatusText').textContent = 'Desconectado';
      }
    }

    async function loadChats() {
      const res = await fetch('/api/chats');
      allChats = await res.json();
      renderChats(allChats);
    }

    function renderChats(chats) {
      const list = document.getElementById('chat-list');
      list.innerHTML = '';
      chats.forEach(chat => {
        const li = document.createElement('li');
        li.className = 'chat-item' + (chat.chat_id === selectedChatId ? ' active' : '');
        li.id = 'chat-' + btoa(chat.chat_id).replace(/=/g, '');
        li.onclick = () => selectChat(chat);
        
        const friendlyTitle = formatFriendlyName(chat.display_name, chat.chat_id);
        const initial = (friendlyTitle || '?')[0].toUpperCase();
        const avatarBg = getColorForName(friendlyTitle);

        let timeStr = '';
        if (chat.last_ts) {
          const d = new Date(chat.last_ts * 1000);
          timeStr = d.toLocaleDateString() === new Date().toLocaleDateString() 
            ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : d.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
        }

        const previewText = formatPreview(chat.last_msg, chat.last_tipo);

        li.innerHTML = `
          <div class="chat-avatar" style="background-color: ${avatarBg};">${initial}</div>
          <div class="chat-info">
            <div class="chat-header-row">
              <span class="chat-name">${escapeHtml(friendlyTitle)}</span>
              <span class="chat-time">${timeStr}</span>
            </div>
            <div class="chat-preview">${escapeHtml(previewText)}</div>
          </div>
        `;
        list.appendChild(li);
      });
    }

    function setSearchMode(mode) {
      currentMode = mode;
      document.getElementById('tabChats').classList.toggle('active', mode === 'chats');
      document.getElementById('tabGlobal').classList.toggle('active', mode === 'global');
      document.getElementById('searchInput').placeholder = mode === 'chats' ? 'Buscar un chat...' : 'Buscar en todos los mensajes (FTS5)...';
      
      if (mode === 'chats') {
        document.getElementById('chat-list').style.display = 'block';
        document.getElementById('search-results-list').style.display = 'none';
        handleSearchInput();
      } else {
        document.getElementById('chat-list').style.display = 'none';
        document.getElementById('search-results-list').style.display = 'block';
        handleSearchInput();
      }
    }

    function handleSearchInput() {
      const query = document.getElementById('searchInput').value.trim();
      if (currentMode === 'chats') {
        const q = query.toLowerCase();
        const filtered = allChats.filter(c => {
          const name = (c.display_name || '').toLowerCase();
          const id = (c.chat_id || '').toLowerCase();
          const last = (c.last_msg || '').toLowerCase();
          return name.includes(q) || id.includes(q) || last.includes(q);
        });
        renderChats(filtered);
      } else {
        clearTimeout(searchDebounceTimer);
        if (!query) {
          document.getElementById('search-results-list').innerHTML = '<li style="padding: 24px; color: #8696a0; text-align: center;">Escribe una palabra o frase para buscar...</li>';
          return;
        }
        searchDebounceTimer = setTimeout(() => performGlobalSearch(query), 300);
      }
    }

    async function performGlobalSearch(query) {
      const list = document.getElementById('search-results-list');
      list.innerHTML = '<li style="padding: 24px; color: #8696a0; text-align: center;">Buscando en base de datos...</li>';
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const results = await res.json();
        list.innerHTML = '';
        if (results.length === 0) {
          list.innerHTML = '<li style="padding: 24px; color: #8696a0; text-align: center;">No se encontraron mensajes coincidentes.</li>';
          return;
        }
        results.forEach(item => {
          const li = document.createElement('li');
          li.className = 'search-item';
          const title = formatFriendlyName(item.chat_nombre, item.chat_id);
          li.onclick = () => {
            const chat = allChats.find(c => c.chat_id === item.chat_id) || { chat_id: item.chat_id, display_name: title };
            selectChat(chat, item.msg_id);
          };
          li.innerHTML = `
            <div class="search-chat-title">${escapeHtml(title)}</div>
            <div class="search-snippet">${item.snippet || escapeHtml(cleanText(item.contenido || ''))}</div>
            <div class="search-date">${item.fecha_utc || ''}</div>
          `;
          list.appendChild(li);
        });
      } catch (e) {
        list.innerHTML = '<li style="padding: 24px; color: #d32f2f; text-align: center;">Error al realizar la búsqueda.</li>';
      }
    }

    async function selectChat(chat, scrollToMsgId = null) {
      selectedChatId = chat.chat_id;
      activeMediaFilter = null;
      document.querySelectorAll('.filter-pill').forEach((el, idx) => el.classList.toggle('active', idx === 0));
      document.getElementById('filterDateFrom').value = '';
      document.getElementById('filterDateTo').value = '';

      document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
      const activeEl = document.getElementById('chat-' + btoa(chat.chat_id).replace(/=/g, ''));
      if (activeEl) activeEl.classList.add('active');

      document.getElementById('empty-state').style.display = 'none';
      document.getElementById('chat-header').style.display = 'flex';
      document.getElementById('chat-filter-bar').style.display = 'flex';
      document.getElementById('messages-container').style.display = 'flex';

      const friendlyTitle = formatFriendlyName(chat.display_name, chat.chat_id);
      document.getElementById('headerTitle').textContent = friendlyTitle;
      
      const isGroup = chat.chat_id.endsWith('@g.us');
      document.getElementById('headerSub').textContent = isGroup 
        ? 'Grupo de WhatsApp' 
        : (chat.chat_id.endsWith('@c.us') ? formatFriendlyName(null, chat.chat_id) : 'Conversación directa');
      
      const avatarEl = document.getElementById('headerAvatar');
      avatarEl.textContent = (friendlyTitle || '?')[0].toUpperCase();
      avatarEl.style.backgroundColor = getColorForName(friendlyTitle);

      const container = document.getElementById('messages-container');
      container.innerHTML = '<p style="text-align: center; color: #667781; margin-top: 24px;">Cargando mensajes...</p>';

      const res = await fetch(`/api/messages?chat_id=${encodeURIComponent(chat.chat_id)}`);
      currentMessages = await res.json();
      
      renderMessages(currentMessages, scrollToMsgId);
    }

    function renderMessages(messages, scrollToMsgId = null) {
      const container = document.getElementById('messages-container');
      container.innerHTML = '';
      let lastDate = null;
      const isGroup = selectedChatId && selectedChatId.endsWith('@g.us');

      if (messages.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #8696a0; margin-top: 30px;">No hay mensajes coincidentes con los filtros.</p>';
        return;
      }

      messages.forEach(m => {
        const msgDate = m.fecha_utc ? m.fecha_utc.split(' ')[0] : 'Desconocida';
        if (msgDate !== lastDate) {
          const dateDiv = document.createElement('div');
          dateDiv.className = 'date-badge';
          dateDiv.textContent = msgDate;
          container.appendChild(dateDiv);
          lastDate = msgDate;
        }

        const isMine = Boolean(m.es_mio) || (m.msg_id && m.msg_id.startsWith('true_'));

        const bubble = document.createElement('div');
        bubble.className = `msg-bubble ${isMine ? 'msg-outgoing' : 'msg-incoming'}`;
        if (m.msg_id) bubble.id = 'msg-' + btoa(m.msg_id).replace(/=/g, '');

        let senderHtml = '';
        if (isGroup && !isMine) {
          const senderDisplayName = formatFriendlyName(m.remitente_nombre, m.remitente_jid);
          const senderColor = getColorForName(senderDisplayName, SENDER_COLORS);
          senderHtml = `<div class="msg-sender" style="color: ${senderColor};">${escapeHtml(senderDisplayName)}</div>`;
        }

        let mediaHtml = '';
        if (m.archivo_local) {
          if (m.tipo === 'image' || (m.mimetype && m.mimetype.startsWith('image/'))) {
            mediaHtml = `<div class="media-container"><img class="media-img" src="/${m.archivo_local}" onclick="openModal(this.src)" loading="lazy"></div>`;
          } else if (m.tipo === 'audio' || m.tipo === 'ptt' || (m.mimetype && m.mimetype.startsWith('audio/'))) {
            mediaHtml = `
              <div class="media-container audio-wrapper">
                <audio class="media-audio" controls src="/${m.archivo_local}" onended="playNextAudio(this)"></audio>
                <button class="btn-speed" onclick="toggleAudioSpeed(this)">1x</button>
              </div>`;
          } else if (m.tipo === 'video' || (m.mimetype && m.mimetype.startsWith('video/'))) {
            mediaHtml = `<div class="media-container"><video class="media-video" controls src="/${m.archivo_local}"></video></div>`;
          } else {
            const fileName = m.archivo_local.split('/').pop();
            mediaHtml = `<div class="media-container"><a class="media-doc" href="/${m.archivo_local}" download><span class="media-doc-icon">📄</span><span>${escapeHtml(fileName)}</span></a></div>`;
          }
        } else if (m.estado_multimedia === 'expirado') {
          mediaHtml = `<div class="media-expired"><span>⚠️</span><span>[Archivo multimedia expirado en servidores de WhatsApp]</span></div>`;
        } else if (m.thumbnail && m.thumbnail.startsWith('data:image')) {
          mediaHtml = `<div class="media-container"><img class="media-img" src="${m.thumbnail}" onclick="openModal(this.src)"></div>`;
        }

        const timeStr = m.fecha_utc ? m.fecha_utc.split(' ')[1].substring(0, 5) : '';
        const checkHtml = isMine ? '<span class="msg-check">✓✓</span>' : '';
        const cleanBody = cleanText(m.contenido);

        bubble.innerHTML = `
          ${senderHtml}
          ${mediaHtml}
          ${cleanBody ? `<div class="msg-text">${escapeHtml(cleanBody)}</div>` : ''}
          <div class="msg-footer">
            <span>${timeStr}</span>
            ${checkHtml}
          </div>
        `;
        container.appendChild(bubble);
      });

      if (scrollToMsgId) {
        const target = document.getElementById('msg-' + btoa(scrollToMsgId).replace(/=/g, ''));
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          target.style.outline = '2px solid #00a884';
          setTimeout(() => target.style.outline = 'none', 2500);
          return;
        }
      }
      container.scrollTop = container.scrollHeight;
    }

    // Filtros multimedia en el chat
    function setMediaFilter(type, el) {
      activeMediaFilter = type;
      document.querySelectorAll('.filter-pill').forEach(pill => pill.classList.remove('active'));
      el.classList.add('active');
      applyClientFilters();
    }

    function applyDateFilter() {
      applyClientFilters();
    }

    function applyClientFilters() {
      const fromVal = document.getElementById('filterDateFrom').value;
      const toVal = document.getElementById('filterDateTo').value;

      let filtered = currentMessages;

      if (activeMediaFilter) {
        if (activeMediaFilter === 'audio') {
          filtered = filtered.filter(m => m.tipo === 'audio' || m.tipo === 'ptt' || (m.mimetype && m.mimetype.startsWith('audio/')));
        } else if (activeMediaFilter === 'image') {
          filtered = filtered.filter(m => m.tipo === 'image' || (m.mimetype && m.mimetype.startsWith('image/')));
        } else if (activeMediaFilter === 'video') {
          filtered = filtered.filter(m => m.tipo === 'video' || (m.mimetype && m.mimetype.startsWith('video/')));
        } else if (activeMediaFilter === 'document') {
          filtered = filtered.filter(m => m.tipo === 'document' || (m.mimetype && !m.mimetype.startsWith('image/') && !m.mimetype.startsWith('audio/') && !m.mimetype.startsWith('video/')));
        }
      }

      if (fromVal) {
        const fromTs = new Date(fromVal + 'T00:00:00').getTime() / 1000;
        filtered = filtered.filter(m => (m.timestamp || 0) >= fromTs);
      }
      if (toVal) {
        const toTs = new Date(toVal + 'T23:59:59').getTime() / 1000;
        filtered = filtered.filter(m => (m.timestamp || 0) <= toTs);
      }

      renderMessages(filtered);
    }

    // Control de velocidad y reproducción continua de audios
    function toggleAudioSpeed(btn) {
      const wrapper = btn.closest('.audio-wrapper');
      const audio = wrapper.querySelector('audio');
      if (!audio) return;

      const speeds = [1, 1.5, 2];
      const current = audio.playbackRate;
      let nextIdx = (speeds.indexOf(current) + 1) % speeds.length;
      audio.playbackRate = speeds[nextIdx];
      btn.textContent = speeds[nextIdx] + 'x';
    }

    function playNextAudio(currentAudio) {
      const allAudios = Array.from(document.querySelectorAll('.media-audio'));
      const idx = allAudios.indexOf(currentAudio);
      if (idx !== -1 && idx + 1 < allAudios.length) {
        const next = allAudios[idx + 1];
        next.currentTime = 0;
        next.play();
        next.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    // Exportación de Chat a HTML
    function exportCurrentChat() {
      if (!selectedChatId) return;
      window.open(`/api/export/html?chat_id=${encodeURIComponent(selectedChatId)}`, '_blank');
    }

    // Gestión de Backups
    async function openBackupModal() {
      const modal = document.getElementById('backup-modal');
      modal.style.display = 'flex';
      await loadBackupList();
    }

    function closeBackupModal() {
      document.getElementById('backup-modal').style.display = 'none';
    }

    async function loadBackupList() {
      const container = document.getElementById('backupListContainer');
      container.innerHTML = '<p style="padding: 14px; color: #8696a0; text-align: center;">Cargando respaldos...</p>';
      try {
        const res = await fetch('/api/backup/list');
        const backups = await res.json();
        if (backups.length === 0) {
          container.innerHTML = '<p style="padding: 14px; color: #8696a0; text-align: center;">No hay copias de seguridad manuales aún.</p>';
          return;
        }
        container.innerHTML = '';
        backups.forEach(b => {
          const div = document.createElement('div');
          div.className = 'backup-item';
          div.innerHTML = `
            <div>
              <strong>${escapeHtml(b.filename)}</strong>
              <div style="color: #8696a0; font-size: 11px;">${b.created_at} · ${b.size_mb} MB</div>
            </div>
            <a href="/api/backup/download?file=${encodeURIComponent(b.filename)}" class="btn-chat-action" style="text-decoration: none;">Descargar</a>
          `;
          container.appendChild(div);
        });
      } catch (e) {
        container.innerHTML = '<p style="padding: 14px; color: #d32f2f; text-align: center;">Error al cargar lista de backups.</p>';
      }
    }

    async function triggerManualBackup() {
      showToast('Creando copia de seguridad consistente de SQLite...');
      try {
        const res = await fetch('/api/backup/create', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast(`¡Backup creado con éxito! (${data.backup.size_mb} MB)`);
          await loadBackupList();
        } else {
          showToast('Error al crear backup: ' + (data.error || 'Desconocido'));
        }
      } catch (e) {
        showToast('Error de conexión al generar backup');
      }
    }

    function openModal(src) {
      const modal = document.getElementById('image-modal');
      document.getElementById('modalImg').src = src;
      modal.style.display = 'flex';
    }

    function escapeHtml(text) {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    init();
  </script>
</body>
</html>
"""

def generate_chat_html_export(chat_id):
    """Genera un archivo HTML autocontenido para imprimir o archivar."""
    conn = db_manager.get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(c.nombre, ct.nombre, ct.push_name, m.chat_id) AS display_name
        FROM (SELECT DISTINCT chat_id FROM mensajes WHERE chat_id = ?) m
        LEFT JOIN chats c ON m.chat_id = c.chat_id
        LEFT JOIN contactos ct ON m.chat_id = ct.contact_id
    """, (chat_id,))
    row = cur.fetchone()
    display_name = row["display_name"] if row else chat_id

    cur.execute("""
        SELECT 
            m.msg_id, m.es_mio, m.fecha_utc, m.timestamp, m.tipo, m.contenido,
            m.archivo_local, m.mimetype,
            COALESCE(ct.nombre, ct.push_name, m.remitente) AS remitente_nombre,
            m.remitente AS remitente_jid
        FROM mensajes m
        LEFT JOIN contactos ct ON m.remitente = ct.contact_id
        WHERE m.chat_id = ?
        ORDER BY m.timestamp ASC
    """, (chat_id,))
    messages = [dict(r) for r in cur.fetchall()]
    conn.close()

    is_group = chat_id.endswith("@g.us")
    
    html_parts = [f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Respaldo: {html.escape(display_name)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; color: #111b21; }}
    .container {{ max-width: 800px; margin: 0 auto; background: #efeae2; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    .header {{ background: #00a884; color: #ffffff; padding: 18px 24px; }}
    .header h1 {{ margin: 0; font-size: 20px; }}
    .header p {{ margin: 4px 0 0 0; font-size: 13px; opacity: 0.9; }}
    .messages {{ padding: 20px; display: flex; flex-direction: column; gap: 6px; }}
    .date-badge {{ align-self: center; background: #ffffff; color: #54656f; font-size: 11px; padding: 4px 12px; border-radius: 6px; margin: 10px 0; }}
    .msg {{ max-width: 70%; padding: 7px 10px; border-radius: 8px; font-size: 14px; line-height: 19px; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13); word-break: break-word; }}
    .incoming {{ align-self: flex-start; background: #ffffff; }}
    .outgoing {{ align-self: flex-end; background: #d9fdd3; }}
    .sender {{ font-size: 12px; font-weight: bold; color: #1f7a63; margin-bottom: 2px; }}
    .time {{ font-size: 10.5px; color: #667781; text-align: right; margin-top: 4px; }}
    .media-img {{ max-width: 300px; border-radius: 6px; display: block; margin-bottom: 4px; }}
    @media print {{ body {{ background: #fff; padding: 0; }} .container {{ box-shadow: none; border-radius: 0; }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{html.escape(display_name)}</h1>
      <p>{len(messages)} mensajes respaldados · Exportado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    <div class="messages">
"""]

    last_date = None
    for m in messages:
        msg_date = m["fecha_utc"].split(" ")[0] if m.get("fecha_utc") else "Fecha desconocida"
        if msg_date != last_date:
            html_parts.append(f'<div class="date-badge">{msg_date}</div>')
            last_date = msg_date

        is_mine = bool(m.get("es_mio")) or (m.get("msg_id", "").startswith("true_"))
        cls = "outgoing" if is_mine else "incoming"
        sender_html = ""
        if is_group and not is_mine:
            name = m["remitente_nombre"] or m["remitente_jid"] or "Desconocido"
            sender_html = f'<div class="sender">{html.escape(name)}</div>'

        media_html = ""
        if m.get("archivo_local"):
            if m.get("tipo") == "image":
                media_html = f'<img class="media-img" src="/{m["archivo_local"]}">'
            elif m.get("tipo") in ("audio", "ptt"):
                media_html = f'<audio controls src="/{m["archivo_local"]}"></audio>'
            else:
                media_html = f'<div>📄 <a href="/{m["archivo_local"]}">{html.escape(m["archivo_local"].split("/")[-1])}</a></div>'

        time_str = m["fecha_utc"].split(" ")[1][:5] if m.get("fecha_utc") else ""
        raw_c = m.get("contenido") or ""
        content_clean = "" if db_manager.is_binary_or_base64_content(m.get("tipo"), raw_c) else raw_c.replace("\ufffd", "").strip()

        html_parts.append(f"""
        <div class="msg {cls}">
          {sender_html}
          {media_html}
          {f'<div>{html.escape(content_clean)}</div>' if content_clean else ''}
          <div class="time">{time_str}</div>
        </div>
        """)

    html_parts.append("""
    </div>
  </div>
</body>
</html>
""")
    return "".join(html_parts)

class BackupServerHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, status_code, data):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        url = urlparse(self.path)

        if url.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_UI.encode("utf-8"))
            return

        elif url.path == "/api/sync/status":
            status = db_manager.get_sync_status()
            self.send_json(200, status)
            return

        elif url.path == "/api/search":
            params = parse_qs(url.query)
            q = params.get("q", [""])[0]
            chat_id = params.get("chat_id", [None])[0]
            results = db_manager.search_full_text(q, chat_id=chat_id, limit=50)
            self.send_json(200, results)
            return

        elif url.path == "/api/chats":
            conn = db_manager.get_connection()
            cur = conn.cursor()
            query = """
            SELECT 
                m.chat_id,
                COALESCE(c.nombre, ct.nombre, ct.push_name, m.chat_id) AS display_name,
                (SELECT contenido FROM mensajes WHERE chat_id = m.chat_id ORDER BY timestamp DESC LIMIT 1) AS last_msg,
                (SELECT tipo FROM mensajes WHERE chat_id = m.chat_id ORDER BY timestamp DESC LIMIT 1) AS last_tipo,
                (SELECT timestamp FROM mensajes WHERE chat_id = m.chat_id ORDER BY timestamp DESC LIMIT 1) AS last_ts
            FROM (SELECT DISTINCT chat_id FROM mensajes WHERE chat_id IS NOT NULL AND chat_id != 'status@broadcast') m
            LEFT JOIN chats c ON m.chat_id = c.chat_id
            LEFT JOIN contactos ct ON m.chat_id = ct.contact_id
            ORDER BY last_ts DESC
            """
            cur.execute(query)
            chats = [dict(row) for row in cur.fetchall()]
            conn.close()
            self.send_json(200, chats)
            return

        elif url.path == "/api/messages":
            params = parse_qs(url.query)
            chat_id = params.get("chat_id", [None])[0]
            if not chat_id:
                self.send_json(400, {"error": "Falta parámetro chat_id"})
                return

            conn = db_manager.get_connection()
            cur = conn.cursor()
            query = """
            SELECT 
                m.msg_id,
                m.chat_id,
                m.es_mio,
                m.fecha_utc,
                m.timestamp,
                m.tipo,
                m.contenido,
                m.archivo_local,
                m.mimetype,
                m.tamano,
                m.duracion,
                m.thumbnail,
                m.estado_multimedia,
                COALESCE(ct.nombre, ct.push_name, m.remitente) AS remitente_nombre,
                m.remitente AS remitente_jid
            FROM mensajes m
            LEFT JOIN contactos ct ON m.remitente = ct.contact_id
            WHERE m.chat_id = ?
            ORDER BY m.timestamp ASC
            """
            cur.execute(query, (chat_id,))
            messages = [dict(row) for row in cur.fetchall()]
            conn.close()
            self.send_json(200, messages)
            return

        elif url.path == "/api/export/html":
            params = parse_qs(url.query)
            chat_id = params.get("chat_id", [None])[0]
            if not chat_id:
                self.send_json(400, {"error": "Falta parámetro chat_id"})
                return

            html_content = generate_chat_html_export(chat_id)
            html_bytes = html_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="chat_{chat_id.split("@")[0]}.html"')
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
            return

        elif url.path == "/api/backup/list":
            backups = db_manager.list_manual_backups()
            self.send_json(200, backups)
            return

        elif url.path == "/api/backup/download":
            params = parse_qs(url.query)
            filename = os.path.basename(params.get("file", [""])[0])
            filepath = os.path.join("backups", filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(os.path.getsize(filepath)))
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        elif url.path.startswith("/media/"):
            rel_file_path = url.path.lstrip("/").replace("/", os.sep)
            if os.path.exists(rel_file_path) and os.path.isfile(rel_file_path):
                mime, _ = mimetypes.guess_type(rel_file_path)
                mime = mime or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-type", mime)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_cors_headers()
                self.end_headers()
                with open(rel_file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        try:
            url = urlparse(self.path)

            if url.path == "/api/sync":
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self.send_json(400, {"error": "Cuerpo de solicitud vacío"})
                    return

                body = self.rfile.read(content_length)
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception as e:
                    self.send_json(400, {"error": f"JSON inválido: {e}"})
                    return

                stats = db_manager.save_incremental_sync(payload)
                print(f"[Sync] Lote procesado con éxito: {stats}")
                media_manager.trigger_media_processing()

                self.send_json(200, {"success": True, "stats": stats})
                return

            elif url.path == "/api/backup/create":
                backup_info = db_manager.create_manual_backup()
                self.send_json(200, {"success": True, "backup": backup_info})
                return

            elif url.path == "/api/media/process":
                media_manager.trigger_media_processing()
                self.send_json(200, {"status": "en_proceso"})
                return

            self.send_response(404)
            self.end_headers()
        except Exception as e:
            traceback.print_exc()
            self.send_json(500, {"error": str(e)})

    def log_message(self, format, *args):
        return

def run():
    db_manager.init_db()
    media_manager.ensure_media_dirs()

    server = ThreadingHTTPServer(("127.0.0.1", PORT), BackupServerHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"============================================================")
    print(f"  Servidor WhatsApp Backup & Visor iniciado con éxito")
    print(f"  Dirección local: {url}")
    print(f"  API Incremental: {url}/api/sync")
    print(f"  Búsqueda FTS5:  {url}/api/search?q=...")
    print(f"  Presiona Ctrl + C en esta terminal para detener el servidor")
    print(f"============================================================")

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor cerrado correctamente.")
        server.server_close()

if __name__ == "__main__":
    run()