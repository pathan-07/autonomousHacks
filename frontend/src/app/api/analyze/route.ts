import { NextResponse } from "next/server";

type AgentResult = {
  name: string;
  focus: string;
  finding: string;
  signals: string[];
};

type AnalyzeResponse = {
  requestId: string;
  overall: {
    label: "likely_scam" | "uncertain" | "likely_legit";
    score: number; // 0..100
    confidence: "Low" | "Medium" | "High";
    summary: string;
    recommendations: string[];
    advice_hindi?: string;
    category?: string;
  };
  agents: AgentResult[];
  report_data?: Record<string, unknown> | null;
};

type BackendAnalyzeResponse = {
  risk_score: number;
  risk_level: "Safe" | "Caution" | "High";
  confidence: "Low" | "Medium" | "High";
  reasons: string[];
  recommended_action: string;
  report_data?: Record<string, unknown> | null;
  audio_analysis?: Record<string, unknown> | null;
  agent_results?: Array<{
    agent: string;
    score: number;
    confidence: string;
    reasons: string[];
    ok: boolean;
  }>;
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function countMatches(haystack: string, re: RegExp): number {
  const matches = haystack.match(re);
  return matches ? matches.length : 0;
}

function hasAny(haystack: string, needles: string[]) {
  return needles.some((n) => haystack.includes(n));
}

function analyzeText(rawText: string): AnalyzeResponse {
  const text = rawText.trim();
  const lower = text.toLowerCase();

  const urls = text.match(/https?:\/\/[^\s)\]}>"]+/gi) ?? [];
  const suspiciousWords = [
    "urgent",
    "immediately",
    "act now",
    "final notice",
    "limited time",
    "verify",
    "login",
    "password",
    "otp",
    "one time password",
    "code",
    "gift card",
    "wire",
    "bank transfer",
    "crypto",
    "bitcoin",
    "usdt",
    "refund",
    "irs",
    "police",
    "arrest",
    "lawsuit",
    "suspended",
    "compromised",
    "security alert",
    "click",
    "tap",
  ];

  const hasThreatOrUrgency = hasAny(lower, [
    "urgent",
    "immediately",
    "final notice",
    "suspended",
    "arrest",
    "lawsuit",
    "compromised",
  ]);

  const hasCredentialAsk = hasAny(lower, [
    "password",
    "otp",
    "verification code",
    "one time password",
    "login",
    "credentials",
  ]);

  const hasPaymentAsk = hasAny(lower, [
    "gift card",
    "wire",
    "bank transfer",
    "crypto",
    "bitcoin",
    "usdt",
    "send money",
  ]);

  const exclamations = countMatches(text, /!/g);
  const allCapsWords = countMatches(text, /\b[A-Z]{4,}\b/g);
  const moneyMentions = countMatches(text, /\$\s?\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+\s?(?:usd|dollars)\b/gi);
  const keywordHits = suspiciousWords.filter((w) => lower.includes(w)).length;

  const shortenedUrlHits = urls.filter((u) =>
    /bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|cutt\.ly/i.test(u)
  ).length;

  const ipv4UrlHits = urls.filter((u) => /https?:\/\/\d{1,3}(?:\.\d{1,3}){3}/.test(u)).length;

  // Simple heuristic scoring. This is a mock; replace with your Python multi-agent backend later.
  let score = 0;
  score += keywordHits * 4;
  score += urls.length * 6;
  score += shortenedUrlHits * 12;
  score += ipv4UrlHits * 12;
  score += exclamations * 2;
  score += allCapsWords * 3;
  score += moneyMentions * 6;
  if (hasThreatOrUrgency) score += 18;
  if (hasCredentialAsk) score += 22;
  if (hasPaymentAsk) score += 22;

  score = clamp(score, 0, 100);

  const label: AnalyzeResponse["overall"]["label"] =
    score >= 70 ? "likely_scam" : score >= 40 ? "uncertain" : "likely_legit";

  const recommendations: string[] = [];
  if (label !== "likely_legit") {
    recommendations.push(
      "Do not click links or share codes/passwords.",
      "Verify using an official website/app you open yourself (not the message link).",
      "If money is requested, stop and confirm via a trusted channel."
    );
  } else {
    recommendations.push("Still verify sender identity if anything feels off.");
  }

  const agents: AgentResult[] = [
    {
      name: "IntentAgent",
      focus: "What is the message trying to get you to do?",
      finding:
        hasPaymentAsk || hasCredentialAsk
          ? "Message pushes for sensitive action (payment or credentials)."
          : hasThreatOrUrgency
          ? "Message leans on urgency/threat to trigger quick action."
          : "No strong coercive intent detected from the text alone.",
      signals: [
        hasThreatOrUrgency ? "Urgency/threat language" : "No strong urgency",
        hasCredentialAsk ? "Asks for OTP/password/login" : "No direct credential request",
        hasPaymentAsk ? "Requests payment via risky methods" : "No payment request",
      ],
    },
    {
      name: "LinkAgent",
      focus: "Check links for common phishing patterns",
      finding:
        urls.length === 0
          ? "No links detected."
          : shortenedUrlHits > 0 || ipv4UrlHits > 0
          ? "Links include high-risk patterns (shorteners or raw IP URLs)."
          : "Links detected; verify domain carefully before opening.",
      signals: [
        `Links found: ${urls.length}`,
        shortenedUrlHits ? `Shortened links: ${shortenedUrlHits}` : "No shortened links",
        ipv4UrlHits ? `IP-based URLs: ${ipv4UrlHits}` : "No IP-based URLs",
      ],
    },
    {
      name: "LanguageAgent",
      focus: "Spot manipulation, pressure, and anomalies",
      finding:
        exclamations + allCapsWords + keywordHits > 10
          ? "High-pressure language and multiple scam-associated terms."
          : exclamations + allCapsWords > 5
          ? "Some pressure markers (excess punctuation/caps)."
          : "Language looks relatively neutral.",
      signals: [
        `Keyword hits: ${keywordHits}`,
        `Exclamation marks: ${exclamations}`,
        `ALL-CAPS words: ${allCapsWords}`,
      ],
    },
    {
      name: "RiskAggregator",
      focus: "Combine signals into an overall risk rating",
      finding:
        label === "likely_scam"
          ? "Multiple red flags align; treat as a likely scam."
          : label === "uncertain"
          ? "Some red flags; proceed carefully and verify independently."
          : "Few red flags; likely legitimate based on text heuristics.",
      signals: [
        `Score: ${score}/100`,
        `Label: ${label}`,
        urls.length ? "Contains links" : "No links",
      ],
    },
  ];

  const summary =
    label === "likely_scam"
      ? "High-risk indicators detected (pressure + sensitive action patterns)."
      : label === "uncertain"
      ? "Some suspicious signals detected; verify independently."
      : "No strong scam signals detected from text heuristics.";

  const confidence: AnalyzeResponse["overall"]["confidence"] =
    score >= 80 || score <= 20
      ? "High"
      : score >= 60 || score <= 35
      ? "Medium"
      : "Low";

  return {
    requestId: crypto.randomUUID(),
    overall: {
      label,
      score,
      confidence,
      summary,
      recommendations,
    },
    agents,
  };
}

