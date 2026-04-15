"""Database helper module: PostgreSQL connection and query functions for CRM."""
import os
from collections import defaultdict

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor


def get_connection():
    """Get a PostgreSQL connection using DATABASE_URL env var."""
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


def fetch_patients(
    search: str = "",
    tag_ids: list = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Fetch paginated patients with optional search and tag filter.

    Returns (rows_as_dicts, total_count).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conditions = []
            params = []

            if search and len(search) >= 3:
                conditions.append(
                    "((first_name || ' ' || last_name) ILIKE %s OR phone_normalized ILIKE %s)"
                )
                params.extend([f"%{search}%", f"%{search}%"])
            elif search and search.isdigit():
                conditions.append("phone_normalized LIKE %s")
                params.append(f"%{search}%")

            if tag_ids:
                conditions.append(
                    "id IN (SELECT patient_id FROM patient_tags WHERE tag_id = ANY(%s::uuid[]))"
                )
                params.append(tag_ids)

            where = "WHERE " + " AND ".join(conditions) if conditions else ""

            # Count total
            cur.execute(f"SELECT COUNT(*) AS count FROM patients {where}", params)
            total = cur.fetchone()["count"]

            # Fetch page
            cur.execute(
                f"""
                SELECT p.id, p.first_name, p.last_name, p.phone_normalized,
                       p.email, p.notes, p.source, p.created_at
                FROM patients p {where}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()

            return rows, total
    finally:
        conn.close()


def fetch_existing_phones() -> set[str]:
    """Return set of all phone_normalized values from patients table."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT phone_normalized FROM patients")
            return {row["phone_normalized"] for row in cur.fetchall()}
    finally:
        conn.close()


def insert_patients(patients: list[dict]) -> int:
    """Batch insert patients. Returns count of inserted rows.

    Skips duplicates via ON CONFLICT on phone_normalized.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO patients (first_name, last_name, phone, phone_normalized, source, notes)
                VALUES %s
                ON CONFLICT (phone_normalized) DO NOTHING
            """
            values = [
                (p["first_name"], p["last_name"], p["phone"], p["phone_normalized"], "csv_import", p.get("notes", ""))
                for p in patients
            ]
            execute_values(cur, sql, values)
            inserted = cur.rowcount
        conn.commit()
        return inserted
    finally:
        conn.close()


def fetch_patient_by_id(patient_id: str) -> dict | None:
    """Fetch a single patient by ID. Returns dict or None."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, phone, phone_normalized,
                       email, notes, source
                FROM patients WHERE id = %s
                """,
                (patient_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def insert_patient(
    first_name: str,
    last_name: str,
    phone: str,
    phone_normalized: str,
    email: str = "",
    notes: str = "",
    source: str = "manual",
) -> dict:
    """Insert a single patient. Returns the created patient dict.

    Raises on duplicate phone_normalized (unique constraint).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO patients (first_name, last_name, phone, phone_normalized, email, notes, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, first_name, last_name, phone_normalized
                """,
                (first_name, last_name, phone, phone_normalized, email, notes, source),
            )
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def update_patient(
    patient_id: str,
    first_name: str,
    last_name: str,
    phone: str,
    phone_normalized: str,
    email: str = "",
    notes: str = "",
) -> dict:
    """Update patient data. Returns the updated patient dict."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE patients
                SET first_name = %s, last_name = %s, phone = %s,
                    phone_normalized = %s, email = %s, notes = %s,
                    updated_at = now()
                WHERE id = %s
                RETURNING id, first_name, last_name, phone_normalized
                """,
                (first_name, last_name, phone, phone_normalized, email, notes, patient_id),
            )
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def delete_patients(patient_ids: list[str]) -> int:
    """Delete patients by IDs. Returns count of deleted rows.

    patient_tags cascade is handled by the DB constraint.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM patients WHERE id = ANY(%s::uuid[])",
                (patient_ids,),
            )
            deleted = cur.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def fetch_tags_with_counts() -> list[dict]:
    """Fetch all tags with the count of assigned patients."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.name, t.color, t.created_at,
                       COUNT(pt.patient_id) AS patient_count
                FROM tags t
                LEFT JOIN patient_tags pt ON t.id = pt.tag_id
                GROUP BY t.id
                ORDER BY t.name
            """)
            return cur.fetchall()
    finally:
        conn.close()


def create_tag(name: str, color: str = "#6366f1") -> dict:
    """Create a new tag. Returns the created tag dict."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO tags (name, color) VALUES (%s, %s) RETURNING id, name, color, created_at",
                (name, color),
            )
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def delete_tag(tag_id: str) -> None:
    """Delete a tag. Raises ValueError if tag is assigned to patients (D-08)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) AS count FROM patient_tags WHERE tag_id = %s",
                (tag_id,),
            )
            count = cur.fetchone()["count"]
            if count > 0:
                raise ValueError(
                    f"Esta etiqueta esta asignada a {count} pacientes. "
                    "Elimina las asignaciones primero."
                )
            cur.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
        conn.commit()
    finally:
        conn.close()


def assign_tags_to_patients(patient_ids: list[str], tag_ids: list[str]) -> int:
    """Bulk assign tags to patients. Returns count of new assignments.

    Uses ON CONFLICT DO NOTHING to skip existing assignments.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO patient_tags (patient_id, tag_id)
                VALUES %s
                ON CONFLICT (patient_id, tag_id) DO NOTHING
            """
            values = [
                (pid, tid) for pid in patient_ids for tid in tag_ids
            ]
            execute_values(cur, sql, values)
            assigned = cur.rowcount
        conn.commit()
        return assigned
    finally:
        conn.close()


def fetch_tags_for_patients(patient_ids: list[str]) -> dict[str, list[dict]]:
    """Fetch tags for a list of patients.

    Returns dict mapping patient_id to list of {name, color} dicts.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT pt.patient_id, t.name, t.color
                FROM patient_tags pt
                JOIN tags t ON pt.tag_id = t.id
                WHERE pt.patient_id = ANY(%s::uuid[])
                """,
                (patient_ids,),
            )
            rows = cur.fetchall()

        result = defaultdict(list)
        for row in rows:
            result[str(row["patient_id"])].append(
                {"name": row["name"], "color": row["color"]}
            )
        return dict(result)
    finally:
        conn.close()


def fetch_templates(active_only: bool = True) -> list[dict]:
    """Fetch message templates, optionally filtering to active only."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT id, name, body, variables, category, is_active, created_at
                FROM message_templates
            """
            if active_only:
                sql += " WHERE is_active = true"
            sql += " ORDER BY created_at DESC"
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def insert_template(
    name: str, body: str, variables: list[str], category: str = "general"
) -> dict:
    """Insert a new message template. Returns the created template dict."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO message_templates (name, body, variables, category)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, body, variables, category, created_at
                """,
                (name, body, variables, category),
            )
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def delete_template(template_id: str) -> None:
    """Delete a message template by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM message_templates WHERE id = %s", (template_id,))
        conn.commit()
    finally:
        conn.close()


