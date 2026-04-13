"""Tests for campaign database helper functions (Phase 5).

All tests follow the mock pattern from test_database.py:
- @mock.patch("components.database.get_connection")
- mock_conn / mock_cursor via MagicMock
- Cursor used as context manager (__enter__/__exit__)
"""
from unittest import mock

import pytest


class TestFetchPatientsByTags:
    """fetch_patients_by_tags returns distinct patients matching any of the given tag UUIDs."""

    @mock.patch("components.database.get_connection")
    def test_returns_patients_matching_any_tag(self, mock_get_conn):
        from components.database import fetch_patients_by_tags

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        tag_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        mock_cursor.fetchall.return_value = [
            {"id": "p1", "first_name": "Ana", "last_name": "Lopez", "phone_normalized": "+525512345678"},
            {"id": "p2", "first_name": "Carlos", "last_name": "Garcia", "phone_normalized": "+525587654321"},
            {"id": "p3", "first_name": "Maria", "last_name": "Torres", "phone_normalized": "+525598765432"},
        ]

        result = fetch_patients_by_tags([tag_id])

        assert len(result) == 3
        sql = mock_cursor.execute.call_args[0][0]
        assert "tag_id = ANY(%s::uuid[])" in sql
        assert "JOIN patient_tags" in sql or "JOIN patient_tags" in sql.replace("\n", " ")

    @mock.patch("components.database.get_connection")
    def test_empty_tag_list_returns_empty(self, mock_get_conn):
        from components.database import fetch_patients_by_tags

        result = fetch_patients_by_tags([])

        # Should NOT hit the DB at all — early return guard
        mock_get_conn.assert_not_called()
        assert result == []

    @mock.patch("components.database.get_connection")
    def test_distinct_results(self, mock_get_conn):
        from components.database import fetch_patients_by_tags

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_patients_by_tags(["tag-id-1", "tag-id-2"])

        sql = mock_cursor.execute.call_args[0][0]
        assert "SELECT DISTINCT" in sql


class TestInsertCampaign:
    """insert_campaign creates a campaign_log row with status='pending' and returns {id}."""

    @mock.patch("components.database.get_connection")
    def test_inserts_with_pending_status(self, mock_get_conn):
        from components.database import insert_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        new_id = "c1d2e3f4-0000-0000-0000-000000000001"
        mock_cursor.fetchone.return_value = {"id": new_id}

        result = insert_campaign(
            campaign_name="acné · 12 abr 2026",
            template_id="t1",
            segment_tags=["tag1"],
            total_recipients=10,
        )

        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO campaign_log" in sql
        assert "'pending'" in sql
        assert "RETURNING id" in sql
        assert "id" in result

    @mock.patch("components.database.get_connection")
    def test_passes_segment_tags_as_uuid_array(self, mock_get_conn):
        from components.database import insert_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": "some-id"}

        segment_tags = ["tag-uuid-1", "tag-uuid-2"]
        insert_campaign(
            campaign_name="test",
            template_id="t1",
            segment_tags=segment_tags,
            total_recipients=5,
        )

        params = mock_cursor.execute.call_args[0][1]
        assert segment_tags in params

    @mock.patch("components.database.get_connection")
    def test_total_recipients_stored(self, mock_get_conn):
        from components.database import insert_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": "some-id"}

        insert_campaign(
            campaign_name="test",
            template_id="t1",
            segment_tags=[],
            total_recipients=42,
        )

        params = mock_cursor.execute.call_args[0][1]
        assert 42 in params


class TestInsertCampaignRecipients:
    """insert_campaign_recipients batch inserts recipient rows using execute_values."""

    @mock.patch("components.database.execute_values")
    @mock.patch("components.database.get_connection")
    def test_batch_insert_uses_execute_values(self, mock_get_conn, mock_exec_values):
        from components.database import insert_campaign_recipients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 3
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        insert_campaign_recipients("campaign-id-1", ["p1", "p2", "p3"])

        mock_exec_values.assert_called_once()

    @mock.patch("components.database.execute_values")
    @mock.patch("components.database.get_connection")
    def test_returns_count_inserted(self, mock_get_conn, mock_exec_values):
        from components.database import insert_campaign_recipients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        result = insert_campaign_recipients("campaign-id-1", ["p1", "p2", "p3", "p4", "p5"])

        assert result == 5

    @mock.patch("components.database.execute_values")
    @mock.patch("components.database.get_connection")
    def test_commits_after_insert(self, mock_get_conn, mock_exec_values):
        from components.database import insert_campaign_recipients

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_cursor.rowcount = 2
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        insert_campaign_recipients("campaign-id-1", ["p1", "p2"])

        mock_conn.commit.assert_called()


