"""Audio downloading, validation, and splitting for LINE voice memo processing."""

import logging
import tempfile
import os

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def download_audio(message_id: str, blob_api) -> bytes:
    """Download audio content from LINE using MessagingApiBlob.

    Args:
        message_id: The LINE message ID to fetch audio for.
        blob_api: An instance of linebot.v3.messaging.MessagingApiBlob.

    Returns:
        The raw audio bytes.
    """
    logger.info("[DOWNLOAD] Fetching message content for message_id=%s", message_id)
    response = blob_api.get_message_content(message_id)
    logger.info("[DOWNLOAD] Response type=%s, has content attr=%s", type(response).__name__, hasattr(response, 'content'))
    # LINE SDK v3 get_message_content returns bytes directly or response object
    if isinstance(response, bytes):
        logger.info("[DOWNLOAD] Response is raw bytes, length=%d", len(response))
        return response
    elif hasattr(response, 'content'):
        logger.info("[DOWNLOAD] Response.content length=%d", len(response.content))
        return response.content
    elif hasattr(response, 'read'):
        data = response.read()
        logger.info("[DOWNLOAD] Response.read() length=%d", len(data))
        return data
    else:
        logger.error("[DOWNLOAD] Unknown response type: %s, dir=%s", type(response), dir(response))
        raise TypeError(f"Unexpected response type from LINE API: {type(response)}")


def validate_audio(audio_data: bytes, max_size_mb: int) -> None:
    """Validate audio data for size constraints.

    Args:
        audio_data: The raw audio bytes to validate.
        max_size_mb: Maximum allowed size in megabytes.

    Raises:
        ValueError: If audio data is empty or exceeds the size limit.
    """
    if not audio_data:
        raise ValueError("Audio data is empty")

    max_size_bytes = max_size_mb * 1024 * 1024
    if len(audio_data) > max_size_bytes:
        raise ValueError(
            f"Audio size ({len(audio_data)} bytes) is too large. "
            f"Maximum allowed: {max_size_bytes} bytes ({max_size_mb} MB)"
        )


def split_audio_if_needed(
    audio_path: str, max_chunk_minutes: int = 15
) -> list[str]:
    """Split audio into chunks if it exceeds the maximum duration.

    Args:
        audio_path: Path to the audio file.
        max_chunk_minutes: Maximum duration per chunk in minutes.

    Returns:
        A list of file paths. If no split is needed, returns [audio_path].
        Otherwise returns paths to the individual chunk files.
    """
    audio = AudioSegment.from_file(audio_path)
    max_chunk_ms = max_chunk_minutes * 60 * 1000

    if len(audio) <= max_chunk_ms:
        return [audio_path]

    chunks = []
    temp_dir = tempfile.mkdtemp()

    start = 0
    chunk_index = 0
    while start < len(audio):
        end = min(start + max_chunk_ms, len(audio))
        chunk = audio[start:end]

        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}.m4a")
        chunk.export(chunk_path, format="ipod")
        chunks.append(chunk_path)

        start = end
        chunk_index += 1

    return chunks
