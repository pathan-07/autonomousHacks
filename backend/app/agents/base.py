from dataclasses import dataclass

from app.core.schemas import AnalyzeRequest


@dataclass(frozen=True)
class AgentResult:
    agent: str
    score: int
    confidence: str
    reasons: list[str]
    ok: bool = True


class BaseAgent:
    name: str = "base"

    def run(self, payload: AnalyzeRequest) -> AgentResult:  # pragma: no cover
        raise NotImplementedError
