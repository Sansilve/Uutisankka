from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class PreferenceProfile(BaseModel):
    interests: List[str] = Field(default_factory=lambda: ["politiikka", "teknologia", "talous"])
    disliked_topics: List[str] = Field(default_factory=lambda: ["viihde", "celebrity"])
    news_scope: List[str] = Field(default_factory=lambda: ["suomi", "maailma"])
    local_city: str = ""
    hide_paywall: bool = False
    excluded_sources: List[str] = Field(default_factory=list)


class PreferenceUpdate(BaseModel):
    interests: List[str]
    disliked_topics: List[str]
    news_scope: List[str] = Field(default_factory=lambda: ["suomi", "maailma"])
    local_city: str = ""
    hide_paywall: bool = False
    excluded_sources: List[str] = Field(default_factory=list)


class SummaryPayload(BaseModel):
    bullets: List[str]


class ScoreBreakdownItem(BaseModel):
    reason: str
    points: float
    category: str = ""


class ScoreBreakdownPayload(BaseModel):
    items: List[ScoreBreakdownItem] = Field(default_factory=list)


class ArticleBrief(BaseModel):
    id: int
    title: str
    source: str
    published_at: datetime | None
    url: str
    score: float
    base_score: float
    feedback_score: float
    feedback_positive: int
    feedback_negative: int
    topics: List[str]
    summary: SummaryPayload
    score_breakdown: ScoreBreakdownPayload
    is_paywall: bool = False
    category: str | None = None
    category_secondary: str | None = None
    tone: str | None = None
    tone_confidence: float | None = None
    tone_reason: str | None = None


class IngestResponse(BaseModel):
    fetched: int
    inserted: int
    duplicates: int
    enriched: int


class BriefingResponse(BaseModel):
    generated_at: datetime
    total: int
    stories: List[ArticleBrief]


class FeedbackPayload(BaseModel):
    article_id: int
    is_relevant: bool


class FeedbackResponse(BaseModel):
    article_id: int
    feedback_positive: int
    feedback_negative: int
    feedback_score: float
    total_score: float


class MetricsResponse(BaseModel):
    top_limit: int
    total_feedback_votes: int
    positive_feedback_ratio: float | None


class SwipeHistoryItem(BaseModel):
    swipe_id: int
    is_relevant: bool
    swiped_at: datetime
    id: int
    title: str
    source: str
    published_at: datetime | None
    url: str
    topics: List[str]
    summary: SummaryPayload


class HistoryResponse(BaseModel):
    total: int
    items: List[SwipeHistoryItem]


class AllNewsItem(BaseModel):
    id: int
    title: str
    source: str
    region: str
    published_at: datetime | None
    url: str
    topics: List[str]
    summary: SummaryPayload
    is_paywall: bool = False


class AllNewsResponse(BaseModel):
    total: int
    items: List[AllNewsItem]
