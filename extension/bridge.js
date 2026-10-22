// Puente de comunicación entre el contexto de la página (MAIN) y el Background Service Worker
(function() {
  'use strict';

  const PAGE_ORIGIN = "https://web.whatsapp.com";

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== PAGE_ORIGIN) return;
    if (!event.data || event.data.type !== "BACKUPWA_REQ") return;

    const { reqId, endpoint, options } = event.data;
    if (typeof reqId !== "string" || typeof endpoint !== "string") return;

    chrome.runtime.sendMessage({
      action: "backend_fetch",
      endpoint: endpoint,
      options: options
    }, (response) => {
      // Responder solo al origen de WhatsApp Web (nunca a "*")
      if (chrome.runtime.lastError) {
        window.postMessage({
          type: "BACKUPWA_RESP",
          reqId: reqId,
          error: chrome.runtime.lastError.message
        }, PAGE_ORIGIN);
      } else {
        window.postMessage({
          type: "BACKUPWA_RESP",
          reqId: reqId,
          response: response
        }, PAGE_ORIGIN);
      }
    });
  });
})();
