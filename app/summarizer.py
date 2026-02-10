import anthropic
import logging

logger = logging.getLogger(__name__)


def generate_meeting_notes(
    transcript: str, model: str, max_tokens: int, api_key: str
) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "以下是一段語音轉錄的文字內容，請根據這段內容生成結構化的會議記錄。請包含以下內容：\n\n"
        "## 會議摘要\n"
        "簡短概述會議主題和目的。\n\n"
        "## 重點討論事項\n"
        "列出主要討論的議題和內容。\n\n"
        "## 決議事項\n"
        "列出會議中做出的決定。\n\n"
        "## 待辦事項\n"
        "列出需要後續跟進的事項。\n\n"
        "請使用繁體中文撰寫，並保持條理清晰。"
        "如果內容不像會議，請根據內容做適當的筆記摘要。\n\n"
        "---\n\n"
        f"{transcript}"
    )

    logger.info(
        "[CLAUDE] Sending transcript (%d chars) to model=%s, max_tokens=%d",
        len(transcript), model, max_tokens,
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )

    if not result:
        logger.warning("[CLAUDE] Empty response from Claude API, content blocks: %s", response.content)
        return "無法生成會議記錄。"

    logger.info("[CLAUDE] Meeting notes generated: %d chars", len(result))
    return result


def generate_meeting_notes_from_chunks(
    transcripts: list[str], model: str, max_tokens: int, api_key: str
) -> str:
    results = []
    for i, transcript in enumerate(transcripts):
        logger.info("Processing transcript chunk %d/%d", i + 1, len(transcripts))
        notes = generate_meeting_notes(transcript, model, max_tokens, api_key)
        results.append(notes)

    if len(results) == 1:
        return results[0]

    return _merge_meeting_notes(results, model, max_tokens, api_key)


def _merge_meeting_notes(
    notes_list: list[str], model: str, max_tokens: int, api_key: str
) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    combined_notes = "---\n".join(notes_list)
    prompt = (
        "以下是同一場會議的多段會議記錄，"
        "請將它們合併成一份完整、不重複的會議記錄，"
        "保持相同的格式結構：\n\n" + combined_notes
    )

    logger.info("Merging %d meeting note chunks", len(notes_list))

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    result = "".join(
        block.text for block in response.content if block.type == "text"
    )

    return result
