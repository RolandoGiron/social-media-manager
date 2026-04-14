"""Tests for database helper module with mocked psycopg2."""
import uuid
from unittest import mock

import pytest


class TestGetConnection:
    """get_connection returns psycopg2 connection using DATABASE_URL."""

    @mock.patch("components.database.psycopg2")
    def test_get_connection(self, mock_psycopg2):
        from components.database import get_connection

        with mock.patch.dict("os.environ", {"DATABASE_URL": "postgresql://test:test@localhost/test"}):
            conn = get_connection()
            mock_psycopg2.connect.assert_called_once_with("postgresql://test:test@localhost/test")
            assert conn == mock_psycopg2.connect.return_value


class TestFetchPatients:
    """fetch_patients with search, tag filtering, and pagination."""

    @mock.patch("components.database.get_connection")
    def test_fetch_patients_no_filter(self, mock_get_conn):
        from components.database import fetch_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        mock_cursor.fetchone.return_value = {"count": 10}
        mock_cursor.fetchall.return_value = [{"id": "abc", "first_name": "Ana"}]

        rows, total = fetch_patients()
        assert total == 10
        assert len(rows) == 1

        # Verify LIMIT/OFFSET in query
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2
        count_sql = calls[0][0][0]
        select_sql = calls[1][0][0]
        assert "COUNT" in count_sql
        assert "LIMIT" in select_sql
        assert "OFFSET" in select_sql

    @mock.patch("components.database.get_connection")
    def test_fetch_patients_with_search(self, mock_get_conn):
        from components.database import fetch_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"count": 5}
        mock_cursor.fetchall.return_value = []

        fetch_patients(search="Ana")
        count_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "ILIKE" in count_sql

    @mock.patch("components.database.get_connection")
    def test_fetch_patients_with_tags(self, mock_get_conn):
        from components.database import fetch_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"count": 3}
        mock_cursor.fetchall.return_value = []

        tag_id = str(uuid.uuid4())
        fetch_patients(tag_ids=[tag_id])
        count_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "patient_tags" in count_sql
        assert "ANY" in count_sql


class TestFetchExistingPhones:
    """fetch_existing_phones returns set of phone_normalized values."""

    @mock.patch("components.database.get_connection")
    def test_fetch_existing_phones(self, mock_get_conn):
        from components.database import fetch_existing_phones

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"phone_normalized": "+525512345678"},
            {"phone_normalized": "+525587654321"},
        ]

        result = fetch_existing_phones()
        assert result == {"+525512345678", "+525587654321"}


class TestInsertPatients:
    """insert_patients uses execute_values with ON CONFLICT."""

    @mock.patch("components.database.execute_values")
    @mock.patch("components.database.get_connection")
    def test_insert_patients(self, mock_get_conn, mock_exec_values):
        from components.database import insert_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 2
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        patients = [
            {"first_name": "Ana", "last_name": "Lopez", "phone": "5512345678", "phone_normalized": "+525512345678"},
            {"first_name": "Carlos", "last_name": "Garcia", "phone": "5587654321", "phone_normalized": "+525587654321"},
        ]
        result = insert_patients(patients)

        # Verify execute_values was called
        mock_exec_values.assert_called_once()
        sql_arg = mock_exec_values.call_args[0][1]
        assert "ON CONFLICT (phone_normalized) DO NOTHING" in sql_arg
        assert result == 2
        mock_conn.commit.assert_called_once()


class TestTagOperations:
    """Tag CRUD: create, fetch with counts, delete blocking."""

    @mock.patch("components.database.get_connection")
    def test_fetch_tags_with_counts(self, mock_get_conn):
        from components.database import fetch_tags_with_counts

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": "t1", "name": "VIP", "color": "#ff0000", "created_at": "2026-01-01", "patient_count": 5}
        ]

        result = fetch_tags_with_counts()
        sql = mock_cursor.execute.call_args[0][0]
        assert "LEFT JOIN patient_tags" in sql
        assert "COUNT" in sql
        assert len(result) == 1

    @mock.patch("components.database.get_connection")
    def test_create_tag(self, mock_get_conn):
        from components.database import create_tag

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": "new-id", "name": "VIP", "color": "#ff0000", "created_at": "2026-01-01"}

        result = create_tag("VIP", "#ff0000")
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO tags" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["name"] == "VIP"

    @mock.patch("components.database.get_connection")
    def test_delete_tag_blocked(self, mock_get_conn):
        from components.database import delete_tag

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"count": 3}

        with pytest.raises(ValueError, match="asignada a"):
            delete_tag("some-tag-id")

    @mock.patch("components.database.get_connection")
    def test_delete_tag_allowed(self, mock_get_conn):
        from components.database import delete_tag

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"count": 0}

        delete_tag("some-tag-id")
        calls = mock_cursor.execute.call_args_list
        delete_sql = calls[1][0][0]
        assert "DELETE FROM tags" in delete_sql
        mock_conn.commit.assert_called_once()


class TestAssignTags:
    """Bulk tag assignment with ON CONFLICT DO NOTHING."""

    @mock.patch("components.database.execute_values")
    @mock.patch("components.database.get_connection")
    def test_assign_tags_to_patients(self, mock_get_conn, mock_exec_values):
        from components.database import assign_tags_to_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 4
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = assign_tags_to_patients(["p1", "p2"], ["t1", "t2"])
        mock_exec_values.assert_called_once()
        sql_arg = mock_exec_values.call_args[0][1]
        assert "ON CONFLICT (patient_id, tag_id) DO NOTHING" in sql_arg
        assert result == 4
        mock_conn.commit.assert_called_once()


