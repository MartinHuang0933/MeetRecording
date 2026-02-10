"""FastAPI entry point with LINE Webhook endpoint."""

import logging

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, AudioMessageContent  # noqa: F401
from linebot.v3.messaging import (
    MessagingApi,
    ApiClient,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)

from app.config import get_settings
from app.line_handler import handle_audio_message
from app.log_store import InMemoryHandler, get_logs, clear_logs, log_buffer
from app.log_page import LOG_HTML

settings = get_settings()

# Setup logging: console + in-memory buffer
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=log_level, format=log_format)

memory_handler = InMemoryHandler()
memory_handler.setLevel(log_level)
memory_handler.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(memory_handler)

logger = logging.getLogger(__name__)

app = FastAPI(title="LINE Voice Memo → Meeting Notes")

parser = WebhookParser(settings.line_channel_secret)

configuration = Configuration(access_token=settings.line_channel_access_token)
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/callback")
async def callback(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")

    logger.info("[WEBHOOK] Received callback request")
    logger.info("[WEBHOOK] Signature: %s", signature[:20] + "..." if signature else "(empty)")
    logger.info("[WEBHOOK] Body length: %d chars", len(body))
    logger.debug("[WEBHOOK] Body: %s", body[:500])

    try:
        events = parser.parse(body, signature)
        logger.info("[WEBHOOK] Parsed %d event(s)", len(events))
    except InvalidSignatureError:
        logger.error("[WEBHOOK] Invalid signature!")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to parse webhook body: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    for i, event in enumerate(events):
        event_type = getattr(event, "type", None)
        logger.info("[WEBHOOK] Event[%d] type=%s, class=%s", i, event_type, type(event).__name__)

        if event_type != "message":
            logger.info("[WEBHOOK] Event[%d] skipped (not a message event)", i)
            continue

        message_type = getattr(event.message, "type", None)
        logger.info("[WEBHOOK] Event[%d] message.type=%s, message.class=%s", i, message_type, type(event.message).__name__)

        if message_type != "audio":
            logger.info("[WEBHOOK] Event[%d] skipped (message type is '%s', not 'audio')", i, message_type)
            continue

        logger.info("[WEBHOOK] Event[%d] Audio message detected! message_id=%s, user_id=%s",
                    i, event.message.id, event.source.user_id)

        def reply_func(text: str, _event=event):
            try:
                logger.info("[REPLY] Sending reply to token=%s...", _event.reply_token[:20])
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=_event.reply_token,
                        messages=[TextMessage(text=text)],
                    )
                )
                logger.info("[REPLY] Reply sent successfully")
            except Exception as e:
                logger.exception("[REPLY] Failed to send reply: %s", e)

        handle_audio_message(event, reply_func, background_tasks)

    return "OK"


# ── Log viewer endpoints ──


@app.get("/logs", response_class=HTMLResponse)
async def logs_page():
    return LOG_HTML


@app.get("/logs/api")
async def logs_api(level: str = "", keyword: str = "", limit: int = 500):
    entries = get_logs(level_filter=level, keyword=keyword, limit=limit)
    return {
        "total": len(log_buffer),
        "showing": len(entries),
        "logs": [
            {"timestamp": e.timestamp, "level": e.level, "name": e.name, "message": e.message}
            for e in entries
        ],
    }


@app.post("/logs/clear")
async def logs_clear():
    count = clear_logs()
    return {"cleared": count}
