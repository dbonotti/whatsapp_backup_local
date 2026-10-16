// Puente de comunicación entre el contexto de la página (MAIN) y el Background Service Worker
(function() {
  'use strict';

  window.addEventListener("message", (event) => {
    if (event.source !== window || !event.data || event.data.type !== "BACKUPWA_REQ") return;

    const { reqId, endpoint, options } = event.data;

    chrome.runtime.sendMessage({
      action: "backend_fetch",
      endpoint: endpoint,
      options: options
    }, (response) => {
      if (chrome.runtime.lastError) {
        window.postMessage({
          type: "BACKUPWA_RESP",
          reqId: reqId,
          error: chrome.runtime.lastError.message
        }, "*");
      } else {
        window.postMessage({
          type: "BACKUPWA_RESP",
          reqId: reqId,
          response: response
        }, "*");
      }
    });
  });
})();
