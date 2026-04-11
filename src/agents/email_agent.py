class EmailAgent:
    """Sends comprehensive crash reports with logs, AI analysis, and fix suggestions.

    Uses SendGrid / Gmail SMTP with Jinja2 templates.
    Cost: $0 — SendGrid free tier (100/day).
    """

    def __init__(self):
        pass

    async def send(
        self, crash_event: dict, analysis: dict, recipient_email: str
    ) -> bool:
        """Send detailed crash report email.

        Email contents: container name, image, exit code, last 100 log lines,
        timestamp + uptime, AI-generated root cause, suggested fixes,
        restart outcome, and dashboard link.
        """
        raise NotImplementedError(
            "Email sending not yet implemented. "
            "Will use Jinja2 to render crash_email.html template, "
            "then send via SendGrid API or SMTP."
        )
