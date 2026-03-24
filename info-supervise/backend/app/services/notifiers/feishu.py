from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any

import httpx


class FeishuNotifier:
    def __init__(self, webhook_url: str, secret: str | None = None, timeout: int = 10) -> None:
        self.webhook_url = webhook_url
        self.secret = secret
        self.timeout = timeout

    async def send_text(self, text: str) -> None:
        payload: dict[str, Any] = {
            "msg_type": "text",
            "content": {
                "text": text,
            },
        }
        await self._post(payload)

    async def send_card(self, card: dict) -> None:
        payload: dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }
        await self._post(payload)

    async def _post(self, payload: dict[str, Any]) -> None:
        if self.secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._sign(timestamp)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"Feishu webhook rejected message: {data}")

    def _sign(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")
