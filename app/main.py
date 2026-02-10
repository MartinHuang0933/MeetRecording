"""FastAPI entry point with LINE Webhook endpoint."""

import logging

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
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

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if getattr(event, "type", None) != "message":
            continue

        if getattr(event.message, "type", None) != "audio":
            continue

        def reply_func(text: str, _event=event):
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=_event.reply_token,
                    messages=[TextMessage(text=text)],
                )
            )

        handle_audio_message(event, reply_func, background_tasks)

    return "OK"