# === Knowledge Base CRUD ===

def fetch_knowledge_base(active_only: bool = True) -> list[dict]:
    """Fetch knowledge base items, optionally filtering to active only.

    Returns list of dicts ordered by categoria then created_at.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM knowledge_base"
            if active_only:
                sql += " WHERE is_active = true"
            sql += " ORDER BY categoria, created_at"
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def upsert_knowledge_base_item(
    item_id,
    pregunta: str,
    respuesta: str,
    categoria: str,
    is_active: bool = True,
) -> dict:
    """Insert or update a knowledge base item. Returns the saved row.

    If item_id is truthy, performs UPDATE; otherwise performs INSERT.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if item_id:
                sql = """
                    UPDATE knowledge_base
                    SET pregunta = %s, respuesta = %s, categoria = %s, is_active = %s
                    WHERE id = %s
                    RETURNING *
                """
                cur.execute(sql, (pregunta, respuesta, categoria, is_active, item_id))
            else:
                sql = """
                    INSERT INTO knowledge_base (pregunta, respuesta, categoria, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                """
                cur.execute(sql, (pregunta, respuesta, categoria, is_active))
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def delete_knowledge_base_item(item_id: str) -> None:
    """Delete a knowledge base item by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM knowledge_base WHERE id = %s", (item_id,))
        conn.commit()
    finally:
        conn.close()


# === Inbox Query Functions ===

def fetch_conversations(state_filter: str = None) -> list[dict]:
    """Fetch open conversations with optional state filter.

    Returns list of dicts with patient info joined. human_handoff conversations
    sort first (per D-15). Closed conversations excluded unless state_filter is set.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT c.id, c.wa_contact_id, c.state, c.context, c.last_message_at, c.created_at,
                       p.first_name, p.last_name, p.phone_normalized,
                       (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) AS last_message
                FROM conversations c
                LEFT JOIN patients p ON c.patient_id = p.id
            """
            if state_filter:
                sql += " WHERE c.state = %s"
                params = [state_filter]
            else:
                sql += " WHERE c.state != 'closed'"
                params = []
            sql += " ORDER BY CASE WHEN c.state = 'human_handoff' THEN 0 ELSE 1 END, c.last_message_at DESC"
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def fetch_messages_for_conversation(conversation_id: str) -> list[dict]:
    """Fetch all messages for a conversation ordered by created_at ASC."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT id, direction, sender, content, media_url, media_type, wa_message_id, created_at
                FROM messages WHERE conversation_id = %s ORDER BY created_at ASC
            """
            cur.execute(sql, (conversation_id,))
            return cur.fetchall()
    finally:
        conn.close()


def insert_message(
    conversation_id: str,
    direction: str,
    sender: str,
    content: str,
) -> dict:
    """Insert a message and update conversation last_message_at. Returns new row."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                INSERT INTO messages (conversation_id, direction, sender, content)
                VALUES (%s, %s, %s, %s) RETURNING *
            """
            cur.execute(sql, (conversation_id, direction, sender, content))
            result = cur.fetchone()
            cur.execute(
                "UPDATE conversations SET last_message_at = now() WHERE id = %s",
                (conversation_id,),
            )
        conn.commit()
        return result
    finally:
        conn.close()


def update_conversation_state(conversation_id: str, new_state: str) -> dict:
    """Update the state of a conversation. Returns the updated row."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                UPDATE conversations SET state = %s WHERE id = %s
                RETURNING id, state, wa_contact_id, context
            """
            cur.execute(sql, (new_state, conversation_id))
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


def insert_appointment(
    patient_id: str,
    appointment_type: str,
    scheduled_at: str,
    google_event_id: str = None,
    duration_minutes: int = 30,
    notes: str = None,
) -> dict:
    """Insert a new appointment. Returns the created appointment row."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                INSERT INTO appointments (patient_id, appointment_type, scheduled_at, google_event_id, duration_minutes, notes)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """
            cur.execute(sql, (patient_id, appointment_type, scheduled_at, google_event_id, duration_minutes, notes))
            result = cur.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()


