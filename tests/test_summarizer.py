import os
import tempfile

import pytest
from unittest.mock import MagicMock, patch, Mock

from app.summarizer import (
    generate_meeting_notes,
    generate_meeting_notes_from_chunks,
    _merge_meeting_notes,
)


@patch("app.summarizer.anthropic.Anthropic")
def test_generate_meeting_notes_success(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [Mock(type="text", text="## 會議摘要\n測試內容")]
    mock_client.messages.create.return_value = mock_response

    result = generate_meeting_notes(
        audio_data=b"fake_audio",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key="test-key",
    )

    assert "## 會議摘要" in result
    assert "測試內容" in result
    mock_anthropic_cls.assert_called_once_with(api_key="test-key")
    mock_client.messages.create.assert_called_once()


@patch("app.summarizer.anthropic.Anthropic")
def test_generate_meeting_notes_empty_response(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = []
    mock_client.messages.create.return_value = mock_response

    result = generate_meeting_notes(
        audio_data=b"fake_audio",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key="test-key",
    )

    assert result == "無法生成會議記錄。"


@patch("app.summarizer.anthropic.Anthropic")
def test_generate_meeting_notes_prompt_structure(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [Mock(type="text", text="notes")]
    mock_client.messages.create.return_value = mock_response

    generate_meeting_notes(
        audio_data=b"fake_audio",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key="test-key",
    )

    call_kwargs = mock_client.messages.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]

    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    content_blocks = messages[0]["content"]
    assert len(content_blocks) == 2
    assert content_blocks[0]["type"] == "input_audio"
    assert content_blocks[0]["source"]["type"] == "base64"
    assert content_blocks[0]["source"]["media_type"] == "audio/mp4"
    assert content_blocks[1]["type"] == "text"


@patch("app.summarizer.generate_meeting_notes")
def test_generate_meeting_notes_from_chunks_single(mock_generate):
    mock_generate.return_value = "## 會議摘要\n單一段落內容"

    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
        f.write(b"fake_audio_chunk")
        chunk_path = f.name

    try:
        result = generate_meeting_notes_from_chunks(
            chunk_paths=[chunk_path],
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            api_key="test-key",
        )

        assert result == "## 會議摘要\n單一段落內容"
        mock_generate.assert_called_once()
    finally:
        os.unlink(chunk_path)


@patch("app.summarizer._merge_meeting_notes")
@patch("app.summarizer.generate_meeting_notes")
def test_generate_meeting_notes_from_chunks_multiple(mock_generate, mock_merge):
    mock_generate.side_effect = [
        "## 會議摘要\n第一段內容",
        "## 會議摘要\n第二段內容",
    ]
    mock_merge.return_value = "## 會議摘要\n合併後的完整內容"

    chunk_paths = []
    try:
        for i in range(2):
            with tempfile.NamedTemporaryFile(
                suffix=".m4a", delete=False
            ) as f:
                f.write(f"fake_audio_chunk_{i}".encode())
                chunk_paths.append(f.name)

        result = generate_meeting_notes_from_chunks(
            chunk_paths=chunk_paths,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            api_key="test-key",
        )

        assert mock_generate.call_count == 2
        mock_merge.assert_called_once_with(
            ["## 會議摘要\n第一段內容", "## 會議摘要\n第二段內容"],
            "claude-sonnet-4-20250514",
            4096,
            "test-key",
        )
        assert result == "## 會議摘要\n合併後的完整內容"
    finally:
        for path in chunk_paths:
            os.unlink(path)
