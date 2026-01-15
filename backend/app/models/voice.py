"""Pydantic models for voice calls and analytics"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CallStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"
    TRANSFERRED = "transferred"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"
    ESCALATED = "escalated"
    FOLLOW_UP_NEEDED = "follow_up_needed"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CustomerType(str, Enum):
    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"
    AT_RISK = "at_risk"
    UNKNOWN = "unknown"


# ========================================
# VAPI Webhook Models
# ========================================

class VAPIWebhookMessage(BaseModel):
    type: str
    call: Optional[Dict[str, Any]] = None
    transcript: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    functionCall: Optional[Dict[str, Any]] = None


class VAPIFunctionCall(BaseModel):
    name: str
    parameters: Dict[str, Any] = {}


# ========================================
# Call Models
# ========================================

class TranscriptMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None


class CallBase(BaseModel):
    vapi_call_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: CallStatus = CallStatus.IN_PROGRESS
    agent_type: str = "general"
    recording_url: Optional[str] = None


class CallCreate(CallBase):
    caller_phone: Optional[str] = None
    caller_id: Optional[str] = None
    vapi_assistant_id: Optional[str] = None


class CallResponse(BaseModel):
    id: str
    vapi_call_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    agent_type: str
    # Joined from analytics
    sentiment: Optional[str] = None
    category: Optional[str] = None
    resolution: Optional[str] = None

    class Config:
        from_attributes = True


class CallDetailResponse(CallResponse):
    transcript: Optional[List[TranscriptMessage]] = None
    analytics: Optional[Dict[str, Any]] = None
    customer_profile: Optional[Dict[str, Any]] = None
    recording_url: Optional[str] = None


class CallListResponse(BaseModel):
    calls: List[CallResponse]
    total: int
    page: int
    page_size: int


# ========================================
# CUSTOMER EXTRACTION MODELS (Structured Output)
# ========================================

class CustomerContactInfo(BaseModel):
    """Contact information extracted from call"""
    name: Optional[str] = Field(None, description="Customer's name if mentioned")
    email: Optional[str] = Field(None, description="Email address if provided")
    phone: Optional[str] = Field(None, description="Phone number if different from caller ID")
    account_id: Optional[str] = Field(None, description="Account or customer ID if mentioned")
    company: Optional[str] = Field(None, description="Company name if B2B customer")


class CustomerContext(BaseModel):
    """Contextual information about the customer"""
    customer_type: CustomerType = Field(CustomerType.UNKNOWN, description="Type of customer based on conversation")
    is_frustrated: bool = Field(False, description="Whether customer showed frustration")
    is_repeat_caller: bool = Field(False, description="Whether customer mentioned calling before")
    previous_issues_mentioned: List[str] = Field(default_factory=list, description="Previous issues customer referenced")
    products_mentioned: List[str] = Field(default_factory=list, description="Products or services discussed")
    competitor_mentions: List[str] = Field(default_factory=list, description="Any competitor products/services mentioned")


class CustomerNeeds(BaseModel):
    """What the customer needs/wants"""
    primary_need: str = Field(..., description="Main reason for the call")
    secondary_needs: List[str] = Field(default_factory=list, description="Additional requests or questions")
    urgency_level: UrgencyLevel = Field(UrgencyLevel.MEDIUM, description="How urgent is the customer's need")
    deadline_mentioned: Optional[str] = Field(None, description="Any deadline or timeframe mentioned")


class CustomerFeedback(BaseModel):
    """Feedback and preferences extracted"""
    pain_points: List[str] = Field(default_factory=list, description="Specific pain points mentioned")
    feature_requests: List[str] = Field(default_factory=list, description="Features customer asked for")
    compliments: List[str] = Field(default_factory=list, description="Positive feedback given")
    complaints: List[str] = Field(default_factory=list, description="Specific complaints made")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions from customer")


class ChurnRisk(BaseModel):
    """Churn risk assessment"""
    risk_level: str = Field("low", description="low, medium, high")
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="0-1 churn probability")
    risk_factors: List[str] = Field(default_factory=list, description="Factors contributing to churn risk")
    retention_actions: List[str] = Field(default_factory=list, description="Recommended retention actions")


class CustomerProfile(BaseModel):
    """Complete customer profile extracted from call"""
    contact_info: CustomerContactInfo = Field(default_factory=CustomerContactInfo)
    context: CustomerContext = Field(default_factory=CustomerContext)
    needs: Optional[CustomerNeeds] = None
    feedback: CustomerFeedback = Field(default_factory=CustomerFeedback)
    churn_risk: ChurnRisk = Field(default_factory=ChurnRisk)

    # Conversation quality
    communication_style: str = Field("neutral", description="formal, casual, technical, emotional")
    language_preference: str = Field("en", description="Detected language")

    # Follow-up
    requires_follow_up: bool = Field(False)
    follow_up_reason: Optional[str] = None
    follow_up_deadline: Optional[str] = None

    # Notes
    special_notes: List[str] = Field(default_factory=list, description="Any special notes about customer")


# ========================================
# ENHANCED ANALYTICS MODELS
# ========================================

class SentimentProgression(BaseModel):
    """Sentiment at a point in time"""
    timestamp: float = Field(..., description="Seconds into the call")
    sentiment: Sentiment
    trigger: Optional[str] = Field(None, description="What caused the sentiment change")


class ConversationFlow(BaseModel):
    """Analysis of conversation structure"""
    opening_quality: float = Field(0.0, ge=0.0, le=100.0, description="How well agent opened the call")
    problem_identification_time: Optional[float] = Field(None, description="Seconds to identify issue")
    resolution_time: Optional[float] = Field(None, description="Seconds to resolve (if resolved)")
    closing_quality: float = Field(0.0, ge=0.0, le=100.0, description="How well agent closed the call")
    dead_air_seconds: float = Field(0.0, description="Total silence/dead air time")
    interruptions_count: int = Field(0, description="Number of interruptions")


class AgentPerformance(BaseModel):
    """Detailed agent performance metrics"""
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    empathy_score: float = Field(0.0, ge=0.0, le=100.0)
    knowledge_score: float = Field(0.0, ge=0.0, le=100.0)
    communication_score: float = Field(0.0, ge=0.0, le=100.0)
    efficiency_score: float = Field(0.0, ge=0.0, le=100.0)

    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    training_recommendations: List[str] = Field(default_factory=list)


class CallAnalytics(BaseModel):
    """Complete call analytics with structured output"""
    # Sentiment
    overall_sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_progression: List[SentimentProgression] = Field(default_factory=list)

    # Classification
    primary_category: str
    secondary_categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list, description="Custom tags for the call")

    # Resolution
    resolution_status: ResolutionStatus
    resolution_notes: Optional[str] = None

    # Predictions
    customer_satisfaction_predicted: float = Field(ge=1.0, le=5.0)
    nps_predicted: int = Field(ge=0, le=10, description="Predicted Net Promoter Score")

    # Intent & Topics
    customer_intent: str
    key_topics: List[str] = Field(default_factory=list)
    questions_asked: List[str] = Field(default_factory=list, description="Questions customer asked")
    questions_unanswered: List[str] = Field(default_factory=list, description="Questions not fully answered")

    # Action Items
    action_items: List[str] = Field(default_factory=list)
    commitments_made: List[str] = Field(default_factory=list, description="Promises agent made")

    # Agent Performance
    agent_performance: AgentPerformance = Field(default_factory=AgentPerformance)

    # Conversation Quality
    conversation_flow: ConversationFlow = Field(default_factory=ConversationFlow)

    # Improvement
    improvement_suggestions: List[str] = Field(default_factory=list)
    knowledge_gaps: List[str] = Field(default_factory=list, description="Topics agent couldn't answer well")

    # Summary
    call_summary: str
    one_line_summary: str = Field("", description="One sentence summary")


# ========================================
# STANDARD DASHBOARD MODELS
# ========================================

class OverviewStats(BaseModel):
    total_calls: int
    avg_duration_seconds: float
    resolution_rate: float
    avg_sentiment_score: float
    calls_today: int
    calls_this_week: int


class SentimentBreakdown(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    mixed: int = 0


class CategoryBreakdown(BaseModel):
    categories: Dict[str, int] = {}


class TrendDataPoint(BaseModel):
    date: str
    calls: int
    avg_sentiment: float
    resolution_rate: float


class TopIssue(BaseModel):
    category: str
    count: int


class RecentCall(BaseModel):
    id: str
    started_at: datetime
    duration: Optional[int] = None
    status: str
    sentiment: Optional[str] = None


class AnalyticsDashboard(BaseModel):
    overview: OverviewStats
    sentiment: SentimentBreakdown
    categories: CategoryBreakdown
    trends: List[TrendDataPoint]
    top_issues: List[TopIssue]
    recent_calls: List[RecentCall]


# ========================================
# CUMULATIVE ANALYTICS MODELS
# ========================================

class CumulativeOverview(BaseModel):
    """All-time cumulative statistics"""
    total_calls: int = 0
    total_duration_seconds: int = 0
    avg_duration_seconds: float = 0.0
    total_resolved: int = 0
    total_escalated: int = 0
    resolution_rate: float = 0.0
    avg_sentiment_score: float = 0.0
    avg_csat: float = 0.0
    avg_agent_score: float = 0.0

    # Time-based
    calls_today: int = 0
    calls_this_week: int = 0
    calls_this_month: int = 0

    # Comparisons
    calls_vs_last_week: float = 0.0  # Percentage change
    resolution_vs_last_week: float = 0.0
    sentiment_vs_last_week: float = 0.0


class CustomerInsightsSummary(BaseModel):
    """Aggregated customer insights"""
    total_unique_customers: int = 0
    repeat_caller_rate: float = 0.0
    avg_calls_per_customer: float = 0.0

    # Top pain points across all calls
    top_pain_points: List[Dict[str, Any]] = Field(default_factory=list)
    # Top feature requests
    top_feature_requests: List[Dict[str, Any]] = Field(default_factory=list)
    # Common complaints
    top_complaints: List[Dict[str, Any]] = Field(default_factory=list)

    # Churn metrics
    high_risk_customers: int = 0
    avg_churn_risk: float = 0.0


class AgentLeaderboard(BaseModel):
    """Agent performance comparison (for multi-agent)"""
    agent_type: str
    total_calls: int
    avg_score: float
    avg_resolution_rate: float
    avg_csat: float


class CumulativeDashboard(BaseModel):
    """Complete cumulative dashboard"""
    overview: CumulativeOverview
    sentiment: SentimentBreakdown
    categories: CategoryBreakdown
    customer_insights: CustomerInsightsSummary
    agent_leaderboard: List[AgentLeaderboard] = Field(default_factory=list)

    # Trends (weekly/monthly)
    weekly_trends: List[TrendDataPoint] = Field(default_factory=list)
    monthly_trends: List[TrendDataPoint] = Field(default_factory=list)

    # Top issues all time
    top_issues_all_time: List[TopIssue] = Field(default_factory=list)

    # Recent activity
    recent_calls: List[RecentCall] = Field(default_factory=list)


# ========================================
# ENHANCED ANALYTICS MODELS
# ========================================

class FeedbackItem(BaseModel):
    """A single feedback item with occurrence count"""
    text: str
    count: int = 1
    category: Optional[str] = None
    first_mentioned: Optional[datetime] = None
    last_mentioned: Optional[datetime] = None


class CustomerProfileSummary(BaseModel):
    """Summary of a customer profile"""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    customer_type: CustomerType = CustomerType.UNKNOWN
    total_calls: int = 0
    avg_satisfaction: float = 0.0
    churn_risk_level: str = "low"
    churn_risk_score: float = 0.0
    last_call_at: Optional[datetime] = None


class CustomerProfileDetail(CustomerProfileSummary):
    """Detailed customer profile"""
    account_id: Optional[str] = None
    company: Optional[str] = None
    communication_style: str = "neutral"
    total_call_duration_seconds: int = 0
    first_call_at: Optional[datetime] = None
    avg_sentiment_score: float = 0.0
    pain_points: List[str] = Field(default_factory=list)
    feature_requests: List[str] = Field(default_factory=list)
    complaints: List[str] = Field(default_factory=list)
    compliments: List[str] = Field(default_factory=list)
    products_mentioned: List[str] = Field(default_factory=list)
    competitor_mentions: List[str] = Field(default_factory=list)
    churn_risk_factors: List[str] = Field(default_factory=list)
    requires_follow_up: bool = False
    follow_up_reason: Optional[str] = None
    special_notes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class AgentPerformanceDetail(BaseModel):
    """Detailed agent performance metrics from a call"""
    call_id: str
    overall_score: float = 0.0
    empathy_score: float = 0.0
    knowledge_score: float = 0.0
    communication_score: float = 0.0
    efficiency_score: float = 0.0
    opening_quality: float = 0.0
    closing_quality: float = 0.0
    problem_identification_time_seconds: Optional[float] = None
    resolution_time_seconds: Optional[float] = None
    dead_air_seconds: float = 0.0
    interruptions_count: int = 0
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    training_recommendations: List[str] = Field(default_factory=list)


class EnhancedCallAnalytics(BaseModel):
    """Complete call analytics with all extracted data"""
    # Basic Info
    call_id: str
    analyzed_at: Optional[datetime] = None

    # Sentiment
    overall_sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_progression: List[SentimentProgression] = Field(default_factory=list)

    # Classification
    primary_category: str
    secondary_categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Resolution
    resolution_status: ResolutionStatus
    resolution_notes: Optional[str] = None

    # Predictions
    customer_satisfaction_predicted: float = Field(ge=1.0, le=5.0)
    nps_predicted: Optional[int] = Field(None, ge=0, le=10)

    # Intent & Topics
    customer_intent: str
    key_topics: List[str] = Field(default_factory=list)
    questions_asked: List[str] = Field(default_factory=list)
    questions_unanswered: List[str] = Field(default_factory=list)

    # Action Items
    action_items: List[str] = Field(default_factory=list)
    commitments_made: List[str] = Field(default_factory=list)

    # Quality
    improvement_suggestions: List[str] = Field(default_factory=list)
    knowledge_gaps: List[str] = Field(default_factory=list)

    # Summary
    call_summary: str
    one_line_summary: Optional[str] = None

    # Agent Performance (embedded)
    agent_performance: Optional[AgentPerformance] = None

    # Conversation Flow (embedded)
    conversation_flow: Optional[ConversationFlow] = None

    # Customer Profile (embedded)
    customer_profile: Optional[CustomerProfile] = None


class EnhancedAnalyticsSummary(BaseModel):
    """Enhanced cumulative analytics with real data"""
    # Period Info
    period_type: str  # daily, weekly, monthly, all_time
    period_start: str
    period_end: str

    # Call Volume
    total_calls: int = 0
    completed_calls: int = 0
    abandoned_calls: int = 0
    escalated_calls: int = 0

    # Duration
    total_duration_seconds: int = 0
    avg_duration_seconds: float = 0.0

    # Resolution
    resolved_calls: int = 0
    first_call_resolution_count: int = 0
    resolution_rate: float = 0.0
    first_call_resolution_rate: float = 0.0

    # Sentiment
    sentiment_breakdown: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    avg_sentiment_score: float = 0.0

    # Customer Satisfaction
    avg_csat_score: float = 0.0
    avg_nps_score: float = 0.0

    # Agent Performance
    avg_agent_score: float = 0.0

    # Customer Risk
    high_risk_customer_count: int = 0
    avg_churn_risk_score: float = 0.0

    # Category Breakdown
    category_breakdown: Dict[str, int] = Field(default_factory=dict)

    # Top Feedback Items
    top_pain_points: List[FeedbackItem] = Field(default_factory=list)
    top_feature_requests: List[FeedbackItem] = Field(default_factory=list)
    top_complaints: List[FeedbackItem] = Field(default_factory=list)
    top_knowledge_gaps: List[FeedbackItem] = Field(default_factory=list)

    # Comparisons (vs previous period)
    calls_change_percent: float = 0.0
    resolution_change_percent: float = 0.0
    sentiment_change_percent: float = 0.0


class CustomerListResponse(BaseModel):
    """Paginated customer list"""
    customers: List[CustomerProfileSummary]
    total: int
    page: int
    page_size: int


class HighRiskCustomer(BaseModel):
    """High risk customer summary"""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    churn_risk_score: float
    churn_risk_factors: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    last_call_at: Optional[datetime] = None
    total_calls: int = 0


class ActionItemSummary(BaseModel):
    """Summary of pending action items"""
    call_id: str
    call_date: datetime
    customer_name: Optional[str] = None
    action_items: List[str]
    commitments_made: List[str]
    follow_up_deadline: Optional[str] = None
