"""Tests for pipeline module."""

from unittest.mock import MagicMock, patch, Mock

from app.pipeline import process_audio_pipeline


@patch("app.pipeline.send_text_to_user")
@patch("app.pipeline.generate_meeting_notes")
@patch("app.pipeline.split_audio_if_needed")
@patch("app.pipeline.validate_audio")
@patch("app.pipeline.download_audio")
@patch("app.pipeline.MessagingApiBlob")
@patch("app.pipeline.MessagingApi")
@patch("app.pipeline.ApiClient")
@patch("app.pipeline.Configuration")
@patch("app.pipeline.get_settings")
def test_pipeline_full_success(
    mock_settings, mock_config, mock_api_client, mock_messaging_api,
    mock_blob_api, mock_download, mock_validate, mock_split,
    mock_generate, mock_send
):
    """Full pipeline succeeds: download → validate → generate → send."""
    settings = MagicMock()
    settings.line_channel_access_token = "token"
    settings.max_audio_size_mb = 100
    settings.claude_model = "claude-sonnet-4-5-20250929"
    settings.claude_max_tokens = 4096
    settings.anthropic_api_key = "key"
    mock_settings.return_value = settings

    mock_download.return_value = b"audio_data"
    mock_split.return_value = ["/tmp/audio.m4a"]
    mock_generate.return_value = "## 會議摘要\n測試結果"

    process_audio_pipeline("U_user", "msg_123")

    mock_download.assert_called_once()
    mock_validate.assert_called_once_with(b"audio_data", 100)
    mock_generate.assert_called_once()
    mock_send.assert_called_once_with("U_user", "## 會議摘要\n測試結果", mock_messaging_api.return_value)


@patch("app.pipeline.send_text_to_user")
@patch("app.pipeline.generate_meeting_notes")
@patch("app.pipeline.split_audio_if_needed")
@patch("app.pipeline.validate_audio")
@patch("app.pipeline.download_audio")
@patch("app.pipeline.MessagingApiBlob")
@patch("app.pipeline.MessagingApi")
@patch("app.pipeline.ApiClient")
@patch("app.pipeline.Configuration")
@patch("app.pipeline.get_settings")
def test_pipeline_empty_result(
    mock_settings, mock_config, mock_api_client, mock_messaging_api,
    mock_blob_api, mock_download, mock_validate, mock_split,
    mock_generate, mock_send
):
    """Pipeline handles empty result from Claude."""
    settings = MagicMock()
    settings.line_channel_access_token = "token"
    settings.max_audio_size_mb = 100
    settings.claude_model = "claude-sonnet-4-5-20250929"
    settings.claude_max_tokens = 4096
    settings.anthropic_api_key = "key"
    mock_settings.return_value = settings

    mock_download.return_value = b"audio_data"
    mock_split.return_value = ["/tmp/audio.m4a"]
    mock_generate.return_value = "無法生成會議記錄。"

    process_audio_pipeline("U_user", "msg_123")

    mock_send.assert_called_once_with("U_user", "無法生成會議記錄。", mock_messaging_api.return_value)


@patch("app.pipeline.send_text_to_user")
@patch("app.pipeline.validate_audio")
@patch("app.pipeline.download_audio")
@patch("app.pipeline.MessagingApiBlob")
@patch("app.pipeline.MessagingApi")
@patch("app.pipeline.ApiClient")
@patch("app.pipeline.Configuration")
@patch("app.pipeline.get_settings")
def test_pipeline_validation_error(
    mock_settings, mock_config, mock_api_client, mock_messaging_api,
    mock_blob_api, mock_download, mock_validate, mock_send
):
    """Pipeline sends error message on validation failure."""
    settings = MagicMock()
    settings.line_channel_access_token = "token"
    settings.max_audio_size_mb = 100
    mock_settings.return_value = settings

    mock_download.return_value = b"audio_data"
    mock_validate.side_effect = ValueError("Audio data is empty")

    process_audio_pipeline("U_user", "msg_123")

    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "音訊處理失敗" in sent_text


@patch("app.pipeline.send_text_to_user")
@patch("app.pipeline.download_audio")
@patch("app.pipeline.MessagingApiBlob")
@patch("app.pipeline.MessagingApi")
@patch("app.pipeline.ApiClient")
@patch("app.pipeline.Configuration")
@patch("app.pipeline.get_settings")
def test_pipeline_unexpected_error(
    mock_settings, mock_config, mock_api_client, mock_messaging_api,
    mock_blob_api, mock_download, mock_send
):
    """Pipeline sends generic error message on unexpected exception."""
    settings = MagicMock()
    settings.line_channel_access_token = "token"
    settings.max_audio_size_mb = 100
    mock_settings.return_value = settings

    mock_download.side_effect = RuntimeError("Network error")

    process_audio_pipeline("U_user", "msg_123")

    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "發生錯誤" in sent_text
