// ==UserScript==
// @name         WhatsApp Web - Respaldo Local Automático e Incremental
// @namespace    http://tampermonkey.net/
// @version      2.1.0
// @description  Captura pasiva de clave, descifrado local, sincronización incremental y multimedia a SQLite
// @author       dbono
// @match        https://web.whatsapp.com/*
// @icon         https://web.whatsapp.com/favicon.ico
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-start
// ==/UserScript==

(function() {
  'use strict';

  const BACKEND_URL = "http://127.0.0.1:8080";
  const AUTO_SYNC_INTERVAL_MS = 60000;
  const BATCH_SIZE = 500;
  const DECRYPT_CHUNK_SIZE = 50;

  let isSyncing = false;
  let autoSyncTimer = null;
  let verifiedKeyData = null;

  console.log("%c[BackupWA Userscript] Iniciando interceptor pasivo de respaldo local...", "color: #00a884; font-weight: bold; font-size: 13px;");

  async function setupCryptoInterceptor() {
    if (window.__wa_db_verified) {
      verifiedKeyData = window.__wa_db_verified;
      updateWidgetStatus("ready", "Clave activa");
      return;
    }

    const origDecrypt = window.crypto.subtle.decrypt;

    window.crypto.subtle.decrypt = async function(algorithm, key, data) {
      if (!verifiedKeyData && key && key.type === "secret") {
        getSampleEncryptedMessage().then(async (sample) => {
          if (!sample || verifiedKeyData) return;
          try {
            const testAlg = {
              name: algorithm.name || (key.algorithm && key.algorithm.name) || "AES-GCM",
              iv: sample.msgRowOpaqueData.iv
            };
            const testRes = await origDecrypt.call(window.crypto.subtle, testAlg, key, sample.msgRowOpaqueData._data);
            if (testRes && testRes.byteLength > 0) {
              verifiedKeyData = {
                key: key,
                algName: testAlg.name,
                algorithm: algorithm
              };
              window.__wa_db_verified = verifiedKeyData;
              console.log("%c🎯 [BackupWA] ¡Clave maestra de base de datos capturada y verificada!", "color: #10b981; font-weight: bold; font-size: 14px;");
              updateWidgetStatus("ready", "Clave activa");
              triggerSync(true, false);
            }
          } catch (e) {}
        });
      }
      return origDecrypt.apply(this, arguments);
    };
  }

  function getSampleEncryptedMessage() {
    return new Promise((resolve) => {
      try {
        const req = window.indexedDB.open("model-storage");
        req.onerror = () => resolve(null);
        req.onsuccess = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains("message")) {
            db.close();
            return resolve(null);
          }
          const tx = db.transaction("message", "readonly");
          const store = tx.objectStore("message");
          const curReq = store.openCursor(null, "prev");
          curReq.onsuccess = (e) => {
            const cursor = e.target.result;
            if (cursor) {
              const val = cursor.value;
              if (val.msgRowOpaqueData && val.msgRowOpaqueData._data && val.msgRowOpaqueData.iv) {
                db.close();
                return resolve(val);
              }
              cursor.continue();
            } else {
              db.close();
              resolve(null);
            }
          };
          curReq.onerror = () => { db.close(); resolve(null); };
        };
      } catch (err) {
        resolve(null);
      }
    });
  }

  function extractTextFromBuffer(buffer) {
    const bytes = new Uint8Array(buffer);
    const valid = [];
    let cur = [];

    for (let i = 0; i < bytes.length; i++) {
      const b = bytes[i];
      if ((b >= 32 && b <= 126) || b === 9 || b === 10 || b === 13 || (b >= 128 && b <= 255)) {
        cur.push(b);
      } else {
        if (cur.length >= 2) {
          try {
            const s = new TextDecoder("utf-8", { fatal: false }).decode(new Uint8Array(cur)).replace(/\ufffd/g, "").trim();
            if (s.length >= 2 && !/^[0-9a-f]{20,}$/i.test(s) && !/^[A-Za-z0-9+/=]{40,}$/.test(s)) {
              valid.push(s);
            }
          } catch (e) {}
        }
        cur = [];
      }
    }
    if (cur.length >= 2) {
      try {
        const s = new TextDecoder("utf-8", { fatal: false }).decode(new Uint8Array(cur)).replace(/\ufffd/g, "").trim();
        if (s.length >= 2 && !/^[0-9a-f]{20,}$/i.test(s) && !/^[A-Za-z0-9+/=]{40,}$/.test(s)) {
          valid.push(s);
        }
      } catch (e) {}
    }
    if (valid.length === 0) return "";
    valid.sort((a, b) => b.length - a.length);
    return valid[0];
  }

  function bufferToBase64(buf) {
    if (!buf) return null;
    if (typeof buf === "string") return buf;
    const bytes = new Uint8Array(buf.buffer || buf);
    const chunkSize = 0x8000;
    const chunks = [];
    for (let i = 0; i < bytes.byteLength; i += chunkSize) {
      chunks.push(String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize)));
    }
    return window.btoa(chunks.join(""));
  }

  function extractId(val) {
    if (!val) return null;
    if (typeof val === "object") return val._serialized || val.id || String(val);
    return String(val);
  }

  function backendFetch(endpoint, options = {}) {
    return new Promise((resolve, reject) => {
      const url = endpoint.startsWith("http") ? endpoint : (BACKEND_URL + endpoint);

      if (typeof GM_xmlhttpRequest !== "undefined") {
        GM_xmlhttpRequest({
          method: options.method || "GET",
          url: url,
          headers: options.headers || {},
          data: options.body || null,
          onload: (res) => {
            if (res.status >= 200 && res.status < 300) {
              try {
                resolve(JSON.parse(res.responseText));
              } catch (e) {
                resolve(res.responseText);
              }
            } else {
              reject(new Error(`Error HTTP ${res.status}`));
            }
          },
          onerror: () => reject(new Error("Error de conexión al servidor")),
          ontimeout: () => reject(new Error("Tiempo de espera agotado"))
        });
      } else {
        fetch(url, options)
          .then(async res => {
            const text = await res.text();
            try { return JSON.parse(text); } catch (e) { return text; }
          })
          .then(resolve)
          .catch(reject);
      }
    });
  }

  async function triggerSync(isAuto = false, forceAll = false) {
    if (isSyncing) return;
    if (!verifiedKeyData) {
      updateWidgetStatus("waiting", "Abre un chat para activar");
      return;
    }

    isSyncing = true;
    updateWidgetStatus("syncing", forceAll ? "Sincronizando todo..." : "Sincronizando...");

    try {
      let lastTimestamp = 0;
      try {
        const statusData = await backendFetch("/api/sync/status");
        lastTimestamp = statusData.last_timestamp || 0;
      } catch (backendErr) {
        console.warn("[BackupWA] Servidor local no disponible:", backendErr);
        updateWidgetStatus("error", "Servidor local desconectado");
        isSyncing = false;
        return;
      }

      console.log(`[BackupWA] Sincronización iniciada (forceAll=${forceAll}). Último timestamp local: ${lastTimestamp}`);

      const db = await openIndexedDB("model-storage");
      if (!db) {
        updateWidgetStatus("error", "Error al leer IndexedDB");
        isSyncing = false;
        return;
      }

      const rawContacts = await getAllFromStore(db, "contact");
      const rawChats = await getAllFromStore(db, "chat");

      const cleanContacts = rawContacts.map(c => ({
        id: extractId(c.id),
        name: c.name || c.formattedName || null,
        pushname: c.pushname || null,
        number: c.number || null
      }));

      const cleanChats = rawChats.map(ch => ({
        id: extractId(ch.id),
        name: ch.name || ch.formattedTitle || null,
        unreadCount: ch.unreadCount || 0,
        t: ch.t || ch.timestamp || null
      }));

      const minTimestamp = forceAll ? 0 : Math.max(0, lastTimestamp - 3600);
      const rawMessages = await getMessagesSince(db, minTimestamp, forceAll);
      db.close();

      console.log(`[BackupWA] Mensajes candidatos a procesar: ${rawMessages.length}`);

      if (rawMessages.length === 0) {
        await backendFetch("/api/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contacts: cleanContacts, chats: cleanChats, messages: [] })
        });
        const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        console.log("%c[BackupWA] Al día. No hay mensajes nuevos.", "color: #10b981; font-weight: bold;");
        updateWidgetStatus("synced", `Al día (${nowStr})`);
        return;
      }

      const cleanMessages = [];
      for (let i = 0; i < rawMessages.length; i += DECRYPT_CHUNK_SIZE) {
        const chunk = rawMessages.slice(i, i + DECRYPT_CHUNK_SIZE);
        const processedChunk = await Promise.all(chunk.map(async (m) => {
          const isMedia = m.type in { image: 1, video: 1, sticker: 1, ptt: 1, audio: 1, document: 1 };
          const caption = m.caption || "";
          const rawBody = (typeof m.body === 'string') ? m.body : "";

          const isBinaryOrB64 = (s) => {
            if (!s) return false;
            if (s.startsWith('data:image') || s.includes('/9j/')) return true;
            if (s.length > 40 && !/\s/.test(s) && /^[A-Za-z0-9+/=_\-\*\&\"\'\(\)\%\;\:\$\^]+$/.test(s)) return true;
            return false;
          };

          let bodyText = "";
          if (isMedia) {
            if (caption && !isBinaryOrB64(caption)) {
              bodyText = caption;
            } else if (rawBody && !isBinaryOrB64(rawBody)) {
              bodyText = rawBody;
            }
          } else if (m.type === "revoked") {
            bodyText = "🚫 Este mensaje fue eliminado";
          } else {
            bodyText = isBinaryOrB64(rawBody) ? "" : (rawBody || caption);
          }

          // Priorizar el texto en claro ya renderizado; solo descifrar protobuf si está vacío y no es media
          if (!bodyText && !isMedia && m.msgRowOpaqueData && m.msgRowOpaqueData._data && m.msgRowOpaqueData.iv) {
            try {
              const decBuf = await window.crypto.subtle.decrypt(
                { name: verifiedKeyData.algName, iv: m.msgRowOpaqueData.iv },
                verifiedKeyData.key,
                m.msgRowOpaqueData._data
              );
              const decoded = extractTextFromBuffer(decBuf);
              if (decoded && !isBinaryOrB64(decoded)) bodyText = decoded;
            } catch (e) {}
          }

          if (bodyText) {
            bodyText = bodyText.replace(/\ufffd/g, "").replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "").trim();
            if (m.type in { sticker: 1, ptt: 1, audio: 1 } && bodyText.length <= 15 && !bodyText.includes(" ")) {
              bodyText = "";
            }
          }

          const mediaKeyB64 = m.mediaKey ? bufferToBase64(m.mediaKey) : null;
          let thumbnailStr = null;
          if (rawBody && (rawBody.startsWith('data:image') || rawBody.includes('/9j/'))) {
            const idx = rawBody.indexOf('/9j/');
            const b64Clean = idx !== -1 ? rawBody.substring(idx).trim() : rawBody;
            thumbnailStr = b64Clean.startsWith('data:image') ? b64Clean : 'data:image/jpeg;base64,' + b64Clean;
          } else if (m.thumbnail) {
            const tB64 = bufferToBase64(m.thumbnail);
            if (tB64) thumbnailStr = tB64.startsWith('data:image') ? tB64 : 'data:image/jpeg;base64,' + tB64;
          }

          const qMsg = m.quotedMsg || {};
          const quotedMsgId = extractId(m.quotedStanzaID || qMsg.id);
          const quotedAuthor = extractId(m.quotedParticipant || qMsg.author || qMsg.from);
          let quotedBody = qMsg.caption || (typeof qMsg.body === "string" && !isBinaryOrB64(qMsg.body) ? qMsg.body : "") || "";

          return {
            id: extractId(m.id),
            chatId: extractId(m.chatId),
            from: extractId(m.from),
            to: extractId(m.to),
            author: extractId(m.author),
            fromMe: Boolean(m.fromMe || (m.id && m.id.fromMe)),
            type: m.type || "chat",
            timestamp: m.t || m.timestamp || null,
            body: bodyText,
            mediaKey: mediaKeyB64,
            directPath: m.directPath || null,
            mimetype: m.mimetype || null,
            size: m.size || m.fileLength || null,
            duration: m.duration || null,
            filename: m.filename || null,
            thumbnail: thumbnailStr,
            encFilehash: m.encFilehash ? bufferToBase64(m.encFilehash) : null,
            filehash: m.filehash ? bufferToBase64(m.filehash) : null,
            quotedMsgId: quotedMsgId,
            quotedAuthor: quotedAuthor,
            quotedBody: quotedBody
          };
        }));

        cleanMessages.push(...processedChunk);
        if (rawMessages.length > 500 && i % 1000 === 0) {
          updateWidgetStatus("syncing", `Procesando ${i}/${rawMessages.length}...`);
        }
      }

      let totalSaved = 0;
      let totalMediaEnqueued = 0;

      for (let i = 0; i < cleanMessages.length; i += BATCH_SIZE) {
        const batch = cleanMessages.slice(i, i + BATCH_SIZE);
        const payload = {
          contacts: i === 0 ? cleanContacts : [],
          chats: i === 0 ? cleanChats : [],
          messages: batch
        };

        const resJson = await backendFetch("/api/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (resJson && resJson.stats) {
          totalSaved += resJson.stats.messages_saved || batch.length;
          totalMediaEnqueued += resJson.stats.media_enqueued || 0;
        } else {
          totalSaved += batch.length;
        }

        if (cleanMessages.length > BATCH_SIZE) {
          updateWidgetStatus("syncing", `Guardando ${Math.min(i + BATCH_SIZE, cleanMessages.length)}/${cleanMessages.length}...`);
        }
      }

      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      console.log(`%c[BackupWA] Sincronización exitosa: ${totalSaved} mensajes guardados, ${totalMediaEnqueued} multimedia en cola.`, "color: #10b981; font-weight: bold; font-size: 13px;");
      updateWidgetStatus("synced", `Sincronizado ${nowStr} (${totalSaved} msgs)`);

    } catch (err) {
      console.error("[BackupWA] Error durante sincronización:", err);
      updateWidgetStatus("error", "Error de sincronización");
    } finally {
      isSyncing = false;
    }
  }

  function openIndexedDB(dbName) {
    return new Promise((resolve) => {
      try {
        const req = window.indexedDB.open(dbName);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch (e) {
        resolve(null);
      }
    });
  }

  function getAllFromStore(db, storeName) {
    return new Promise((resolve) => {
      try {
        if (!db.objectStoreNames.contains(storeName)) return resolve([]);
        const tx = db.transaction(storeName, "readonly");
        const store = tx.objectStore(storeName);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  }

  function getMessagesSince(db, minTimestamp, forceAll = false) {
    if (forceAll || !minTimestamp || minTimestamp <= 0) {
      return getAllFromStore(db, "message");
    }
    return new Promise((resolve) => {
      try {
        if (!db.objectStoreNames.contains("message")) return resolve([]);
        const tx = db.transaction("message", "readonly");
        const store = tx.objectStore("message");

        if (store.indexNames && store.indexNames.contains("t")) {
          const idx = store.index("t");
          const range = IDBKeyRange.lowerBound(minTimestamp);
          const req = idx.getAll(range);
          req.onsuccess = () => resolve(req.result || []);
          req.onerror = () => getAllFromStore(db, "message").then(all => resolve(all.filter(m => (m.t || m.timestamp || 0) >= minTimestamp)));
          return;
        }

        const results = [];
        const curReq = store.openCursor();
        curReq.onsuccess = (e) => {
          const cursor = e.target.result;
          if (cursor) {
            const val = cursor.value;
            if ((val.t || val.timestamp || 0) >= minTimestamp) {
              results.push(val);
            }
            cursor.continue();
          } else {
            resolve(results);
          }
        };
        curReq.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  }

  function createWidget() {
    if (document.getElementById("backupwa-widget")) return;

    const widget = document.createElement("div");
    widget.id = "backupwa-widget";
    widget.style.cssText = `
      position: fixed;
      bottom: 16px;
      left: 16px;
      z-index: 999999;
      background: #ffffff;
      border: 1px solid #d1d7db;
      border-radius: 20px;
      padding: 5px 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 2px 10px rgba(11,20,26,0.18);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 12px;
      color: #111b21;
      user-select: none;
      transition: all 0.2s ease;
    `;

    widget.innerHTML = `
      <div id="backupwa-dot" style="width: 8px; height: 8px; border-radius: 50%; background: #eab308; flex-shrink: 0;"></div>
      <span id="backupwa-text" style="font-weight: 500;">Iniciando respaldo...</span>
      <button id="backupwa-btn-sync" title="Sincronizar mensajes nuevos o recientes" style="border: none; background: #00a884; color: #fff; border-radius: 12px; padding: 3px 9px; font-size: 11px; font-weight: 600; cursor: pointer;">Novedades</button>
      <button id="backupwa-btn-all" title="Sincronizar todos los mensajes para vincular archivos multimedia (fotos, audios, docs)" style="border: 1px solid #00a884; background: #ffffff; color: #00a884; border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 600; cursor: pointer;">Todo (Media)</button>
    `;

    document.body.appendChild(widget);

    document.getElementById("backupwa-btn-sync").onclick = (e) => {
      e.stopPropagation();
      triggerSync(false, false);
    };

    document.getElementById("backupwa-btn-all").onclick = (e) => {
      e.stopPropagation();
      triggerSync(false, true);
    };
  }

  function updateWidgetStatus(state, message) {
    const dot = document.getElementById("backupwa-dot");
    const text = document.getElementById("backupwa-text");
    if (!dot || !text) return;

    text.textContent = message;

    if (state === "ready" || state === "synced") {
      dot.style.background = "#25d366";
    } else if (state === "syncing") {
      dot.style.background = "#3b82f6";
    } else if (state === "waiting") {
      dot.style.background = "#eab308";
    } else if (state === "error") {
      dot.style.background = "#ef4444";
    }
  }

  function init() {
    setupCryptoInterceptor();

    if (document.body) {
      createWidget();
    } else {
      window.addEventListener("DOMContentLoaded", createWidget);
    }

    if (autoSyncTimer) clearInterval(autoSyncTimer);
    autoSyncTimer = setInterval(() => {
      if (verifiedKeyData) {
        triggerSync(true, false);
      }
    }, AUTO_SYNC_INTERVAL_MS);
  }

  init();

})();
