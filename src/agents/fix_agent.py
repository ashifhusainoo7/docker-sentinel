import logging

from langchain_openai import ChatOpenAI

from config.settings import settings
from src.agents._prompts import build_analysis_prompt
from src.schemas.crash_event import CrashAnalysis
from src.services.crash_memory import CrashMemory

logger = logging.getLogger("sentinel.agents.fix")


def _minimal_fallback() -> CrashAnalysis:
    """Returned when both LLM primary and fallback fail."""
    return CrashAnalysis(
        restart_likely_fixes=False,
        root_cause="LLM unavailable — manual investigation required",
        severity="medium",
        category="unknown",
        suggestions=["Check LLM provider status", "Review logs manually"],
        confidence=0.0,
    )


class FixAgent:
    """Analyzes crash events via OpenAI, with Qdrant cache lookup.

    Phase 2: CrashMemory stub returns None → every event hits the LLM.
    Phase 3: Qdrant similarity check gates the LLM call.
    """

    def __init__(self):
        self._memory = CrashMemory()
        self._chain = self._build_chain()

    def _build_chain(self):
        # Pass api_key explicitly from settings so the key flows through
        # pydantic-settings → .env rather than relying on process env vars.
        api_key = settings.openai_api_key
        primary = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=30,
            api_key=api_key,
        ).with_structured_output(CrashAnalysis)
        fallback = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            timeout=30,
            api_key=api_key,
        ).with_structured_output(CrashAnalysis)
        return primary.with_fallbacks([fallback])

    async def analyze(self, crash_event: dict) -> tuple[CrashAnalysis, bool]:
        """Analyze a crash event. Returns (analysis, cache_hit)."""
        logs = crash_event.get("logs") or ""

        cached = await self._memory.find_similar(logs)
        if cached is not None:
            return CrashAnalysis.model_validate(cached), True

        try:
            messages = build_analysis_prompt(crash_event)
            analysis = await self._chain.ainvoke(messages)
        except Exception:
            logger.exception("LLM call failed for crash analysis")
            return _minimal_fallback(), False

        try:
            await self._memory.store(logs, analysis.model_dump())
        except Exception:
            logger.exception("Failed to store crash analysis in memory")

        return analysis, False


_agent_instance: FixAgent | None = None


def get_fix_agent() -> FixAgent:
    """Return the module-level singleton, building it on first call."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FixAgent()
    return _agent_instance