# ---------- Campaigns (Phase 5) ----------

def fetch_patients_by_tags(tag_ids: list[str]) -> list[dict]:
    """Fetch DISTINCT patients matching ANY of the given tag UUIDs.

    Returns list of dicts: id, first_name, last_name, phone_normalized.
    Empty tag_ids returns [] without hitting the DB.
    """
    if not tag_ids:
        return []
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT p.id, p.first_name, p.last_name, p.phone_normalized
                FROM patients p
                JOIN patient_tags pt ON p.id = pt.patient_id
                WHERE pt.tag_id = ANY(%s::uuid[])
                ORDER BY p.first_name, p.last_name
                """,
                (tag_ids,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def insert_campaign(
    campaign_name: str,
    template_id: str,
    segment_tags: list[str],
    total_recipients: int,
) -> dict:
    """Insert a new campaign_log row with status='pending'. Returns {id}."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO campaign_log
                    (campaign_name, template_id, segment_tags, total_recipients, status)
                VALUES (%s, %s, %s::uuid[], %s, 'pending')
                RETURNING id
                """,
                (campaign_name, template_id, segment_tags, total_recipients),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    finally:
        conn.close()


def insert_campaign_recipients(campaign_id: str, patient_ids: list[str]) -> int:
    """Batch insert N recipient rows. Returns count inserted."""
    if not patient_ids:
        return 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            values = [(campaign_id, pid) for pid in patient_ids]
            execute_values(
                cur,
                "INSERT INTO campaign_recipients (campaign_id, patient_id) VALUES %s",
                values,
            )
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def fetch_campaign_status(campaign_id: str) -> dict | None:
    """Return campaign progress dict or None.

    Keys: id, campaign_name, sent_count, failed_count, total_recipients, status,
          started_at, completed_at, cancelled_at, created_at.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, campaign_name, sent_count, failed_count, total_recipients,
                       status, started_at, completed_at, cancelled_at, created_at
                FROM campaign_log
                WHERE id = %s
                """,
                (campaign_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def cancel_campaign(campaign_id: str) -> None:
    """Set campaign_log.status='cancelled' and cancelled_at=now()."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE campaign_log
                SET status = 'cancelled', cancelled_at = now()
                WHERE id = %s
                """,
                (campaign_id,),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_campaign_history(limit: int = 50) -> list[dict]:
    """Return all campaigns ordered by created_at DESC with concatenated tag names.

    Each row has: id, campaign_name, segment_tag_names (TEXT), sent_count,
    failed_count, total_recipients, status, created_at.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    cl.id,
                    cl.campaign_name,
                    cl.sent_count,
                    cl.failed_count,
                    cl.total_recipients,
                    cl.status,
                    cl.created_at,
                    COALESCE(
                        (SELECT string_agg(t.name, ', ')
                         FROM tags t
                         WHERE t.id = ANY(cl.segment_tags)),
                        ''
                    ) AS segment_tag_names
                FROM campaign_log cl
                ORDER BY cl.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# =============================================================================