export async function POST(req: Request) {
  const contentType = req.headers.get("content-type") || "";

  let text = "";
  let imageUrl = "";
  let audioFile: File | null = null;

  if (contentType.toLowerCase().includes("multipart/form-data")) {
    const form = await req.formData();
    const t = form.get("text");
    const iu = form.get("image_url");
    const af = form.get("audio_file");

    text = typeof t === "string" ? t : "";
    imageUrl = typeof iu === "string" ? iu : "";
    audioFile = af instanceof File ? af : null;
  } else {
    let payload: unknown;
    try {
      payload = await req.json();
    } catch {
      return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }

    text =
      typeof (payload as { text?: unknown })?.text === "string"
        ? ((payload as { text: string }).text as string)
        : "";

    imageUrl =
      typeof (payload as { image_url?: unknown })?.image_url === "string"
        ? ((payload as { image_url: string }).image_url as string)
        : "";
  }

  if (text.trim().length === 0 && imageUrl.trim().length === 0 && !audioFile) {
    return NextResponse.json(
      { error: "Missing 'text', 'image_url', or 'audio_file'" },
      { status: 400 }
    );
  }

  if (text.length > 10_000) {
    return NextResponse.json(
      { error: "Text too long (max 10,000 chars)" },
      { status: 413 }
    );
  }

  // Backend URL resolution:
  // - Local dev: use localhost by default.
  // - Prod: allow env override; fallback to the deployed Cloud Run URL.
  const BACKEND_URL =
    process.env.BACKEND_URL ||
    (process.env.NODE_ENV === "development"
      ? "http://127.0.0.1:8000"
      : "https://scamshield-backend-457750343726.us-central1.run.app");

  // Extract links so backend can run link signals.
  const links = text.match(/https?:\/\/[^\s)\]}>\"]+/gi) ?? [];

  try {
    const fd = new FormData();
    if (text.trim()) fd.append("text", text);
    if (imageUrl.trim()) fd.append("image_url", imageUrl);
    if (links.length) fd.append("links", JSON.stringify(links));
    if (audioFile) fd.append("audio_file", audioFile, audioFile.name || "audio");

    const resp = await fetch(`${BACKEND_URL}/analyze`, {
      method: "POST",
      headers: {
        ...(process.env.BACKEND_API_KEY
          ? { "X-API-Key": process.env.BACKEND_API_KEY }
          : {}),
      },
      body: fd,
    });

    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      return NextResponse.json(
        {
          error: "Backend /analyze failed",
          status: resp.status,
          details: errText.slice(0, 500),
        },
        { status: 502 }
      );
    }

    const backend = (await resp.json()) as BackendAnalyzeResponse;
    const score = clamp(Number(backend.risk_score) || 0, 0, 100);
    const label: AnalyzeResponse["overall"]["label"] =
      backend.risk_level === "High"
        ? "likely_scam"
        : backend.risk_level === "Caution"
        ? "uncertain"
        : "likely_legit";

    const reasons = backend.reasons ?? [];
    const advice = reasons
      .filter((r) => r.trim().toLowerCase().startsWith("advice:"))
      .map((r) => r.split(":", 2)[1]?.trim() || "")
      .filter(Boolean);
    const redFlags = reasons.filter((r) => !r.trim().toLowerCase().startsWith("advice:"));

    const summary = redFlags.length
      ? redFlags.slice(0, 3).join("; ")
      : backend.recommended_action || "";

    const recommendations = advice.length
      ? advice
      : backend.recommended_action
      ? [backend.recommended_action]
      : [];

    const inferredCategory =
      (typeof (backend.report_data as { category?: unknown } | undefined)?.category === "string"
        ? ((backend.report_data as { category: string }).category as string)
        : "") ||
      (typeof (backend.audio_analysis as { category?: unknown } | undefined)?.category === "string"
        ? ((backend.audio_analysis as { category: string }).category as string)
        : "");

    return NextResponse.json({
      requestId: crypto.randomUUID(),
      overall: {
        label,
        score,
        confidence: backend.confidence,
        summary,
        recommendations,
        ...(inferredCategory ? { category: inferredCategory } : {}),
      },
      agents: [
        {
          name: "BackendFusion",
          focus: `Backend verdict (confidence: ${backend.confidence})`,
          finding: summary || "Verdict generated by backend",
          signals: reasons,
        },
      ],
      report_data: backend.report_data ?? null,
    } satisfies AnalyzeResponse);
  } catch (e) {
    const details = e instanceof Error ? e.message : String(e);

    // Optional dev-only fallback to local heuristics.
    if (process.env.ALLOW_LOCAL_HEURISTICS === "1" && text.trim().length > 0) {
      return NextResponse.json(analyzeText(text));
    }

    // If backend isn't running, surface a clear error instead of silently returning wrong results.
    return NextResponse.json(
      {
        error:
          "Backend unavailable. Start it from backend/ with: .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000",
        details: details.slice(0, 200),
      },
      { status: 502 }
    );
  }
}
