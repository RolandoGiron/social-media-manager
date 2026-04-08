"""Tests for inbox query functions and appointment insert with mocked psycopg2."""
import uuid
from unittest import mock

import pytest


class TestFetchConversations:
    """fetch_conversations with optional state filter and human_handoff ordering."""

    @mock.patch("components.database.get_connection")
    def test_fetch_conversations_returns_all_non_closed(self, mock_get_conn):
        """fetch_conversations() with no filter should return non-closed conversations."""
        from components.database import fetch_conversations

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": str(uuid.uuid4()), "wa_contact_id": "+525512345678",
             "state": "human_handoff", "first_name": "Ana", "last_name": "Lopez",
             "phone_normalized": "+525512345678", "last_message": "Hola", "last_message_at": "2026-01-01"},
        ]

        result = fetch_conversations()

        sql = mock_cursor.execute.call_args[0][0]
        assert "closed" in sql
        assert len(result) == 1

    @mock.patch("components.database.get_connection")
    def test_fetch_conversations_with_state_filter(self, mock_get_conn):
        """fetch_conversations(state_filter='human_handoff') should filter by state."""
        from components.database import fetch_conversations

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": str(uuid.uuid4()), "state": "human_handoff", "wa_contact_id": "+52555"},
        ]

        result = fetch_conversations(state_filter="human_handoff")

        sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        assert "WHERE" in sql and "state" in sql
        assert "human_handoff" in params
        assert len(result) == 1

    @mock.patch("components.database.get_connection")
    def test_fetch_conversations_human_handoff_sorts_first(self, mock_get_conn):
        """fetch_conversations ordering should prioritize human_handoff state (D-15)."""
        from components.database import fetch_conversations

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_conversations()

        sql = mock_cursor.execute.call_args[0][0]
        assert "human_handoff" in sql
        assert "ORDER BY" in sql

    @mock.patch("components.database.get_connection")
    def test_fetch_conversations_joins_patient_name(self, mock_get_conn):
        """fetch_conversations should join with patients to include first_name, last_name."""
        from components.database import fetch_conversations

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        fetch_conversations()

        sql = mock_cursor.execute.call_args[0][0]
        assert "JOIN patients" in sql or "patients" in sql
        assert "first_name" in sql


class TestFetchMessagesForConversation:
    """fetch_messages_for_conversation returns ordered messages."""

    @mock.patch("components.database.get_connection")
    def test_fetch_messages_ordered_by_created_at_asc(self, mock_get_conn):
        """fetch_messages_for_conversation should return messages in ASC order."""
        from components.database import fetch_messages_for_conversation

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [
            {"id": str(uuid.uuid4()), "direction": "inbound", "sender": "patient",
             "content": "Hola", "created_at": "2026-01-01T09:00:00"},
            {"id": str(uuid.uuid4()), "direction": "outbound", "sender": "bot",
             "content": "Bienvenido", "created_at": "2026-01-01T09:01:00"},
        ]

        conversation_id = str(uuid.uuid4())
        result = fetch_messages_for_conversation(conversation_id)

        sql = mock_cursor.execute.call_args[0][0]
        assert "ORDER BY" in sql
        assert "ASC" in sql
        assert "conversation_id" in sql
        assert len(result) == 2


class TestInsertMessage:
    """insert_message inserts and updates conversation last_message_at."""

    @mock.patch("components.database.get_connection")
    def test_insert_message_inserts_and_returns_row(self, mock_get_conn):
        """insert_message should INSERT message and return the new row."""
        from components.database import insert_message

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        msg_id = str(uuid.uuid4())
        conv_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": msg_id, "conversation_id": conv_id,
            "direction": "inbound", "sender": "patient",
            "content": "Hola", "created_at": "2026-01-01T09:00:00",
        }

        result = insert_message(
            conversation_id=conv_id,
            direction="inbound",
            sender="patient",
            content="Hola",
        )

        calls = mock_cursor.execute.call_args_list
        assert len(calls) >= 2  # INSERT + UPDATE last_message_at
        insert_sql = calls[0][0][0]
        assert "INSERT INTO messages" in insert_sql
        assert "RETURNING" in insert_sql
        mock_conn.commit.assert_called_once()
        assert result["id"] == msg_id

    @mock.patch("components.database.get_connection")
    def test_insert_message_updates_conversation_last_message_at(self, mock_get_conn):
        """insert_message should also update conversations.last_message_at."""
        from components.database import insert_message

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": str(uuid.uuid4()), "content": "test"}

        conv_id = str(uuid.uuid4())
        insert_message(conv_id, "outbound", "agent", "Hola paciente")

        calls = mock_cursor.execute.call_args_list
        sql_calls = [c[0][0] for c in calls]
        assert any("UPDATE conversations" in s and "last_message_at" in s for s in sql_calls)


class TestUpdateConversationState:
    """update_conversation_state updates the state column."""

    @mock.patch("components.database.get_connection")
    def test_update_conversation_state_returns_updated_row(self, mock_get_conn):
        """update_conversation_state should UPDATE state and return the updated row."""
        from components.database import update_conversation_state

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        conv_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": conv_id, "state": "human_handoff",
            "wa_contact_id": "+52555", "context": {},
        }

        result = update_conversation_state(conv_id, "human_handoff")

        sql = mock_cursor.execute.call_args[0][0]
        assert "UPDATE conversations" in sql
        assert "state" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["state"] == "human_handoff"


class TestInsertAppointment:
    """insert_appointment inserts a new appointment and returns the row."""

    @mock.patch("components.database.get_connection")
    def test_insert_appointment_inserts_and_returns_row(self, mock_get_conn):
        """insert_appointment should INSERT into appointments and RETURNING *."""
        from components.database import insert_appointment

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)

        appt_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": appt_id, "patient_id": patient_id,
            "appointment_type": "limpieza_facial",
            "scheduled_at": "2026-02-01T10:00:00",
            "duration_minutes": 30,
            "status": "confirmed",
            "google_event_id": "evt123",
            "notes": None,
            "created_at": "2026-01-15",
        }

        result = insert_appointment(
            patient_id=patient_id,
            appointment_type="limpieza_facial",
            scheduled_at="2026-02-01T10:00:00",
            google_event_id="evt123",
            duration_minutes=30,
        )

        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO appointments" in sql
        assert "RETURNING" in sql
        mock_conn.commit.assert_called_once()
        assert result["id"] == appt_id

    @mock.patch("components.database.get_connection")
    def test_insert_appointment_accepts_optional_params(self, mock_get_conn):
        """insert_appointment should work with minimal params (google_event_id defaults to None)."""
        from components.database import insert_appointment

        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mock.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": str(uuid.uuid4()), "status": "confirmed"}

        patient_id = str(uuid.uuid4())
        result = insert_appointment(
            patient_id=patient_id,
            appointment_type="revision_general",
            scheduled_at="2026-02-15T11:00:00",
        )

        mock_conn.commit.assert_called_once()
        assert result is not None
