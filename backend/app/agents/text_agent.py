import re

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest


_SUSPICIOUS_PHRASES = [
    r"\bkyc\b",
    r"\bupi\b",
    r"\bpin\b",
    r"\botp\b",
    r"\baccount\s+blocked\b",
    r"\bverify\s+now\b",
    r"\burgent\b",
    r"\bpolice\b",
    r"\bcourier\b",
    r"\bjob\s+offer\b",
    r"\brefund\b",
    r"\btax\s+refund\b",
    r"\birs\b",
    r"\bchargeback\b",
]

_URGENCY_RE = re.compile(
    r"\b(within\s+\d+\s*(?:hour|hours|hr|hrs)|\d+\s*(?:hour|hours)\b|today\b|immediately\b|final\s+notice\b|last\s+chance\b)",
    re.IGNORECASE,
)

_MONEY_RE = re.compile(r"₹\s?\d+|\b(?:rs|inr)\.?\s?\d+\b", re.IGNORECASE)


class TextAgent(BaseAgent):
    name = "TextAgent"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        text = (payload.text or "").strip()
        if not text:
            return AgentResult(agent=self.name, score=0, confidence="Low", reasons=[])

        reasons: list[str] = []
        score = 0

        keyword_hits = 0
        for pat in _SUSPICIOUS_PHRASES:
            if re.search(pat, text, re.IGNORECASE):
                keyword_hits += 1

        if keyword_hits:
            score += min(40, keyword_hits * 12)
            reasons.append("Scam-associated keywords")

        if _MONEY_RE.search(text):
            score += 10
            reasons.append("Money amount mentioned")

        if "[UPI_ID]" in text or "[PHONE]" in text:
            score += 10
            reasons.append("Sensitive payment/contact detail mentioned")

        has_link_cta = any(x in text.lower() for x in ["click", "tap", "link", "http", "www"])
        if has_link_cta:
            score += 10
            reasons.append("Call-to-action with link")

        has_urgency = bool(_URGENCY_RE.search(text))
        if has_urgency:
            score += 15
            reasons.append("Urgency/deadline pressure")

        # Synergy: refund/impersonation + link + urgency is a strong phishing pattern.
        if keyword_hits >= 1 and has_link_cta and has_urgency:
            score += 20
            reasons.append("High-pressure link-based request")

        score = min(100, score)
        confidence = "High" if score >= 70 else "Medium" if score >= 35 else "Low"

        return AgentResult(agent=self.name, score=score, confidence=confidence, reasons=reasons)
