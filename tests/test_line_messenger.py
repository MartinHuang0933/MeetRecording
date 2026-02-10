"""Tests for line_messenger module."""

import pytest
from unittest.mock import MagicMock, call

from app.line_messenger import split_text, send_text_to_user


class TestSplitText:
    def test_split_text_short(self):
        """Text under 5000 chars returns a single-element list."""
        text = "Hello, this is a short message."
        result = split_text(text)
        assert result == [text]

    def test_split_text_by_paragraph(self):
        """Text with paragraph breaks splits at the paragraph boundary."""
        text = "A" * 4000 + "\n\n" + "B" * 4000
        result = split_text(text)
        assert len(result) == 2
        assert result[0] == "A" * 4000 + "\n\n"
        assert result[1] == "B" * 4000

    def test_split_text_by_newline(self):
        """Text with newlines (no paragraph breaks) splits at newline."""
        text = "A" * 4000 + "\n" + "B" * 4000
        result = split_text(text)
        assert len(result) == 2
        assert result[0] == "A" * 4000 + "\n"
        assert result[1] == "B" * 4000

    def test_split_text_by_period(self):
        """Text with '\u3002' (no newlines) splits at the period."""
        text = "A" * 4000 + "\u3002" + "B" * 4000
        result = split_text(text)
        assert len(result) == 2
        assert result[0] == "A" * 4000 + "\u3002"
        assert result[1] == "B" * 4000

    def test_split_text_hard_cut(self):
        """Text with no delimiters hard cuts at max_length."""
        text = "A" * 10000
        result = split_text(text)
        assert len(result) == 2
        assert len(result[0]) == 5000
        assert len(result[1]) == 5000

    def test_split_text_exact_max_length(self):
        """Text exactly at max_length returns a single-element list."""
        text = "A" * 5000
        result = split_text(text)
        assert result == [text]


class TestSendTextToUser:
    def test_send_text_short_message(self):
        """Short text sends a single push with one TextMessage."""
        mock_api = MagicMock()
        send_text_to_user("U_user1", "Hello!", mock_api)

        mock_api.push_message.assert_called_once()
        push_call = mock_api.push_message.call_args
        request = push_call[0][0]
        assert request.to == "U_user1"
        assert len(request.messages) == 1
        assert request.messages[0].text == "Hello!"

    def test_send_text_long_message_with_pages(self):
        """Long text that splits into 3 parts has page numbers appended."""
        mock_api = MagicMock()

        # Create text that will split into 3 parts via paragraph breaks
        text = "A" * 4000 + "\n\n" + "B" * 4000 + "\n\n" + "C" * 4000
        send_text_to_user("U_user2", text, mock_api)

        # All 3 messages fit in one push (< 5 limit)
        mock_api.push_message.assert_called_once()
        request = mock_api.push_message.call_args[0][0]
        assert len(request.messages) == 3
        assert request.messages[0].text.endswith("(1/3)")
        assert request.messages[1].text.endswith("(2/3)")
        assert request.messages[2].text.endswith("(3/3)")

    def test_send_text_batching(self):
        """7 segments are sent in 2 batches: 5 + 2."""
        mock_api = MagicMock()

        # Use split_text with a small max_length to generate 7 segments
        # Build text: 7 segments of 90 chars separated by "\n\n"
        parts = [("X" * 90 + "\n\n") for _ in range(6)] + ["X" * 90]
        text = "".join(parts)

        # Call with a max_length that forces splits at paragraph boundaries
        # Each part is 92 chars (90 + 2 for \n\n), total ~644 chars
        # Use max_length=100 so each paragraph boundary triggers a split
        from app.line_messenger import split_text as st
        segments = st(text, max_length=100)
        assert len(segments) == 7  # Verify our test data produces 7 segments

        # Now test the actual send function by mocking split_text
        from unittest.mock import patch
        with patch("app.line_messenger.split_text", return_value=segments):
            send_text_to_user("U_user3", text, mock_api)

        assert mock_api.push_message.call_count == 2
        # First batch: 5 messages
        first_request = mock_api.push_message.call_args_list[0][0][0]
        assert len(first_request.messages) == 5
        # Second batch: 2 messages
        second_request = mock_api.push_message.call_args_list[1][0][0]
        assert len(second_request.messages) == 2
