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
    # 1. Filter out broken agents
    usable = [r for r in (agent_results or []) if getattr(r, "ok", True)]

    if not usable:
        return Decision(0, "Safe", "Low", ["No signals detected"], "Proceed normally")

    # 2. STRATEGY: MAX RISK WINS
    # Sort agents by score (Highest first)
    usable.sort(key=lambda x: x.score, reverse=True)
    top_agent = usable[0]

    final_score = top_agent.score
    final_confidence = top_agent.confidence

    # 3. Aggregate Reasons (Don't lose context from other agents)
    all_reasons: list[str] = []
    seen: set[str] = set()

    for r in usable:
        # Only add reasons if the agent actually found something (score > 0)
        if r.score > 0:
            for reason in r.reasons:
                if reason not in seen:
                    seen.add(reason)
                    all_reasons.append(reason)

    # 4. Determine Risk Level
    if final_score < 30:
        level = "Safe"
        action = "No specific threats detected."
    elif final_score <= 65:
        level = "Caution"
        action = "Verify the sender carefully. Do not click suspicious links."
    else:
        level = "High"
        action = "BLOCK this sender. Do not pay or share OTPs."

    # 5. Extract specific advice if available
    advice_lines = [
        x.split(":", 1)[1].strip() for x in all_reasons if x.lower().startswith("advice:")
    ]
    if advice_lines:
        action = advice_lines[0][:250]  # Use the AI's specific advice

    return Decision(
        risk_score=final_score,
        risk_level=level,
        confidence=final_confidence,
        reasons=all_reasons[:8],
        recommended_action=action,
    )
