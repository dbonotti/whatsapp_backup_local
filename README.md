# WhatsApp Backup Local & Incremental (Edición Limpia y Portable)

Sistema de respaldo pasivo, incremental y 100% seguro para WhatsApp Web. Permite archivar conversaciones completas, contactos y archivos multimedia (fotos, audios, notas de voz, videos y documentos descifrados localmente) en una base de datos local SQLite con motor de búsqueda indexada (FTS5) y un visor web moderno inspirado en WhatsApp Web.

> **Seguridad y Cero Riesgo de Suspensión:**  
> A diferencia de librerías no oficiales (como Baileys o WA-JS) o bots que emulan clics en pantalla, este sistema **no envía peticiones de red sospechosas ni manipula el DOM**. Funciona de manera puramente pasiva leyendo el almacenamiento local estándar del navegador (`IndexedDB`) e interceptando de forma transparente las claves criptográficas temporales del cliente (`WebCrypto`).

---

## 📁 Estructura del Proyecto

```text
whatsapp_backup_local/
├── extension/                       # Extensión para el navegador (Manifest V3)
│   ├── manifest.json
│   ├── background.js                # Service worker puente hacia el servidor local
│   ├── bridge.js                    # Conector seguro entre contextos de página
│   └── content.js                   # Extractor pasivo incremental y widget visual
├── whatsapp_viewer.py               # Servidor local HTTP, panel de control y visor web
├── db_manager.py                    # Gestor de base de datos SQLite (WAL mode, FTS5)
├── media_manager.py                 # Descifrador de multimedia (HKDF-SHA256 + AES-256-CBC)
├── iniciar_visor.bat                # Lanzador con actualizador automático y panel de control
├── ver_logs.bat                     # Visor en vivo de logs de sincronización
├── requirements.txt                 # Dependencias mínimas del sistema (cryptography)
└── README.md                        # Esta guía de uso
```

---

## 🔄 Actualizaciones Seguras en 1 Clic

El sistema incluye un sistema de actualización inteligente diseñado para **garantizar la total preservación de tus datos**:
* **En el Visor (`iniciar_visor.bat`):** Al iniciar, verifica si hay nuevas versiones en GitHub. Si aceptas actualizar, realiza un respaldo preventivo de `whatsapp_backup.db` en la carpeta `backups/` antes de descargar el código. También puedes presionar `[U]` en cualquier momento en el panel de control.
* **En la Extensión (WhatsApp Web):** Si el servidor detecta una versión más reciente en disco, el widget flotante mostrará el botón `🔄 Actualizar a v...`. Al hacer clic, recarga la extensión y la pestaña automáticamente sin necesidad de entrar a la configuración del navegador.
```

---

## 🚀 Requisitos Previos

1. **Python 3.8 o superior** instalado en el equipo (marcar la casilla *"Add Python to PATH"* durante la instalación).
2. **Navegador basado en Chromium**: Google Chrome, Microsoft Edge, Brave u Opera.

---

## 🛠️ Puesta en Marcha (Configuración en 3 Pasos)

### Paso 1: Iniciar el servidor local
Haz doble clic en **`iniciar_visor.bat`**.  
*(En el primer arranque, instalará automáticamente las dependencias necesarias de Python sin pasos manuales).*
- Se abrirá la terminal con el **Panel de Control** y tu navegador en: [http://127.0.0.1:8080](http://127.0.0.1:8080).

### Paso 2: Cargar la extensión en el navegador
1. Abre tu navegador y dirígete a:
   - En Google Chrome: `chrome://extensions/`
   - En Microsoft Edge: `edge://extensions/`
   - En Brave: `brave://extensions/`
2. Activa el interruptor **"Modo de desarrollador"** (Developer mode) en la esquina superior derecha.
3. Haz clic en el botón **"Cargar descomprimida"** (Load unpacked).
4. Selecciona la carpeta **`extension`** dentro de este proyecto *(puedes usar el botón "📋 Copiar ruta" que aparece en el visor web)*.

### Paso 3: Abrir WhatsApp Web
1. Ingresa a [https://web.whatsapp.com](https://web.whatsapp.com) e inicia sesión con cualquier cuenta de WhatsApp vinculando el código QR.
2. Observarás un widget flotante en la esquina inferior izquierda: **"Backup WhatsApp"**.
3. Abre cualquier conversación para que la extensión capture la clave criptográfica de la sesión (`🎯 ¡Clave maestra verificada!`).
4. Haz clic en:
   - **`[Todo (Media)]`**: Para realizar la primera sincronización completa del historial y encolar la descarga y descifrado de imágenes, audios y documentos.
   - **`[Novedades]`**: Para sincronizar únicamente los mensajes y novedades de la última hora.
   *(La extensión también realiza sincronizaciones automáticas periódicas cada 60 segundos de forma desatendida)*.

---

## ✨ Características Principales

- **Visor Web Réplica WhatsApp (Modo Claro y Modo Oscuro)**: Interfaz limpia con soporte nativo para tema oscuro (`🌙`/`☀️`), avatares dinámicos, citas/respuestas (`quotedMsg`) interactivas, estados de lectura `✓✓` y carga progresiva paginada para conversaciones con miles de mensajes.
- **Descifrado Multimedia Real y Streaming HTTP Range (`206 Partial Content`)**: Descarga continua de archivos `.enc` desde la CDN de WhatsApp, descifrado mediante HKDF-SHA256 y AES-256-CBC, y panel de estado (`🎬 Media`) con botón para reintentar descargas fallidas. Permite adelantar y retroceder pistas de audio y video sin esperas.
- **Reproductor de Voz Avanzado**: Selector de velocidad (`1x` ➔ `1.5x` ➔ `2x`) y reproducción continua automática al finalizar una nota de voz.
- **Filtros Dinámicos**: Píldoras para filtrar por tipo (`📷 Fotos`, `🎤 Audios`, `📄 Documentos`, `🎬 Videos`) y selectores de fecha (`Desde` / `Hasta`).
- **Búsqueda Instantánea FTS5**: Motor de texto completo en SQLite con soporte para acentos y diacríticos (`remove_diacritics 1`).
- **Exportación a HTML Ligero o Autónomo**: Botones para exportar cualquier conversación en HTML ligero o en un único archivo `.html` autónomo (`📦 Exportar Autónomo`) con imágenes y audios incrustados en Base64.
- **Copias de Seguridad Manuales Consistentes**: Botón en la cabecera (`💾 Backup`) para generar y descargar respaldos puntuales de la base de datos SQLite en `backups/` mediante `sqlite3.Connection.backup()`.
