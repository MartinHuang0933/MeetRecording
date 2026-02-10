"""Tests for audio_processor module."""

import pytest
from unittest.mock import MagicMock, patch, Mock

from app.audio_processor import download_audio, validate_audio, split_audio_if_needed


class TestDownloadAudio:
    def test_download_audio_success(self):
        """Successful download returns the audio bytes from the response."""
        expected_bytes = b"\x00\xff" * 512
        mock_response = MagicMock()
        mock_response.content = expected_bytes

        mock_blob_api = MagicMock()
        mock_blob_api.get_message_content.return_value = mock_response

        result = download_audio("msg_123", mock_blob_api)

        assert result == expected_bytes
        mock_blob_api.get_message_content.assert_called_once_with("msg_123")

    def test_download_audio_failure(self):
        """Exception from blob API propagates to the caller."""
        mock_blob_api = MagicMock()
        mock_blob_api.get_message_content.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            download_audio("msg_456", mock_blob_api)


class TestValidateAudio:
    def test_validate_audio_success(self):
        """Valid audio data within size limit passes without error."""
        audio_data = b"\x00" * 1024
        validate_audio(audio_data, max_size_mb=1)

    def test_validate_audio_empty(self):
        """Empty bytes raises ValueError with 'empty' in message."""
        with pytest.raises(ValueError, match="(?i)empty"):
            validate_audio(b"", max_size_mb=10)

    def test_validate_audio_too_large(self):
        """Data exceeding max_size_mb raises ValueError about size."""
        # 2 MB of data with a 1 MB limit
        audio_data = b"\x00" * (2 * 1024 * 1024)
        with pytest.raises(ValueError, match="(?i)(size|large)"):
            validate_audio(audio_data, max_size_mb=1)


class TestSplitAudio:
    @patch("app.audio_processor.AudioSegment")
    def test_split_audio_no_split_needed(self, mock_audio_segment_cls):
        """Audio shorter than max returns the original path."""
        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=5 * 60 * 1000)  # 5 minutes
        mock_audio_segment_cls.from_file.return_value = mock_audio

        result = split_audio_if_needed("/tmp/test.m4a", max_chunk_minutes=15)

        assert result == ["/tmp/test.m4a"]
        mock_audio_segment_cls.from_file.assert_called_once_with("/tmp/test.m4a")

    @patch("app.audio_processor.tempfile")
    @patch("app.audio_processor.AudioSegment")
    def test_split_audio_splits_large_file(
        self, mock_audio_segment_cls, mock_tempfile
    ):
        """35-minute audio is split into 3 chunks (15 + 15 + 5)."""
        total_duration_ms = 35 * 60 * 1000
        chunk_duration_ms = 15 * 60 * 1000

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=total_duration_ms)

        # Each slice returns a mock chunk that supports export
        mock_chunk = MagicMock()
        mock_audio.__getitem__ = Mock(return_value=mock_chunk)

        mock_audio_segment_cls.from_file.return_value = mock_audio

        mock_tempfile.mkdtemp.return_value = "/tmp/fake_chunks"

        result = split_audio_if_needed("/tmp/long_audio.m4a", max_chunk_minutes=15)

        # 35 min / 15 min = 2 full chunks + 1 remainder = 3 chunks
        assert len(result) == 3
        assert all(path.startswith("/tmp/fake_chunks/chunk_") for path in result)
        assert all(path.endswith(".m4a") for path in result)

        # Verify export was called for each chunk with format="ipod"
        assert mock_chunk.export.call_count == 3
        for call in mock_chunk.export.call_args_list:
            assert call[1]["format"] == "ipod" or call[0][1] == "ipod"

        # Verify slicing boundaries
        slice_calls = mock_audio.__getitem__.call_args_list
        assert len(slice_calls) == 3

        # First chunk: 0 to 15 min
        assert slice_calls[0][0][0] == slice(0, chunk_duration_ms)
        # Second chunk: 15 min to 30 min
        assert slice_calls[1][0][0] == slice(chunk_duration_ms, 2 * chunk_duration_ms)
        # Third chunk: 30 min to 35 min
        assert slice_calls[2][0][0] == slice(2 * chunk_duration_ms, total_duration_ms)
