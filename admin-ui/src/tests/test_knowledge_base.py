"""Tests for knowledge base CRUD functions with mocked psycopg2."""
import uuid
from unittest import mock

import pytest


class TestFetchKnowledgeBase:
    """fetch_knowledge_base with active_only filtering and ordering."""

    @mock.patch("components.database.get_connection")
    def test_fetch_knowledge_base_active_only_filters_rows(self, mock_get_conn):
        """fetch_knowledge_base(active_only=True) should filter with is_active=true."""
        from components.database import fetch_knowledge_base

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": str(uuid.uuid4()), "pregunta": "¿Cuál es el horario?",
             "respuesta": "Lunes a viernes 9-6pm", "categoria": "horarios",
             "is_active": True, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        ]

        result = fetch_knowledge_base(active_only=True)

        sql = mock_cursor.execute.call_args[0][0]
        assert "is_active = true" in sql or "is_active = True" in sql or "is_active" in sql
        assert "WHERE" in sql
        assert len(result) == 1

    @mock.patch("components.database.get_connection")
    def test_fetch_knowledge_base_all_rows_when_not_active_only(self, mock_get_conn):
        """fetch_knowledge_base(active_only=False) should return all rows without is_active filter."""
        from components.database import fetch_knowledge_base

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": str(uuid.uuid4()), "pregunta": "Q1", "respuesta": "R1",
             "categoria": "general", "is_active": True, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
            {"id": str(uuid.uuid4()), "pregunta": "Q2", "respuesta": "R2",
             "categoria": "precios", "is_active": False, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        ]

        result = fetch_knowledge_base(active_only=False)

        sql = mock_cursor.execute.call_args[0][0]
        assert "WHERE" not in sql
        assert len(result) == 2

    @mock.patch("components.database.get_connection")
    def test_fetch_knowledge_base_ordered_by_categoria_then_created_at(self, mock_get_conn):
        """fetch_knowledge_base should ORDER BY categoria, created_at."""
        from components.database import fetch_knowledge_base

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_knowledge_base()

        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY" in sql
        assert "categoria" in sql
        assert "created_at" in sql

    @mock.patch("components.database.get_connection")
    def test_fetch_knowledge_base_returns_list_of_dicts_with_expected_keys(self, mock_get_conn):
        """fetch_knowledge_base should return list of dicts with required keys."""
        from components.database import fetch_knowledge_base

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        expected_row = {
            "id": str(uuid.uuid4()),
            "pregunta": "¿Dónde están ubicados?",
            "respuesta": "Calle Reforma 123",
            "categoria": "ubicacion",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        mock_cursor.fetchall.return_value = [expected_row]

        result = fetch_knowledge_base()

        assert len(result) == 1
        row = result[0]
        for key in ("id", "pregunta", "respuesta", "categoria", "is_active", "created_at", "updated_at"):
            assert key in row


class TestUpsertKnowledgeBaseItem:
    """upsert_knowledge_base_item performs INSERT or UPDATE based on item_id."""

    @mock.patch("components.database.get_connection")
    def test_upsert_with_no_item_id_performs_insert(self, mock_get_conn):
        """upsert_knowledge_base_item(item_id=None, ...) should INSERT and return new row."""
        from components.database import upsert_knowledge_base_item

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        new_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": new_id, "pregunta": "¿Precio de limpieza?", "respuesta": "$500",
            "categoria": "precios", "is_active": True,
            "created_at": "2026-01-01", "updated_at": "2026-01-01",
        }

        result = upsert_knowledge_base_item(
            item_id=None,
            pregunta="¿Precio de limpieza?",
            respuesta="$500",
            categoria="precios",
            is_active=True,
        )

        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO knowledge_base" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["id"] == new_id

    @mock.patch("components.database.get_connection")
    def test_upsert_with_existing_item_id_performs_update(self, mock_get_conn):
        """upsert_knowledge_base_item(item_id=uuid, ...) should UPDATE and return updated row."""
        from components.database import upsert_knowledge_base_item

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        existing_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": existing_id, "pregunta": "¿Precio actualizado?", "respuesta": "$600",
            "categoria": "precios", "is_active": True,
            "created_at": "2026-01-01", "updated_at": "2026-01-02",
        }

        result = upsert_knowledge_base_item(
            item_id=existing_id,
            pregunta="¿Precio actualizado?",
            respuesta="$600",
            categoria="precios",
            is_active=True,
        )

        sql = mock_cursor.execute.call_args[0][0]
        assert "UPDATE knowledge_base" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["id"] == existing_id


class TestDeleteKnowledgeBaseItem:
    """delete_knowledge_base_item removes row by id."""

    @mock.patch("components.database.get_connection")
    def test_delete_knowledge_base_item_executes_delete(self, mock_get_conn):
        """delete_knowledge_base_item should run DELETE query and commit."""
        from components.database import delete_knowledge_base_item

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        item_id = str(uuid.uuid4())
        delete_knowledge_base_item(item_id)

        sql = mock_cursor.execute.call_args[0][0]
        assert "DELETE FROM knowledge_base" in sql
        assert "WHERE id" in sql or "WHERE" in sql
        mock_conn.commit.assert_called_once()

    @mock.patch("components.database.get_connection")
    def test_delete_knowledge_base_item_returns_none(self, mock_get_conn):
        """delete_knowledge_base_item should return None."""
        from components.database import delete_knowledge_base_item

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = delete_knowledge_base_item(str(uuid.uuid4()))
        assert result is None
