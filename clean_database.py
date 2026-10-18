import re
from datetime import datetime
import db_manager
from db_manager import extract_base64_jpeg, is_binary_or_base64_content, clean_protobuf_text, build_contact_map, resolve_mentions_in_text

def clean_database():
    conn = db_manager.get_connection()
    cur = conn.cursor()

    print("0. Eliminando notificaciones internas de sistema vacías...")
    cur.execute("""
        DELETE FROM mensajes
        WHERE tipo IN ('e2e_notification', 'notification_template', 'gp2', 'protocol', 'ciphertext', 'biz_content_placeholder')
    """)
    print(f"   -> Notificaciones de sistema eliminadas: {cur.rowcount}")
    cur.execute("UPDATE chats SET nombre = NULL WHERE nombre = chat_id")
    conn.commit()

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

    print("2. Limpiando prefijos Protobuf, menciones @ID, binarios y ajustando zona horaria local...")
    contact_map = build_contact_map(cur)
    cur.execute("SELECT msg_id, tipo, contenido, thumbnail, timestamp, fecha_utc FROM mensajes")
    all_msgs = [dict(r) for r in cur.fetchall()]

    content_updates = []
    thumbnail_updates = []
    date_updates = []

    for m in all_msgs:
        mid = m["msg_id"]
        tipo = m["tipo"]
        content = m["contenido"]
        existing_thumb = m["thumbnail"]
        ts = m["timestamp"]
        fecha_utc = m["fecha_utc"]

        if ts and isinstance(ts, (int, float)):
            try:
                local_dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if local_dt != fecha_utc:
                    date_updates.append((local_dt, mid))
            except Exception:
                pass

        if not content:
            continue

        orig = content
        c = clean_protobuf_text(content)

        # Si es un binario, JID o base64
        if is_binary_or_base64_content(tipo, c):
            extracted_thumb = extract_base64_jpeg(content)
            if extracted_thumb and not existing_thumb:
                thumbnail_updates.append((extracted_thumb, mid))
            c = ""
        else:
            c = resolve_mentions_in_text(c, contact_map)

        if c != orig:
            content_updates.append((c, mid))

    if date_updates:
        for i in range(0, len(date_updates), 1000):
            cur.executemany("UPDATE mensajes SET fecha_utc = ? WHERE msg_id = ?", date_updates[i:i+1000])
        conn.commit()
    print(f"   -> Marcas de tiempo actualizadas a hora local: {len(date_updates)}")

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
