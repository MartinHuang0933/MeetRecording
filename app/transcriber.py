import logging
from pathlib import Path

import openai

logger = logging.getLogger(__name__)


def transcribe_audio(audio_path: str, api_key: str) -> str:
    client = openai.OpenAI(api_key=api_key)

    file_name = Path(audio_path).name
    file_size = Path(audio_path).stat().st_size
    logger.info("[WHISPER] Transcribing %s (%d bytes)...", file_name, file_size)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    transcript = response.text
    logger.info("[WHISPER] Transcription complete: %d chars", len(transcript))
    logger.debug("[WHISPER] Preview: %s", transcript[:200])
    return transcript
