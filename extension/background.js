// Service Worker de la extensión (inmune a la Content Security Policy de WhatsApp Web)
const BACKEND_BASE = "http://127.0.0.1:8080";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "backend_fetch") {
    const url = request.endpoint.startsWith("http") ? request.endpoint : (BACKEND_BASE + request.endpoint);
    const options = request.options || {};

    fetch(url, options)
      .then(async (res) => {
        const text = await res.text();
        let json = null;
        try {
          json = JSON.parse(text);
        } catch (e) {
          json = null;
        }

        sendResponse({
          ok: res.ok,
          status: res.status,
          data: json !== null ? json : text
        });
      })
      .catch((err) => {
        sendResponse({
          ok: false,
          error: err.message || "Error al conectar con el servidor local"
        });
      });

    return true; // Mantiene el canal abierto para la respuesta asíncrona
  }
});