class TestFetchCampaignStatus:
    """fetch_campaign_status returns progress dict or None for a given campaign_id."""

    @mock.patch("components.database.get_connection")
    def test_returns_status_dict(self, mock_get_conn):
        from components.database import fetch_campaign_status

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {
            "sent_count": 10,
            "failed_count": 2,
            "total_recipients": 50,
            "status": "in_progress",
            "campaign_name": "acné · 12 abr 2026",
        }

        result = fetch_campaign_status("campaign-id-1")

        assert result["sent_count"] == 10
        assert result["failed_count"] == 2
        assert result["total_recipients"] == 50
        assert result["status"] == "in_progress"

    @mock.patch("components.database.get_connection")
    def test_returns_none_when_not_found(self, mock_get_conn):
        from components.database import fetch_campaign_status

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = fetch_campaign_status("nonexistent-campaign-id")

        assert result is None

    @mock.patch("components.database.get_connection")
    def test_select_columns(self, mock_get_conn):
        from components.database import fetch_campaign_status

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        fetch_campaign_status("campaign-id-1")

        sql = mock_cursor.execute.call_args[0][0]
        assert "sent_count" in sql
        assert "failed_count" in sql
        assert "total_recipients" in sql
        assert "status" in sql
        assert "campaign_name" in sql


class TestCancelCampaign:
    """cancel_campaign sets status='cancelled' and cancelled_at=now()."""

    @mock.patch("components.database.get_connection")
    def test_sets_status_cancelled(self, mock_get_conn):
        from components.database import cancel_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        cancel_campaign("campaign-id-1")

        sql = mock_cursor.execute.call_args[0][0]
        assert "UPDATE campaign_log" in sql
        assert "status = 'cancelled'" in sql
        assert "cancelled_at = now()" in sql

    @mock.patch("components.database.get_connection")
    def test_filters_by_id(self, mock_get_conn):
        from components.database import cancel_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        campaign_id = "specific-campaign-uuid"
        cancel_campaign(campaign_id)

        params = mock_cursor.execute.call_args[0][1]
        assert campaign_id in params

    @mock.patch("components.database.get_connection")
    def test_commits(self, mock_get_conn):
        from components.database import cancel_campaign

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        cancel_campaign("campaign-id-1")

        mock_conn.commit.assert_called()


class TestFetchCampaignHistory:
    """fetch_campaign_history returns campaigns ordered by created_at DESC with tag names."""

    @mock.patch("components.database.get_connection")
    def test_orders_by_created_at_desc(self, mock_get_conn):
        from components.database import fetch_campaign_history

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_campaign_history()

        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY" in sql
        assert "created_at DESC" in sql

    @mock.patch("components.database.get_connection")
    def test_joins_to_get_tag_names(self, mock_get_conn):
        from components.database import fetch_campaign_history

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_campaign_history()

        sql = mock_cursor.execute.call_args[0][0]
        # Must reference the tags table either via LEFT JOIN or subquery
        assert "tags" in sql

    @mock.patch("components.database.get_connection")
    def test_returns_list(self, mock_get_conn):
        from components.database import fetch_campaign_history

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": "c1", "campaign_name": "acné · 12 abr 2026", "status": "completed"},
            {"id": "c2", "campaign_name": "VIP · 10 abr 2026", "status": "cancelled"},
            {"id": "c3", "campaign_name": "todos · 08 abr 2026", "status": "in_progress"},
        ]

        result = fetch_campaign_history()

        assert isinstance(result, list)
        assert len(result) == 3
