class SlackAgent:
    """Sends immediate crash alerts to Slack channels via webhooks.

    Uses Block Kit formatting for rich, readable notifications.
    Cost: $0 — Free forever.
    """

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url

    async def notify(self, crash_event: dict, analysis: dict) -> bool:
        """Send a Slack notification with crash details and analysis.

        Message includes: container name, exit code, severity, root cause,
        and suggested fixes in Block Kit format.
        """
        raise NotImplementedError(
            "Slack notification not yet implemented. "
            "Will use httpx to POST Block Kit formatted message to webhook URL."
        )
