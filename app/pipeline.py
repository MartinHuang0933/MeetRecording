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
        logger.info("[PIPELINE] ====== START message_id=%s user_id=%s ======", message_id, user_id)

        # Step 1: Download audio
        logger.info("[PIPELINE] Step 1: Downloading audio...")
        audio_data = download_audio(message_id, blob_api)
        logger.info("[PIPELINE] Step 1: Downloaded %d bytes", len(audio_data))

        # Step 2: Validate
        logger.info("[PIPELINE] Step 2: Validating audio (max=%dMB)...", settings.max_audio_size_mb)
        validate_audio(audio_data, settings.max_audio_size_mb)
        logger.info("[PIPELINE] Step 2: Validation passed")

        # Step 3: Save to temp file, split if needed, generate notes
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = os.path.join(tmp_dir, "audio.m4a")
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            logger.info("[PIPELINE] Step 3: Saved to temp file %s", audio_path)

            logger.info("[PIPELINE] Step 3: Checking if audio needs splitting...")
            chunk_paths = split_audio_if_needed(audio_path)
            logger.info("[PIPELINE] Step 3: Got %d chunk(s)", len(chunk_paths))

            if len(chunk_paths) == 1:
                logger.info("[PIPELINE] Step 4: Sending audio to Claude API (model=%s, max_tokens=%d)...",
                           settings.claude_model, settings.claude_max_tokens)
                result = generate_meeting_notes(
                    audio_data,
                    settings.claude_model,
                    settings.claude_max_tokens,
                    settings.anthropic_api_key,
                )
            else:
                logger.info("[PIPELINE] Step 4: Sending %d chunks to Claude API...", len(chunk_paths))
                result = generate_meeting_notes_from_chunks(
                    chunk_paths,
                    settings.claude_model,
                    settings.claude_max_tokens,
                    settings.anthropic_api_key,
                )

            logger.info("[PIPELINE] Step 4: Claude returned %d chars", len(result))
            logger.debug("[PIPELINE] Step 4: Result preview: %s", result[:200])

        # Step 5: Send result to user
        logger.info("[PIPELINE] Step 5: Sending result to user via LINE push...")
        send_text_to_user(user_id, result, messaging_api)
        logger.info("[PIPELINE] ====== DONE message_id=%s ======", message_id)

    except ValueError as e:
        error_msg = f"音訊處理失敗：{e}"
        logger.warning("[PIPELINE] Validation error for message %s: %s", message_id, e)
        send_text_to_user(user_id, error_msg, messaging_api)

    except Exception as e:
        error_msg = "處理音訊時發生錯誤，請稍後再試。"
        logger.exception("[PIPELINE] Unexpected error for message %s: %s", message_id, e)
        try:
            send_text_to_user(user_id, error_msg, messaging_api)
        except Exception as send_err:
            logger.exception("[PIPELINE] Failed to send error message: %s", send_err)
