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
        transcript="這是一段測試轉錄文字",
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
        transcript="這是一段測試轉錄文字",
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
        transcript="這是一段測試轉錄文字",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key="test-key",
    )

    call_kwargs = mock_client.messages.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    # Now sends plain text prompt (not input_audio blocks)
    content = messages[0]["content"]
    assert isinstance(content, str)
    assert "這是一段測試轉錄文字" in content


@patch("app.summarizer.generate_meeting_notes")
def test_generate_meeting_notes_from_chunks_single(mock_generate):
    mock_generate.return_value = "## 會議摘要\n單一段落內容"

    result = generate_meeting_notes_from_chunks(
        transcripts=["轉錄文字片段一"],
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key="test-key",
    )

    assert result == "## 會議摘要\n單一段落內容"
    mock_generate.assert_called_once()


@patch("app.summarizer._merge_meeting_notes")
@patch("app.summarizer.generate_meeting_notes")
def test_generate_meeting_notes_from_chunks_multiple(mock_generate, mock_merge):
    mock_generate.side_effect = [
        "## 會議摘要\n第一段內容",
        "## 會議摘要\n第二段內容",
    ]
    mock_merge.return_value = "## 會議摘要\n合併後的完整內容"

    result = generate_meeting_notes_from_chunks(
        transcripts=["轉錄文字片段一", "轉錄文字片段二"],
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
