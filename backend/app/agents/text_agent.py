import re
from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest

_SUSPICIOUS_PHRASES = [
    # General
    r"\bkyc\b", r"\bupi\b", r"\bpin\b", r"\botp\b",
    r"\bverify\s+now\b", r"\burgent\b", r"\bjob\s+offer\b",
    r"\brefund\b", r"\bcashback\b", r"\blottery\b",
    # Indian Context Scams
    r"\belectricity\b", r"\bdisconnect\b", r"\bpower\s+cut\b",
    r"\bblocked\b", r"\bpan\s+card\b", r"\badhaar\b",
    r"\bpolice\b", r"\bcbi\b", r"\bcustoms\b", r"\bseized\b",
    r"\barrest\b", r"\bwarrant\b",
]

_URGENCY_RE = re.compile(
    r"\b(immediately|urgent|tonight|today|24\s*hours|final\s+notice|block|suspend)",
    re.IGNORECASE,
)


class TextAgent(BaseAgent):
    name = "TextAgent"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        text = (payload.text or "").strip().lower()
        if not text:
            return AgentResult(agent=self.name, score=0, confidence="Low", reasons=[])

        reasons: list[str] = []
        score = 0
        hits = 0

        # 1. Keyword Scan
        for pat in _SUSPICIOUS_PHRASES:
            if re.search(pat, text):
                hits += 1

        if hits > 0:
            score += min(50, hits * 15)
            reasons.append(f"Found {hits} suspicious keywords")

        # 2. Urgency Scan
        if _URGENCY_RE.search(text):
            score += 25
            reasons.append("High urgency/threat language detected")

        # 3. The 'Link + Threat' Combo
        has_link = "http" in text or "www" in text or ".com" in text
        if has_link and (hits > 0 or score > 0):
            score += 25
            reasons.append("Combination of Link + Threat/Urgency")

        return AgentResult(
            agent=self.name,
            score=min(100, score),
            confidence="High" if score > 70 else "Medium",
            reasons=reasons,
        )
