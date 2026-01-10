import re
import tldextract

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest
from app.services.domain_tools import get_domain_age_days

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

            # Domain age (hard fact): most phishing domains are very new.
            # Unknown age is treated as risky (WHOIS blocked/unavailable).
            age_days = get_domain_age_days(u)
            if age_days is None:
                score += 20
                reasons.append("Domain age unknown (WHOIS unavailable)")
            elif age_days < 30:
                score += 35
                reasons.append(f"Newly registered domain ({age_days} days old)")
            elif age_days < 90:
                score += 10
                reasons.append(f"Recently registered domain ({age_days} days old)")

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
