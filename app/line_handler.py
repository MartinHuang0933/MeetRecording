"""LINE webhook event handling for audio messages."""

import logging

from linebot.v3.webhooks import MessageEvent, AudioMessageContent

from app import config, pipeline

logger = logging.getLogger(__name__)


def handle_audio_message(event: MessageEvent, reply_func, background_tasks) -> None:
    """Handle an incoming LINE audio message event.

    Sends an immediate acknowledgement reply, then schedules
    the audio processing pipeline as a background task.

    Args:
        event: The LINE MessageEvent containing the audio message.
        reply_func: A callable to send an immediate text reply to the user.
        background_tasks: A FastAPI BackgroundTasks instance to schedule work.
    """
    user_id = event.source.user_id
    message_id = event.message.id

    logger.info(
        "Received audio message %s from user %s", message_id, user_id
    )

    reply_func("\ud83c\udf99\ufe0f \u5df2\u6536\u5230\u8a9e\u97f3\u8a0a\u606f\uff0c\u6b63\u5728\u8655\u7406\u4e2d\uff0c\u8acb\u7a0d\u5019...")

    background_tasks.add_task(pipeline.process_audio_pipeline, user_id, message_id)

    logger.info(
        "Background task scheduled for audio message %s from user %s",
        message_id,
        user_id,
    )