class TestFetchTagsForPatients:
    """fetch_tags_for_patients returns dict mapping patient_id to tag list."""

    @mock.patch("components.database.get_connection")
    def test_fetch_tags_for_patients(self, mock_get_conn):
        from components.database import fetch_tags_for_patients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"patient_id": "p1", "name": "VIP", "color": "#ff0000"},
            {"patient_id": "p1", "name": "Nuevo", "color": "#00ff00"},
            {"patient_id": "p2", "name": "VIP", "color": "#ff0000"},
        ]

        result = fetch_tags_for_patients(["p1", "p2"])
        sql = mock_cursor.execute.call_args[0][0]
        assert "patient_tags" in sql
        assert "ANY" in sql
        assert len(result["p1"]) == 2
        assert len(result["p2"]) == 1
        assert result["p1"][0]["name"] == "VIP"


class TestTemplateOperations:
    """Template CRUD operations."""

    @mock.patch("components.database.get_connection")
    def test_fetch_templates(self, mock_get_conn):
        from components.database import fetch_templates

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [{"id": "t1", "name": "Promo"}]

        result = fetch_templates()
        sql = mock_cursor.execute.call_args[0][0]
        assert "message_templates" in sql
        assert len(result) == 1

    @mock.patch("components.database.get_connection")
    def test_insert_template(self, mock_get_conn):
        from components.database import insert_template

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {
            "id": "new-id", "name": "Promo", "body": "Hola {{nombre}}",
            "variables": ["nombre"], "category": "general", "created_at": "2026-01-01"
        }

        result = insert_template("Promo", "Hola {{nombre}}", ["nombre"], "general")
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO message_templates" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["name"] == "Promo"

    @mock.patch("components.database.get_connection")
    def test_delete_template(self, mock_get_conn):
        from components.database import delete_template

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        delete_template("template-id")
        sql = mock_cursor.execute.call_args[0][0]
        assert "DELETE FROM message_templates" in sql
        mock_conn.commit.assert_called_once()


# =============================================================================
# Social posts (Phase 6 — SOCIAL-01, SOCIAL-03)
# =============================================================================

class TestInsertSocialPost:
    """insert_social_post inserts with status='scheduled' and returns a row dict."""

    @mock.patch("components.database.get_connection")
    def test_insert_social_post_executes_insert_with_status_scheduled(self, mock_get_conn):
        from components.database import insert_social_post
        from datetime import datetime, timezone

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        scheduled = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        mock_cursor.fetchone.return_value = {
            "id": "row-id",
            "caption": "Promo verano",
            "image_url": "uploads/abc.jpg",
            "platforms": ["instagram"],
            "scheduled_at": scheduled,
            "status": "scheduled",
            "campaign_id": None,
        }

        result = insert_social_post(
            caption="Promo verano",
            image_url="uploads/abc.jpg",
            platforms=["instagram"],
            scheduled_at=scheduled,
        )

        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO social_posts" in sql
        assert "'scheduled'" in sql
        assert "RETURNING" in sql
        assert result["status"] == "scheduled"
        assert "id" in result
        mock_conn.commit.assert_called_once()

    @mock.patch("components.database.get_connection")
    def test_insert_social_post_passes_campaign_id_when_provided(self, mock_get_conn):
        from components.database import insert_social_post
        from datetime import datetime, timezone

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        scheduled = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        campaign_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": "row-id",
            "caption": "Promo",
            "image_url": "uploads/x.jpg",
            "platforms": ["facebook"],
            "scheduled_at": scheduled,
            "status": "scheduled",
            "campaign_id": campaign_id,
        }

        insert_social_post(
            caption="Promo",
            image_url="uploads/x.jpg",
            platforms=["facebook"],
            scheduled_at=scheduled,
            campaign_id=campaign_id,
        )

        params = mock_cursor.execute.call_args[0][1]
        assert campaign_id in params


class TestFetchSocialPosts:
    """fetch_social_posts orders by scheduled_at ASC NULLS LAST."""

    @mock.patch("components.database.get_connection")
    def test_fetch_social_posts_orders_by_scheduled_at_asc_nulls_last(self, mock_get_conn):
        from components.database import fetch_social_posts

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_social_posts()

        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY scheduled_at ASC NULLS LAST" in sql


class TestFetchSocialPostById:
    """fetch_social_post_by_id returns dict or None."""

    @mock.patch("components.database.get_connection")
    def test_fetch_social_post_by_id_returns_none_when_missing(self, mock_get_conn):
        from components.database import fetch_social_post_by_id

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = fetch_social_post_by_id(str(uuid.uuid4()))
        assert result is None


class TestDeleteSocialPost:
    """delete_social_post only removes draft/scheduled rows."""

    @mock.patch("components.database.get_connection")
    def test_delete_social_post_only_deletes_pending(self, mock_get_conn):
        from components.database import delete_social_post

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.rowcount = 1

        result = delete_social_post(str(uuid.uuid4()))

        sql = mock_cursor.execute.call_args[0][0]
        assert "status IN ('draft', 'scheduled')" in sql
        assert result == 1
        mock_conn.commit.assert_called_once()
