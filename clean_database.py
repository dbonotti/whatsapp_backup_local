import re
import db_manager
from db_manager import extract_base64_jpeg, is_binary_or_base64_content

def clean_database():
    conn = db_manager.get_connection()
    cur = conn.cursor()

    print("1. Reparando remitentes de mensajes de grupo...")
    cur.execute("SELECT msg_id, chat_id, remitente FROM mensajes WHERE chat_id LIKE '%@g.us'")
    group_msgs = [dict(r) for r in cur.fetchall()]

    sender_updates = []
    for m in group_msgs:
        mid = m["msg_id"]
        chat_id = m["chat_id"]
        current_sender = m["remitente"]

        if not current_sender or current_sender == chat_id or current_sender.endswith("@g.us"):
            parts = mid.split("_")
            if len(parts) >= 4 and ("@c.us" in parts[-1] or "@lid" in parts[-1]):
                real_author = parts[-1]
                sender_updates.append((real_author, mid))

    if sender_updates:
        cur.executemany("UPDATE mensajes SET remitente = ? WHERE msg_id = ?", sender_updates)
        conn.commit()
    print(f"   -> Remitentes de grupo corregidos: {len(sender_updates)}")

    print("2. Limpiando binarios, miniaturas base64 y ruido en mensajes...")
    cur.execute("SELECT msg_id, tipo, contenido, thumbnail FROM mensajes WHERE contenido IS NOT NULL AND contenido != ''")
    all_msgs = [dict(r) for r in cur.fetchall()]

    content_updates = []
    thumbnail_updates = []

    for m in all_msgs:
        mid = m["msg_id"]
        tipo = m["tipo"]
        content = m["contenido"]
        existing_thumb = m["thumbnail"]

        if not content:
            continue

        orig = content
        # Quitar caracteres de reemplazo unicode y de control
        c = content.replace("\ufffd", "")
        c = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', c).strip()

        # Si es un binario o base64 (como las miniaturas JPEG de imágenes y videos)
        if is_binary_or_base64_content(tipo, c):
            # Rescatar miniatura si el mensaje no tenía una
            extracted_thumb = extract_base64_jpeg(c)
            if extracted_thumb and not existing_thumb:
                thumbnail_updates.append((extracted_thumb, mid))
            c = ""
        else:
            c = re.sub(r'^[^\w¿¡"\']+', '', c).strip()

        if c != orig:
            content_updates.append((c, mid))

    if thumbnail_updates:
        for i in range(0, len(thumbnail_updates), 1000):
            cur.executemany("UPDATE mensajes SET thumbnail = ? WHERE msg_id = ?", thumbnail_updates[i:i+1000])
        conn.commit()
    print(f"   -> Miniaturas JPEG rescatadas como thumbnails: {len(thumbnail_updates)}")

    if content_updates:
        for i in range(0, len(content_updates), 1000):
            cur.executemany("UPDATE mensajes SET contenido = ? WHERE msg_id = ?", content_updates[i:i+1000])
        conn.commit()
    print(f"   -> Mensajes con texto/binario limpiado: {len(content_updates)}")

    print("3. Verificando diferenciación de mensajes propios y entrantes (es_mio)...")
    cur.execute("UPDATE mensajes SET es_mio = 1 WHERE msg_id LIKE 'true_%' AND es_mio != 1")
    cur.execute("UPDATE mensajes SET es_mio = 0 WHERE msg_id LIKE 'false_%' AND es_mio != 0")
    conn.commit()

    print("4. Reconstruyendo índice FTS5...")
    cur.execute("DELETE FROM mensajes_fts")
    cur.execute("""
        INSERT INTO mensajes_fts (msg_id, chat_id, contenido, remitente_nombre)
        SELECT 
            m.msg_id, 
            m.chat_id, 
            COALESCE(m.contenido, ''),
            COALESCE(c.nombre, c.push_name, m.remitente, '')
        FROM mensajes m
        LEFT JOIN contactos c ON m.remitente = c.contact_id
        WHERE m.contenido IS NOT NULL AND length(m.contenido) > 0;
    """)

    conn.commit()
    conn.close()
    print("¡Base de datos limpiada y optimizada con éxito!")

if __name__ == "__main__":
    clean_database()
