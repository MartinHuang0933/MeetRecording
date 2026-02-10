"""LINE message sending with automatic text splitting for long messages."""

import logging

from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage

logger = logging.getLogger(__name__)

LINE_MESSAGE_MAX_LENGTH = 5000
LINE_MAX_MESSAGES_PER_PUSH = 5


def split_text(text: str, max_length: int = LINE_MESSAGE_MAX_LENGTH) -> list[str]:
    """Split text into segments that fit within LINE's message length limit.

    Split strategy priority:
        1. Paragraph break ("\\n\\n")
        2. Newline ("\\n")
        3. Period ("\u3002")
        4. Hard cut at max_length

    Args:
        text: The text to split.
        max_length: Maximum characters per segment.

    Returns:
        A list of text segments, each within max_length.
    """
    if len(text) <= max_length:
        return [text]

    segments = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            segments.append(remaining)
            break

        chunk = remaining[:max_length]

        # Try delimiters in priority order
        split_pos = None
        for delimiter in ["\n\n", "\n", "\u3002"]:
            pos = chunk.rfind(delimiter)
            if pos != -1:
                split_pos = pos + len(delimiter)
                break

        if split_pos is None:
            split_pos = max_length

        segments.append(remaining[:split_pos])
        remaining = remaining[split_pos:]

    return segments


def send_text_to_user(user_id: str, text: str, messaging_api) -> None:
    """Send a text message to a LINE user, splitting long messages automatically.

    Messages are split if they exceed LINE's 5000-character limit.
    Page numbers are appended when the text is split into multiple segments.
    Messages are sent in batches of up to 5 per push (LINE API limit).

    Args:
        user_id: The LINE user ID to send to.
        text: The text message content.
        messaging_api: An instance of linebot.v3.messaging.MessagingApi.
    """
    segments = split_text(text)

    # Add page numbers if multiple segments
    if len(segments) > 1:
        total = len(segments)
        segments = [
            f"{segment} ({i + 1}/{total})"
            for i, segment in enumerate(segments)
        ]

    # Send in batches of LINE_MAX_MESSAGES_PER_PUSH
    for batch_start in range(0, len(segments), LINE_MAX_MESSAGES_PER_PUSH):
        batch = segments[batch_start:batch_start + LINE_MAX_MESSAGES_PER_PUSH]
        messages = [TextMessage(text=segment) for segment in batch]

        messaging_api.push_message(
            PushMessageRequest(to=user_id, messages=messages)
        )
        logger.info(
            "Pushed %d message(s) to user %s (batch starting at %d)",
            len(batch),
            user_id,
            batch_start,
        )
