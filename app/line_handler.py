"""LINE webhook event handling for audio messages."""

import logging

from linebot.v3.webhooks import MessageEvent, AudioMessageContent

from app import config, pipeline

logger = logging.getLogger(__name__)


def handle_audio_message(event, reply_func, background_tasks) -> None:
    """Handle an incoming LINE audio message event."""
    user_id = event.source.user_id
    message_id = event.message.id

    logger.info("[HANDLER] Processing audio message_id=%s from user_id=%s", message_id, user_id)

    logger.info("[HANDLER] Sending immediate reply...")
    reply_func("🎙️ 已收到語音訊息，正在處理中，請稍候...")
    logger.info("[HANDLER] Immediate reply done")

    logger.info("[HANDLER] Scheduling background task...")
    background_tasks.add_task(pipeline.process_audio_pipeline, user_id, message_id)
    logger.info("[HANDLER] Background task scheduled for message_id=%s", message_id)
