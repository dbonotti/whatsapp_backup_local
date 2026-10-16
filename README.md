# WhatsApp Backup Local & Incremental (Edición Limpia y Portable)

Sistema de respaldo pasivo, incremental y 100% seguro para WhatsApp Web. Permite archivar conversaciones completas, contactos y archivos multimedia (fotos, audios, notas de voz, videos y documentos descifrados localmente) en una base de datos local SQLite con motor de búsqueda indexada (FTS5) y un visor web moderno inspirado en WhatsApp Web.

> **Seguridad y Cero Riesgo de Suspensión:**  
> A diferencia de librerías no oficiales (como Baileys o WA-JS) o bots que emulan clics en pantalla, este sistema **no envía peticiones de red sospechosas ni manipula el DOM**. Funciona de manera puramente pasiva leyendo el almacenamiento local estándar del navegador (`IndexedDB`) e interceptando de forma transparente las claves criptográficas temporales del cliente (`WebCrypto`).

---

## 📁 Estructura del Proyecto

```text
whatsapp_backup_clean/
├── extension/                       # Extensión para el navegador (Manifest V3)
│   ├── manifest.json
│   ├── rules.json                   # Reglas declarativas de red (omisión de CSP)
│   ├── background.js                # Service worker puente hacia el servidor local
│   ├── bridge.js                    # Conector seguro entre contextos de página
│   └── content.js                   # Extractor pasivo incremental y widget visual
├── whatsapp_viewer.py               # Servidor local HTTP, API y visor web interactivo
├── db_manager.py                    # Gestor de base de datos SQLite (WAL mode, FTS5)
├── media_manager.py                 # Descifrador de multimedia (HKDF-SHA256 + AES-256-CBC)
├── clean_database.py                # Utilidad de optimización y mantenimiento
├── whatsapp_backup_sync.user.js     # Versión alternativa en userscript (Tampermonkey)
├── iniciar_visor.bat                # Lanzador del servidor con consola en Windows
├── iniciar_visor_segundo_plano.vbs  # Lanzador silencioso en segundo plano (sin ventana)
├── instalar_dependencias.bat        # Instalador automático de librerías de Python
├── requirements.txt                 # Dependencias mínimas del sistema
└── README.md                        # Esta guía de uso
```

---

## 🚀 Requisitos Previos

1. **Python 3.8 o superior** instalado en el equipo (marcar la casilla *"Add Python to PATH"* durante la instalación).
2. **Navegador basado en Chromium**: Google Chrome, Microsoft Edge, Brave u Opera.

---

## 🛠️ Puesta en Marcha en un Equipo Nuevo o Nueva Cuenta

### Paso 1: Instalar dependencias
Haz doble clic en **`instalar_dependencias.bat`**  
*(O ejecuta en la terminal: `pip install -r requirements.txt`)*

### Paso 2: Cargar la extensión en el navegador
1. Abre tu navegador y dirígete a:
   - En Google Chrome: `chrome://extensions/`
   - En Microsoft Edge: `edge://extensions/`
   - En Brave: `brave://extensions/`
2. Activa el interruptor **"Modo de desarrollador"** (Developer mode) en la esquina superior derecha.
3. Haz clic en el botón **"Cargar descomprimida"** (Load unpacked).
4. Selecciona la carpeta **`extension`** dentro de este proyecto.

### Paso 3: Iniciar el servidor y visor local
Haz doble clic en **`iniciar_visor.bat`** (o en **`iniciar_visor_segundo_plano.vbs`** si prefieres que no quede una ventana abierta).
- Se abrirá automáticamente tu navegador en: [http://127.0.0.1:8080](http://127.0.0.1:8080).

### Paso 4: Abrir WhatsApp Web
1. Ingresa a [https://web.whatsapp.com](https://web.whatsapp.com) e inicia sesión con cualquier cuenta de WhatsApp vinculando el código QR.
2. Observarás un widget flotante en la esquina inferior derecha: **"Backup WhatsApp"**.
3. Abre cualquier conversación para que la extensión capture la clave criptográfica de la sesión (`🎯 ¡Clave maestra verificada!`).
4. Haz clic en:
   - **`[Todo (Media)]`**: Para realizar la primera sincronización completa del historial y encolar la descarga y descifrado de imágenes, audios y documentos.
   - **`[Novedades]`**: Para sincronizar únicamente los mensajes y novedades de la última hora.
   *(La extensión también realiza sincronizaciones automáticas periódicas cada 10 minutos de forma desatendida)*.

---

## ✨ Características Principales

- **Visor Web Réplica WhatsApp**: Interfaz limpia, avatares dinámicos con paleta de colores, marcas de tiempo, estados de lectura `✓✓` y burbujas diferenciadas (verde claro para mensajes enviados por ti a la derecha, blanco para recibidos a la izquierda).
- **Descifrado Multimedia Real**: Descarga archivos `.enc` de los CDN oficiales de WhatsApp y los descifra localmente mediante HKDF-SHA256 y AES-256-CBC, organizándolos en `media/images/`, `media/audio/`, `media/documents/`, etc.
- **Reproductor de Voz Avanzado**: Selector de velocidad (`1x` ➔ `1.5x` ➔ `2x`) y reproducción continua automática al finalizar una nota de voz.
- **Filtros Dinámicos**: Píldoras para filtrar por tipo (`📷 Fotos`, `🎤 Audios`, `📄 Documentos`, `🎬 Videos`) y selectores de fecha (`Desde` / `Hasta`).
- **Búsqueda Instantánea FTS5**: Motor de texto completo en SQLite con soporte para acentos y diacríticos (`remove_diacritics 1`).
- **Exportación a HTML Autónomo**: Botón para descargar cualquier conversación en un único archivo `.html` estilizado para compartir, archivar o imprimir (`Ctrl + P`).
- **Copias de Seguridad Manuales Consistentes**: Botón en la cabecera para generar un respaldo puntual de la base de datos SQLite en `backups/` mediante la API nativa `sqlite3.Connection.backup()`.
