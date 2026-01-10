import re
from datetime import datetime, timezone

import tldextract
import whois

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest

_SHORTENER_RE = re.compile(r"\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly)\b", re.IGNORECASE)
_IP_URL_RE = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}")


class LinkAgent(BaseAgent):
    name = "LinkAgent"

    def _registered_domain(self, url: str) -> str:
        ext = tldextract.extract(url)
        if not ext.domain or not ext.suffix:
            return ""
        return f"{ext.domain}.{ext.suffix}".lower()

    def get_domain_age_days(self, url: str) -> int:
        """Returns domain age in days.

        0 means unknown/unavailable (treated as suspicious).
        """
        try:
            registered = self._registered_domain(url)
            if not registered:
                return 0

            domain = whois.whois(registered)
            creation_date = getattr(domain, "creation_date", None)

            # Handle cases where creation_date is a list
            if isinstance(creation_date, list) and creation_date:
                creation_date = creation_date[0]

            if not creation_date:
                return 0

            if isinstance(creation_date, datetime):
                created = creation_date
            else:
                # Some WHOIS libs return date strings; fail safe.
                return 0

            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            age = (datetime.now(timezone.utc) - created).days
            return max(0, int(age))
        except Exception:
            # Fail-safe: hidden/blocked WHOIS is often associated with risky domains.
            return 0

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
            age_days = self.get_domain_age_days(u)
            if age_days == 0:
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