# Social posts (Phase 6 — SOCIAL-01, SOCIAL-03)
# =============================================================================

def insert_social_post(
    caption: str,
    image_url: str,
    platforms: list[str],
    scheduled_at,  # tz-aware datetime
    campaign_id: str | None = None,
) -> dict:
    """Insert a scheduled social post. Returns the inserted row.

    Schema reference: postgres/init/001_schema.sql social_posts table.
    Status starts as 'scheduled' so the n8n dispatcher (Plan 02) picks it up.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO social_posts
                    (caption, image_url, platforms, scheduled_at, status, campaign_id)
                VALUES (%s, %s, %s, %s, 'scheduled', %s)
                RETURNING id, caption, image_url, platforms, scheduled_at, status, campaign_id
                """,
                (caption, image_url, platforms, scheduled_at, campaign_id),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


def fetch_social_posts(limit: int = 100) -> list[dict]:
    """Return scheduled posts ordered by scheduled_at ASC NULLS LAST.

    Used by 8_Publicaciones.py to render the list section (D-09).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, caption, image_url, platforms, scheduled_at,
                       published_at, status, error_message, campaign_id, created_at
                FROM social_posts
                ORDER BY scheduled_at ASC NULLS LAST, created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetch_social_post_by_id(post_id: str) -> dict | None:
    """Fetch a single social post by ID. Returns dict or None."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, caption, image_url, platforms, scheduled_at,
                       published_at, status, error_message, campaign_id
                FROM social_posts
                WHERE id = %s::uuid
                """,
                (post_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def delete_social_post(post_id: str) -> int:
    """Delete a pending social_post. Refuses to touch published/publishing/failed rows.

    Returns the number of rows removed (0 or 1).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM social_posts
                WHERE id = %s::uuid
                  AND status IN ('draft', 'scheduled')
                """,
                (post_id,),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted
    finally:
        conn.close()


# =============================================================================
# Dashboard (Phase 7 — DASH-01, DASH-03)
# =============================================================================

def fetch_dashboard_kpis(days: int = 30) -> dict:
    """Return 4 KPI values for the dashboard (last N days).

    Keys: messages_sent (int), bot_resolution_pct (float 0-100),
          appointments_booked (int), posts_published (int).
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Messages sent (outbound only)
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM messages
                WHERE direction = 'outbound'
                  AND created_at >= now() - interval '1 day' * %s
                """,
                (days,),
            )
            messages_sent = cur.fetchone()["cnt"]

            # Bot resolution %
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE human_handoff = false) AS bot_resolved,
                    COUNT(*) AS total
                FROM conversations
                WHERE created_at >= now() - interval '1 day' * %s
                """,
                (days,),
            )
            row = cur.fetchone()
            total_convs = row["total"] or 0
            bot_resolved = row["bot_resolved"] or 0
            bot_resolution_pct = (bot_resolved / total_convs * 100) if total_convs > 0 else 0.0

            # Appointments booked
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM appointments
                WHERE status = 'confirmed'
                  AND created_at >= now() - interval '1 day' * %s
                """,
                (days,),
            )
            appointments_booked = cur.fetchone()["cnt"]

            # Posts published
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM social_posts
                WHERE status = 'published'
                  AND created_at >= now() - interval '1 day' * %s
                """,
                (days,),
            )
            posts_published = cur.fetchone()["cnt"]

        return {
            "messages_sent": int(messages_sent),
            "bot_resolution_pct": round(float(bot_resolution_pct), 1),
            "appointments_booked": int(appointments_booked),
            "posts_published": int(posts_published),
        }
    finally:
        conn.close()


