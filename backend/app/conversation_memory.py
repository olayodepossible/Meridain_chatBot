"""Conversation transcript storage: S3 in Lambda (when configured) or local directory for dev."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from app.config import Settings

logger = logging.getLogger("conversation_memory")

_MAX_MESSAGES = 80  # cap stored / loaded rows to bound token use


def _conversation_object_name(conversation_id: str) -> str:
    digest = hashlib.sha256(conversation_id.encode("utf-8")).hexdigest()
    return f"conversations/{digest}.json"


def _normalize_messages(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        out.append({"role": role, "content": content})
    return out[-_MAX_MESSAGES:]


class ConversationMemory:
    """Load / append chat turns as JSON lists of {role, content} messages."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _use_s3(self) -> bool:
        return bool(self._settings.use_s3 and self._settings.s3_bucket)

    async def load(self, conversation_id: str) -> list[dict[str, Any]]:
        key = _conversation_object_name(conversation_id)
        raw_json: str | None
        if self._use_s3():
            raw_json = await asyncio.to_thread(self._s3_get_body, key)
        else:
            path = self._local_path(key)
            raw_json = await asyncio.to_thread(self._read_file_if_exists, path)

        if not raw_json:
            return []
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("Corrupt conversation JSON", extra={"key": key})
            return []
        messages = data.get("messages") if isinstance(data, dict) else None
        return _normalize_messages(messages)

    async def append(
        self, conversation_id: str, user_text: str, assistant_text: str
    ) -> None:
        if not assistant_text.strip():
            return
        key = _conversation_object_name(conversation_id)
        prev = await self.load(conversation_id)
        next_messages = list(prev)
        if user_text.strip():
            next_messages.append({"role": "user", "content": user_text.strip()})
        if assistant_text.strip():
            next_messages.append({"role": "assistant", "content": assistant_text.strip()})
        next_messages = _normalize_messages(next_messages)
        body = json.dumps({"version": 1, "messages": next_messages}, ensure_ascii=False)
        if self._use_s3():
            await asyncio.to_thread(self._s3_put_body, key, body)
        else:
            path = self._local_path(key)
            await asyncio.to_thread(self._write_file, path, body)

    def _local_path(self, key: str) -> Path:
        base = Path(self._settings.conversation_memory_dir)
        # key is like conversations/<hash>.json — safe under base
        return base / key.replace("\\", "/")

    @staticmethod
    def _read_file_if_exists(path: Path) -> str | None:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _write_file(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def _s3_get_body(self, key: str) -> str | None:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("s3")
        try:
            resp = client.get_object(Bucket=self._settings.s3_bucket, Key=key)
            return resp["Body"].read().decode("utf-8")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                return None
            logger.warning(
                "S3 get_object failed",
                extra={"key": key, "code": code},
            )
            raise

    def _s3_put_body(self, key: str, body: str) -> None:
        import boto3

        client = boto3.client("s3")
        client.put_object(
            Bucket=self._settings.s3_bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )

    
async def overwrite(
    self,
    conversation_id: str,
    messages: list[dict[str, Any]],
) -> None:
    key = _conversation_object_name(conversation_id)
    messages = _normalize_messages(messages)

    body = json.dumps({"version": 1, "messages": messages}, ensure_ascii=False)

    if self._use_s3():
        await asyncio.to_thread(self._s3_put_body, key, body)
    else:
        path = self._local_path(key)
        await asyncio.to_thread(self._write_file, path, body)