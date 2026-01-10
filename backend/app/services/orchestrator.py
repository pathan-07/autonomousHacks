from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents.base import AgentResult
from app.agents.gemini_agent import GeminiAgent
from app.agents.gemini_image_agent import GeminiImageAgent
from app.agents.reporting_agent import ReportingAgent
from app.agents.text_agent import TextAgent
from app.agents.link_agent import LinkAgent
from app.agents.link_reputation_agent import LinkReputationAgent
from app.core.schemas import AnalyzeRequest
from app.core.settings import settings


def maybe_generate_report_data(input_text: str, result: dict) -> dict | None:
    if result.get("risk_score", 0) < 75:
        return None
    reporter = ReportingAgent()
    return reporter.generate_draft(input_text, result)


def build_agents() -> list[object]:
    agents: list[object] = [TextAgent(), LinkAgent(), LinkReputationAgent()]

    if settings.gemini_api_key:
        for model in settings.get_gemini_models():
            agents.append(GeminiAgent(model=model))
            agents.append(GeminiImageAgent(model=model))

    return agents


def run_agents(payload: AnalyzeRequest) -> list[AgentResult]:
    agents = build_agents()
    results: list[AgentResult] = []

    with ThreadPoolExecutor(max_workers=len(agents) or 1) as executor:
        future_map = {executor.submit(agent.run, payload): agent for agent in agents}
        for fut in as_completed(future_map):
            agent = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                results.append(
                    AgentResult(
                        agent=getattr(agent, "name", agent.__class__.__name__),
                        score=0,
                        confidence="Low",
                        reasons=[f"{getattr(agent, 'name', agent.__class__.__name__)} failed: {type(e).__name__}"],
                        ok=False,
                    )
                )

    return results