def fetch_activity_chart_data(days: int = 7) -> list[dict]:
    """Return daily activity for the last N days (two series).

    Returns list of dicts ordered by date ASC. Each dict:
    { date: date, messages_sent: int, appointments: int }
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    gs.day::date AS date,
                    COALESCE(m.cnt, 0) AS messages_sent,
                    COALESCE(a.cnt, 0) AS appointments
                FROM generate_series(
                    (now() - interval '1 day' * (%s - 1))::date,
                    now()::date,
                    '1 day'::interval
                ) AS gs(day)
                LEFT JOIN (
                    SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                    FROM messages
                    WHERE direction = 'outbound'
                      AND created_at >= now() - interval '1 day' * %s
                    GROUP BY DATE(created_at)
                ) m ON m.day = gs.day::date
                LEFT JOIN (
                    SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                    FROM appointments
                    WHERE status = 'confirmed'
                      AND created_at >= now() - interval '1 day' * %s
                    GROUP BY DATE(created_at)
                ) a ON a.day = gs.day::date
                ORDER BY gs.day ASC
                """,
                (days, days, days),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetch_workflow_errors(limit: int = 20) -> list[dict]:
    """Return the most recent N workflow errors for the error log table.

    Returns list of dicts ordered by created_at DESC. Each dict:
    { id, workflow_name, node_name, error_message, created_at }
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, workflow_name, node_name, error_message, created_at
                FROM workflow_errors
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# =============================================================================
# Campaign delivery analytics (Phase 7 — DASH-02)
# =============================================================================

def fetch_campaign_delivery_analytics(days: int = 30, limit: int = 10) -> list[dict]:
    """Return per-campaign delivery analytics for the last N days.

    Returns list of dicts ordered by created_at DESC (most recent first).
    Each dict:
    {
        id: UUID,
        campaign_name: str,
        segment_tag_names: str,
        created_at: datetime,
        total_recipients: int,
        sent: int,
        delivered: int,
        read: int,
        failed: int,
    }

    Status funnel logic (cumulative, not exclusive buckets):
    - sent      = recipients who got past pending (status IN sent, delivered, read)
    - delivered = subset of sent confirmed delivered by Evolution API webhook
    - read      = subset of delivered who opened the message
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    cl.id,
                    cl.campaign_name,
                    cl.created_at,
                    cl.total_recipients,
                    COALESCE(
                        (SELECT string_agg(t.name, ', ')
                         FROM tags t WHERE t.id = ANY(cl.segment_tags)),
                        '—'
                    ) AS segment_tag_names,
                    COUNT(cr.id) FILTER (WHERE cr.status IN ('sent','delivered','read')) AS sent,
                    COUNT(cr.id) FILTER (WHERE cr.status IN ('delivered','read'))        AS delivered,
                    COUNT(cr.id) FILTER (WHERE cr.status = 'read')                       AS read,
                    COUNT(cr.id) FILTER (WHERE cr.status = 'failed')                     AS failed
                FROM campaign_log cl
                LEFT JOIN campaign_recipients cr ON cr.campaign_id = cl.id
                WHERE cl.created_at >= now() - interval '1 day' * %s
                  AND cl.status IN ('completed', 'in_progress', 'cancelled')
                GROUP BY cl.id
                ORDER BY cl.created_at DESC
                LIMIT %s
                """,
                (days, limit),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
