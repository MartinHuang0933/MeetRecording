"""Processing pipeline: download → validate → split → Claude → send result."""

import logging
import tempfile
import os

from linebot.v3.messaging import MessagingApi, MessagingApiBlob, ApiClient, Configuration

from app.config import get_settings
from app.audio_processor import download_audio, validate_audio, split_audio_if_needed
from app.summarizer import generate_meeting_notes, generate_meeting_notes_from_chunks
from app.line_messenger import send_text_to_user

logger = logging.getLogger(__name__)


def process_audio_pipeline(user_id: str, message_id: str) -> None:
    """Full audio processing pipeline.

    Downloads audio from LINE, validates it, optionally splits large files,
    sends to Claude for meeting notes generation, and pushes the result
    back to the user via LINE.

    Args:
        user_id: The LINE user ID to send results to.
        message_id: The LINE message ID of the audio to process.
    """
    settings = get_settings()

    configuration = Configuration(access_token=settings.line_channel_access_token)
    api_client = ApiClient(configuration)
    messaging_api = MessagingApi(api_client)
    blob_api = MessagingApiBlob(api_client)

    try:
        logger.info("Starting pipeline for message %s from user %s", message_id, user_id)

        # Step 1: Download audio
        audio_data = download_audio(message_id, blob_api)
        logger.info("Downloaded audio: %d bytes", len(audio_data))

        # Step 2: Validate
        validate_audio(audio_data, settings.max_audio_size_mb)

        # Step 3: Save to temp file, split if needed, generate notes
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = os.path.join(tmp_dir, "audio.m4a")
            with open(audio_path, "wb") as f:
                f.write(audio_data)

            chunk_paths = split_audio_if_needed(audio_path)

            if len(chunk_paths) == 1:
                result = generate_meeting_notes(
                    audio_data,
                    settings.claude_model,
                    settings.claude_max_tokens,
                    settings.anthropic_api_key,
                )
            else:
                result = generate_meeting_notes_from_chunks(
                    chunk_paths,
                    settings.claude_model,
                    settings.claude_max_tokens,
                    settings.anthropic_api_key,
                )

        # Step 4: Send result to user
        send_text_to_user(user_id, result, messaging_api)
        logger.info("Pipeline completed for message %s", message_id)

    except ValueError as e:
        error_msg = f"音訊處理失敗：{e}"
        logger.warning("Validation error for message %s: %s", message_id, e)
        send_text_to_user(user_id, error_msg, messaging_api)

    except Exception as e:
        error_msg = "處理音訊時發生錯誤，請稍後再試。"
        logger.exception("Unexpected error for message %s: %s", message_id, e)
        send_text_to_user(user_id, error_msg, messaging_api)
