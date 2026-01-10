from pydantic import BaseModel, Field


class AnalyzeMetadata(BaseModel):
    sender: str | None = None
    time: str | None = None
    app_type: str | None = None
    region: str | None = None


class AnalyzeRequest(BaseModel):
    text: str | None = None
    image_base64: str | None = None
    image_url: str | None = None
    audio_base64: str | None = None
    audio_url: str | None = None
    links: list[str] = Field(default_factory=list)
    metadata: AnalyzeMetadata | None = None


class AgentBreakdown(BaseModel):
    agent: str
    score: int
    confidence: str
    reasons: list[str]
    ok: bool = True


class ReportDraft(BaseModel):
    is_reportable: bool = True
    portal_url: str
    email_subject: str
    email_body: str


class AnalyzeResponse(BaseModel):
    risk_score: int
    risk_level: str
    confidence: str
    reasons: list[str]
    recommended_action: str
    agent_results: list[AgentBreakdown] | None = None
    report_data: ReportDraft | None = None


class FeedbackRequest(BaseModel):
    interaction_id: str | None = None
    user_verdict: str = Field(description="'scam' or 'safe'")
    notes: str | None = None


class FeedbackResponse(BaseModel):
    ok: bool
