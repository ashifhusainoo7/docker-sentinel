import logging
from typing import Any

import httpx

logger = logging.getLogger("sentinel.agents.slack")


class SlackAgent:
    """Sends immediate crash alerts to Slack channels via webhooks.

    Uses Block Kit formatting for readable notifications. All delivery
    errors are swallowed — notify returns False on any failure.
    """

    def __init__(self, webhook_url: str, timeout_s: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout_s = timeout_s

    async def notify(self, crash_event: dict, analysis: dict) -> bool:
        """Returns True on 2xx webhook response, False on any failure."""
        payload = self._build_block_kit(crash_event, analysis)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(self.webhook_url, json=payload)
            if 200 <= resp.status_code < 300:
                return True
            logger.warning(
                "Slack webhook returned %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        except Exception:
            logger.exception("Slack webhook call failed")
            return False

    def _build_block_kit(
        self, crash_event: dict, analysis: dict
    ) -> dict[str, Any]:
        severity = (analysis.get("severity") or "unknown").upper()
        emoji = {
            "CRITICAL": "🚨",
            "HIGH": "⚠️",
            "MEDIUM": "⚡",
            "LOW": "ℹ️",
        }.get(severity, "❓")
        suggestions = analysis.get("suggestions") or []
        suggestion_text = (
            "\n".join(f"• {s}" for s in suggestions[:3]) or "_None_"
        )

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Container Crash: {crash_event.get('container_name', 'unknown')}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Image:*\n{crash_event.get('image', 'unknown')}"},
                        {"type": "mrkdwn", "text": f"*Exit Code:*\n{crash_event.get('exit_code')}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                        {"type": "mrkdwn", "text": f"*Category:*\n{analysis.get('category', 'unknown')}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{analysis.get('root_cause', 'Unknown')}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested Fixes:*\n{suggestion_text}",
                    },
                },
            ]
        }
