from __future__ import annotations

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest
from app.services.safe_browsing_client import SafeBrowsingError, find_threats


class LinkReputationAgent(BaseAgent):
    name = "LinkReputationAgent"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        links = payload.links or []
        if not links:
            return AgentResult(agent=self.name, score=0, confidence="Low", reasons=[], ok=True)

        try:
            threats_by_url = find_threats(urls=links)
        except SafeBrowsingError as e:
            # Still return something so the user sees why it didn't run.
            return AgentResult(
                agent=self.name,
                score=0,
                confidence="Low",
                reasons=[f"Link reputation not checked: {str(e)}"],
                ok=False,
            )
        except Exception as e:
            return AgentResult(
                agent=self.name,
                score=0,
                confidence="Low",
                reasons=[f"Link reputation check failed: {type(e).__name__}"],
                ok=False,
            )

        flagged = [(u, ts) for (u, ts) in threats_by_url.items() if ts]
        if flagged:
            # If Safe Browsing flags, treat as high risk.
            top_url, threats = flagged[0]
            threat_list = ",".join(sorted(set(threats)))
            reasons = [f"Google Safe Browsing flagged URL ({threat_list})"]
            if len(flagged) > 1:
                reasons.append(f"Flagged URLs: {len(flagged)}")
            reasons.append(f"Example: {top_url}")
            return AgentResult(agent=self.name, score=85, confidence="High", reasons=reasons[0:6], ok=True)

        # No matches returned: not a guarantee of safety, but a positive signal.
        return AgentResult(
            agent=self.name,
            score=5,
            confidence="Medium",
            reasons=["No known threats in Google Safe Browsing"],
            ok=True,
        )
