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
    usable = [r for r in (agent_results or []) if getattr(r, "ok", True)]
    if not usable:
        return Decision(0, "Safe", "Low", ["No signals"], "Proceed normally")

    # Weighted average: LLM agents get a slight weight bump vs heuristic agents.
    weighted_sum = 0.0
    weight_total = 0.0
    scores: list[int] = []
    for r in usable:
        s = max(0, min(100, int(r.score)))
        scores.append(s)

        name = (r.agent or "").lower()
        w = 1.2 if "geminiagent" in name or name.startswith("gemini") else 1.0
        weighted_sum += s * w
        weight_total += w

    base = round(weighted_sum / max(1e-9, weight_total))

    # Guardrail: if a Gemini model strongly flags a scam, don't let low-signal
    # heuristic agents average it down to "Safe".
    gemini_scores: list[int] = []
    for r in usable:
        name = (r.agent or "").lower()
        if "geminiagent" in name:
            gemini_scores.append(max(0, min(100, int(r.score))))

    # Synergy boost: high-pressure text + risky link patterns.
    all_reasons: list[str] = []
    for r in usable:
        all_reasons.extend(r.reasons)

    # If Gemini provides a concrete defensive suggestion, prefer that as the
    # recommended action (users perceive this as "better" than generic text).
    advice_lines: list[str] = []
    for x in all_reasons:
        if isinstance(x, str) and x.strip().lower().startswith("advice:"):
            advice_lines.append(x.split(":", 1)[1].strip())

    has_urgency = any("Urgency/deadline" in x for x in all_reasons)
    has_link_shortener = any("Link shortener" in x for x in all_reasons)
    has_high_pressure_link = any("High-pressure link" in x for x in all_reasons)

    boost = 0
    if has_link_shortener and (has_urgency or has_high_pressure_link):
        boost += 20

    avg = min(100, base + boost)

    if gemini_scores:
        gemini_max = max(gemini_scores)
        if gemini_max >= 80:
            avg = max(avg, gemini_max)
        elif gemini_max >= 60:
            avg = max(avg, min(75, gemini_max))

    # Confidence: if multiple agents agree on high score, raise.
    high_votes = sum(1 for s in scores if s >= 60)
    spread = (max(scores) - min(scores)) if scores else 0
    if high_votes >= 2 and spread <= 25:
        conf = "High"
    elif high_votes >= 1 and spread <= 45:
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

    if level != "Safe" and advice_lines:
        # Clamp length to keep UI tidy.
        action = (advice_lines[0] or action).strip()[:220]

    reasons = all_reasons

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for x in reasons:
        if x not in seen:
            seen.add(x)
            deduped.append(x)

    return Decision(avg, level, conf, deduped, action)
