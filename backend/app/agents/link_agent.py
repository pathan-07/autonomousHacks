import re

import tldextract

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest

_SHORTENER_RE = re.compile(r"\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly)\b", re.IGNORECASE)
_IP_URL_RE = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}")


class LinkAgent(BaseAgent):
    name = "LinkAgent"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        links = payload.links or []
        if not links:
            return AgentResult(agent=self.name, score=0, confidence="Low", reasons=[])

        reasons: list[str] = []
        score = 0

        for url in links:
            u = url.strip()
            if not u:
                continue

            if _SHORTENER_RE.search(u):
                score += 30
                reasons.append("Link shortener used")

            if _IP_URL_RE.search(u):
                score += 25
                reasons.append("IP-based URL")

            ext = tldextract.extract(u)
            suffix = (ext.suffix or "").lower()
            domain = (ext.domain or "").lower()

            if suffix in {"xyz", "top", "work", "click"}:
                score += 10
                reasons.append("High-risk TLD")

            if domain and any(x in domain for x in ["pay", "upi", "kyc", "bank", "secure", "verify"]):
                score += 5
                reasons.append("Domain suggests payment/verification")

        score = min(100, score)
        confidence = "Medium" if score >= 20 else "Low"
        return AgentResult(agent=self.name, score=score, confidence=confidence, reasons=reasons)
