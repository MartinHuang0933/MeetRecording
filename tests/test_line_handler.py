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

        reply_func.assert_called_once_with(
            "\ud83c\udf99\ufe0f \u5df2\u6536\u5230\u8a9e\u97f3\u8a0a\u606f\uff0c\u6b63\u5728\u8655\u7406\u4e2d\uff0c\u8acb\u7a0d\u5019..."
        )

    def test_handle_audio_message_adds_background_task(self):
        """Verify background_tasks.add_task is called with the pipeline function."""
        event = self._make_event()
        reply_func = MagicMock()
        background_tasks = MagicMock()

        handle_audio_message(event, reply_func, background_tasks)

        background_tasks.add_task.assert_called_once_with(
            pipeline.process_audio_pipeline, "U123", "msg456"
        )
