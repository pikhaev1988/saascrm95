from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def resolve_gigachat_credentials() -> str:
    """Authorization key: GIGACHAT_AUTH_KEY or Base64(client_id:client_secret)."""
    auth_key = os.getenv("GIGACHAT_AUTH_KEY", "").strip()
    if auth_key:
        return auth_key
    client_id = os.getenv("GIGACHAT_CLIENT_ID", "").strip()
    client_secret = os.getenv("GIGACHAT_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return ""


def gigachat_configured() -> bool:
    return bool(resolve_gigachat_credentials())


def _analysis_enabled() -> bool:
    raw = os.getenv("GIGACHAT_ANALYSIS_ENABLED", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    # По умолчанию: включено, если заданы учётные данные.
    return gigachat_configured()


def _verify_ssl() -> bool:
    return os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").lower() == "true"


def _gigachat_scope() -> str:
    return os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")


def _gigachat_model() -> str:
    return os.getenv("GIGACHAT_MODEL", "GigaChat")


def _request_timeout() -> float:
    return float(os.getenv("GIGACHAT_REQUEST_TIMEOUT", "45"))


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("GigaChat response is not a JSON object.")
    return payload


def chat_completion_text(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str | None = None,
) -> str | None:
    if not _analysis_enabled():
        return None
    credentials = resolve_gigachat_credentials()
    if not credentials:
        logger.warning("GigaChat: учётные данные не заданы (GIGACHAT_AUTH_KEY или CLIENT_ID+SECRET).")
        return None

    try:
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole
    except Exception:
        logger.exception("Пакет gigachat не установлен.")
        return None

    chat = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=system_prompt),
            Messages(role=MessagesRole.USER, content=user_prompt),
        ],
        temperature=temperature,
    )
    timeout = _request_timeout()
    try:
        with GigaChat(
            credentials=credentials,
            scope=_gigachat_scope(),
            model=model or _gigachat_model(),
            timeout=timeout,
            verify_ssl_certs=_verify_ssl(),
        ) as client:
            response = client.chat(chat)
        message = response.choices[0].message
        text = (message.content or "").strip()
        return text or None
    except Exception:
        logger.exception("GigaChat request failed.")
        return None


def chat_completion_json(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str | None = None,
) -> dict[str, Any] | None:
    text = chat_completion_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        model=model,
    )
    if not text:
        return None
    try:
        return parse_json_response(text)
    except Exception:
        logger.exception("GigaChat JSON parse failed.")
        return None
