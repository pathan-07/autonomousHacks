from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents.base import AgentResult
from app.agents.text_agent import TextAgent
from app.agents.link_agent import LinkAgent
from app.core.schemas import AnalyzeRequest


AGENTS = [TextAgent(), LinkAgent()]


def run_agents(payload: AnalyzeRequest) -> list[AgentResult]:
    results: list[AgentResult] = []

    with ThreadPoolExecutor(max_workers=len(AGENTS) or 1) as executor:
        future_map = {executor.submit(agent.run, payload): agent for agent in AGENTS}
        for fut in as_completed(future_map):
            agent = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                results.append(
                    AgentResult(
                        agent=agent.name,
                        score=0,
                        confidence="Low",
                        reasons=[f"{agent.name} failed"],
                    )
                )

    return results
