from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, Dict, Any

from pydantic import BaseModel, RootModel, Field


class SentimentTone(str, Enum):
    positive = "Positive"
    neutral = "Neutral"
    negative = "Negative"
    mixed = "Mixed"


class Metadata(BaseModel):
    Summary: List[str] = Field(default_factory=list)
    Title: Optional[str] = None
    Author: Optional[List[str]] = None
    DateCreated: Optional[datetime] = None          # stricter typing
    LastModifiedDate: Optional[datetime] = None     # stricter typing
    Publisher: Optional[str] = None                 # made optional
    Language: Optional[str] = None
    PageCount: Optional[Union[int, str]] = None     # keep flexible, allow "unknown"
    SentimentTone: Optional[SentimentTone] = None   # normalized enumeration


class ChangeFormat(BaseModel):
    Page: str
    Changes: str


class SummaryResponse(RootModel[List[ChangeFormat]]):
    pass


class PromptType(str, Enum):
    DOCUMENT_ANALYSIS = "document_analysis"
    DOCUMENT_COMPARISON = "document_comparison"
    CONTEXTUALIZE_QUESTION = "contextualize_question"
    CONTEXT_QA = "context_qa"
    # Added for EI use-case
    ANALYZE_JOURNAL = "analyze_journal"
    RECOMMEND_EXERCISE = "recommend_exercise"
    COACH_QUESTION = "coach_question"
    SAFETY_CHECK = "safety_check"


class BaselineAnswer(BaseModel):
    qid: str
    value: int  # 1..5 Likert (validate elsewhere if needed)


class BaselineRequest(BaseModel):
    user_id: str
    answers: List[BaselineAnswer]


class BaselineScores(BaseModel):
    self_awareness: float
    self_regulation: float
    motivation: float
    empathy: float
    social_skills: float


class BaselineResponse(BaseModel):
    scores: BaselineScores
    strengths: List[str]
    focus: List[str]
    summary: str

class Emotion(BaseModel):
    label: str
    score: float


class FacetSignals(BaseModel):
    self_awareness: str  # "+", "-", "0"
    self_regulation: str
    motivation: str
    empathy: str
    social_skills: str


class JournalAnalysis(BaseModel):
    emotions: List[Emotion]
    sentiment: float  # -1..1
    cognitive_distortions: List[str]
    topics: List[str]
    facet_signals: FacetSignals
    one_line_insight: str


class JournalRequest(BaseModel):
    user_id: str
    mood: int  # 1..5
    journal: str
    context: Dict[str, Any] = Field(default_factory=dict)


class ExerciseRecommendation(BaseModel):
    exercise_id: str
    title: str
    steps: List[str]
    expected_outcome: str
    source_doc_id: str
    followup_question: str


class ExerciseRequest(BaseModel):
    user_id: str
    target_facets: List[str]
    context_tags: List[str]
    duration_hint: str = "2min"


class ExerciseResponse(BaseModel):
    exercise: ExerciseRecommendation

class CoachState(BaseModel):
    facet: str
    emotions: List[Emotion] = Field(default_factory=list)
    last_entry_summary: Optional[str] = None


class CoachRequest(BaseModel):
    user_id: str
    state: CoachState


class CoachResponse(BaseModel):
    question: str
    insight_line: Optional[str] = None


class SafetyLabel(str, Enum):
    SAFE = "SAFE"
    ESCALATE = "ESCALATE"


class SafetyCheckRequest(BaseModel):
    text: str


class SafetyCheckResponse(BaseModel):
    label: SafetyLabel
    message: Optional[str] = None
