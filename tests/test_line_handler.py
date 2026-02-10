"""Tests for line_handler module."""

import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock

from app.line_handler import handle_audio_message
from app import pipeline


class TestHandleAudioMessage:
    def _make_event(self, user_id="U123", message_id="msg456"):
        """Create a mock MessageEvent with the given user_id and message_id."""
        event = MagicMock()
        event.source.user_id = user_id
        event.message.id = message_id
        return event

    def test_handle_audio_message_replies_immediately(self):
        """Verify reply_func is called with the acknowledgement message."""
        event = self._make_event()
        reply_func = MagicMock()
        background_tasks = MagicMock()

        handle_audio_message(event, reply_func, background_tasks)

        reply_func.assert_called_once()
        call_text = reply_func.call_args[0][0]
        assert "已收到語音訊息" in call_text
        assert "處理中" in call_text

    def test_handle_audio_message_adds_background_task(self):
        """Verify background_tasks.add_task is called with the pipeline function."""
        event = self._make_event()
        reply_func = MagicMock()
        background_tasks = MagicMock()

        handle_audio_message(event, reply_func, background_tasks)

        background_tasks.add_task.assert_called_once_with(
            pipeline.process_audio_pipeline, "U123", "msg456"
        )
