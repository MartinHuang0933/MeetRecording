"""Integration tests for the FastAPI application."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWebhookCallback:
    def test_invalid_signature(self, client):
        """Request with invalid signature returns 400."""
        response = client.post(
            "/callback",
            content='{"events": []}',
            headers={
                "X-Line-Signature": "invalid_signature",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    @patch("app.main.handle_audio_message")
    @patch("app.main.parser")
    @patch("app.main.messaging_api")
    def test_valid_audio_event(self, mock_messaging_api, mock_parser, mock_handler, client):
        """Valid audio event triggers handler."""
        mock_event = MagicMock()
        mock_event.type = "message"
        mock_event.source.user_id = "U_test"
        mock_event.message.type = "audio"
        mock_event.message.id = "msg_test"
        mock_event.reply_token = "reply_token"

        mock_parser.parse.return_value = [mock_event]

        body = '{"events": []}'
        response = client.post(
            "/callback",
            content=body,
            headers={
                "X-Line-Signature": "valid",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    @patch("app.main.handle_audio_message")
    @patch("app.main.parser")
    def test_non_audio_event_ignored(self, mock_parser, mock_handler, client):
        """Non-audio message events are ignored."""
        mock_event = MagicMock()
        mock_event.type = "message"
        mock_event.message.type = "text"
        mock_event.message.file_name = None

        mock_parser.parse.return_value = [mock_event]

        response = client.post(
            "/callback",
            content='{"events": []}',
            headers={
                "X-Line-Signature": "valid",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_handler.assert_not_called()

    @patch("app.main.handle_audio_message")
    @patch("app.main.parser")
    @patch("app.main.messaging_api")
    def test_file_m4a_treated_as_audio(self, mock_messaging_api, mock_parser, mock_handler, client):
        """M4A file shared via LINE file message triggers audio handler."""
        mock_event = MagicMock()
        mock_event.type = "message"
        mock_event.source.user_id = "U_test"
        mock_event.message.type = "file"
        mock_event.message.file_name = "recording.m4a"
        mock_event.message.id = "msg_file"
        mock_event.reply_token = "reply_token"

        mock_parser.parse.return_value = [mock_event]

        response = client.post(
            "/callback",
            content='{"events": []}',
            headers={
                "X-Line-Signature": "valid",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_handler.assert_called_once()

    @patch("app.main.handle_audio_message")
    @patch("app.main.parser")
    def test_file_non_audio_ignored(self, mock_parser, mock_handler, client):
        """Non-audio file (e.g. PDF) is ignored."""
        mock_event = MagicMock()
        mock_event.type = "message"
        mock_event.message.type = "file"
        mock_event.message.file_name = "document.pdf"

        mock_parser.parse.return_value = [mock_event]

        response = client.post(
            "/callback",
            content='{"events": []}',
            headers={
                "X-Line-Signature": "valid",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        mock_handler.assert_not_called()
