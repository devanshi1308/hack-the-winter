from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union, Dict, Any, Literal

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
    risk_score: Optional[int] = None
    risk_band: Optional[str] = None
    signals: Optional[Dict[str, Any]] = None
    policy_message: Optional[str] = None
    message: Optional[str] = None


# Crisis event persistence model
class CrisisEventStatus(str, Enum):
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class CrisisEvent(BaseModel):
    event_id: Optional[str] = None
    user_id: str
    session_id: Optional[str] = None
    text: str
    risk_score: int
    risk_band: str
    label: SafetyLabel
    signals: Dict[str, Any]
    policy_message: str
    status: CrisisEventStatus = CrisisEventStatus.TRIGGERED
    resolution_steps: Optional[List[Dict[str, Any]]] = None  # step, actor, timestamp
    timestamp: Optional[datetime] = None

class ImageAnalysisRequest(BaseModel):
    image_input: str
    input_type: Literal["url", "base64"] = "url"
    task: Literal["emotion", "scene", "text"] = "emotion"
    provider: Literal["gemini"] = "gemini"


# user Profile v1 schema for personalization
class UserTone(str, Enum):
    """Preferred communication tone for coaching."""
    warm = "warm"  # nurturing, empathetic
    direct = "direct"  # straightforward, actionable
    humorous = "humorous"  # lighthearted, uplifting
    clinical = "clinical"  # evidence-based, technical
    balanced = "balanced"  # mix of warmth and directness


class CopingStyle(str, Enum):
    """Primary coping strategy preference."""
    reflective = "reflective"  # journal, introspect
    actionable = "actionable"  # do something, take action
    social = "social"  # talk to others, seek support
    somatic = "somatic"  # physical, breath, movement
    creative = "creative"  # art, music, expression


class HabitFrequency(str, Enum):
    """Frequency of habit engagement."""
    daily = "daily"
    several_weekly = "several_weekly"
    weekly = "weekly"
    occasionally = "occasionally"
    rarely = "rarely"


class SleepHabit(BaseModel):
    """Sleep tracking and preferences."""
    avg_hours_per_night: Optional[float] = None  # e.g., 7.5
    sleep_time: Optional[str] = None  # e.g., "23:00"
    wake_time: Optional[str] = None  # e.g., "06:30"
    quality_rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 Likert
    challenges: List[str] = Field(default_factory=list)  # e.g., ["insomnia", "early_waking"]


class ExerciseHabit(BaseModel):
    """Exercise/movement tracking and preferences."""
    frequency: HabitFrequency = HabitFrequency.occasionally
    preferred_types: List[str] = Field(default_factory=list)  # e.g., ["yoga", "running", "walking"]
    duration_minutes: Optional[int] = None
    time_of_day: Optional[str] = None  # e.g., "morning", "evening"


class ExerciseFeedback(BaseModel):
    """Feedback on a recommended exercise."""
    exercise_id: str
    thumbs_up: Optional[bool] = None  # True=liked, False=disliked
    intensity_match: Optional[str] = None  # "too_easy", "just_right", "too_intense"
    duration_match: Optional[str] = None  # "too_short", "just_right", "too_long"
    relevance: Optional[str] = None  # "generic", "personalized", "life_changing"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserProfile(BaseModel):
    """User Profile v1: stable traits, goals, preferences, and learned behaviors."""
    user_id: str
    
    # Tone and communication preferences
    preferred_tone: UserTone = UserTone.balanced
    communication_pace: Optional[str] = None  # "slow", "moderate", "fast"
    
    # Emotional triggers and patterns
    known_triggers: List[str] = Field(default_factory=list)  # e.g., ["social_conflict", "deadline_stress"]
    coping_style: CopingStyle = CopingStyle.reflective
    coping_style_alternatives: List[CopingStyle] = Field(default_factory=list)  # fallback preferences
    
    # Goals and intentions
    wellness_goals: List[str] = Field(default_factory=list)  # e.g., ["reduce_anxiety", "improve_sleep"]
    goal_facets: Dict[str, int] = Field(default_factory=dict)  # facet -> priority (1-5)
    
    # Habits
    sleep_habit: SleepHabit = Field(default_factory=SleepHabit)
    exercise_habit: ExerciseHabit = Field(default_factory=ExerciseHabit)
    
    # Preference learning
    exercise_feedback_history: List[ExerciseFeedback] = Field(default_factory=list)
    preference_vector: Optional[List[float]] = None  # Learned embeddings from feedback
    preference_updated_at: Optional[datetime] = None
    
    # Profile metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: Optional[datetime] = None


class UserProfileRequest(BaseModel):
    """Request to create or update a user profile."""
    user_id: str
    preferred_tone: Optional[UserTone] = None
    communication_pace: Optional[str] = None
    known_triggers: Optional[List[str]] = None
    coping_style: Optional[CopingStyle] = None
    wellness_goals: Optional[List[str]] = None
    goal_facets: Optional[Dict[str, int]] = None
    sleep_habit: Optional[SleepHabit] = None
    exercise_habit: Optional[ExerciseHabit] = None


class UserProfileResponse(BaseModel):
    """Response containing a user's profile."""
    profile: UserProfile
    message: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    labels: List[str]  # detected concepts/emotions
    confidence: List[float]  # corresponding confidence scores
    metadata: Dict[str, Any]  # source, timestamp, provider used