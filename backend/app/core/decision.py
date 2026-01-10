from dataclasses import dataclass

from app.agents.base import AgentResult


@dataclass(frozen=True)
class Decision:
    risk_score: int
    risk_level: str
    confidence: str
    reasons: list[str]
    recommended_action: str


def decide(agent_results: list[AgentResult]) -> Decision:
    if not agent_results:
        return Decision(0, "Safe", "Low", ["No signals"], "Proceed normally")

    scores = [max(0, min(100, r.score)) for r in agent_results]
    base = round(sum(scores) / len(scores))

    # Synergy boost: high-pressure text + risky link patterns.
    all_reasons: list[str] = []
    for r in agent_results:
        all_reasons.extend(r.reasons)

    has_urgency = any("Urgency/deadline" in x for x in all_reasons)
    has_link_shortener = any("Link shortener" in x for x in all_reasons)
    has_high_pressure_link = any("High-pressure link" in x for x in all_reasons)

    boost = 0
    if has_link_shortener and (has_urgency or has_high_pressure_link):
        boost += 20

    avg = min(100, base + boost)

    # Confidence: if multiple agents agree on high score, raise.
    high_votes = sum(1 for s in scores if s >= 60)
    if high_votes >= 2:
        conf = "High"
    elif high_votes == 1:
        conf = "Medium"
    else:
        conf = "Low"

    if avg < 30:
        level = "Safe"
        action = "Proceed normally"
    elif avg <= 60:
        level = "Caution"
        action = "Avoid sharing OTP/UPI PIN; verify sender independently"
    else:
        level = "High"
        action = "Do not pay/click; block/report; contact your bank/app support"

    reasons = all_reasons

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for x in reasons:
        if x not in seen:
            seen.add(x)
            deduped.append(x)

    return Decision(avg, level, conf, deduped, action)
