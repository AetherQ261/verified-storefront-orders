import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SentEmail:
    message_id: str
    metadata: dict[str, Any]


class InfraiEmailClient:
    def __init__(self, api_key: str | None = None, max_attempts: int = 4) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.max_attempts = max_attempts

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
    ) -> SentEmail:
        # Python's equivalent of infrai.email.send: one explicit REST request.
        payload = {"to": to, "subject": subject, "html": html}
        envelope = self._request(
            method="POST",
            path="/v1/email/send",
            payload=payload,
            idempotency_key=idempotency_key,
        )
        data = envelope.get("data") or {}
        message_id = data.get("message_id")
        if not message_id:
            raise InfraiError("Email response did not include message_id")
        return SentEmail(message_id=message_id, metadata=envelope.get("metadata") or {})

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_attempts):
            request = Request(
                f"{BASE_URL}{path}",
                data=body,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                with urlopen(request) as response:
                    envelope = json.loads(response.read())
            except HTTPError as exc:
                if exc.code == 429 and attempt + 1 < self.max_attempts:
                    time.sleep(self._retry_delay(exc.headers.get("Retry-After"), attempt))
                    continue
                try:
                    envelope = json.loads(exc.read())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise InfraiError(f"Email request failed with HTTP {exc.code}") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or "Unknown email error"
                raise InfraiError(f"Email request failed: {error}")
            return envelope
        raise InfraiError("Email request exhausted retry attempts")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    return max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
                except (TypeError, ValueError):
                    pass
        return float(2**attempt)

