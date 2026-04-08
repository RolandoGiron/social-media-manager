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
                       p.source, p.notes, p.created_at
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
                WHERE pt.patient_id = ANY(%s)
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
