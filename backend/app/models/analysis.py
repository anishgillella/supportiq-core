"""
Pydantic models for transcript analysis structured output.

These models define the expected structure of the LLM analysis response,
providing type safety, validation, and automatic JSON schema generation.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ========================================
# SENTIMENT TYPES
# ========================================

SentimentType = Literal["positive", "neutral", "negative", "mixed"]
ResolutionStatus = Literal["resolved", "partially_resolved", "unresolved", "escalated", "follow_up_needed"]
CustomerType = Literal["new", "returning", "vip", "at_risk", "unknown"]
UrgencyLevel = Literal["low", "medium", "high", "critical"]
ChurnRiskLevel = Literal["low", "medium", "high"]
CommunicationStyle = Literal["formal", "casual", "technical", "emotional", "neutral"]


# ========================================
# NESTED MODELS
# ========================================

class SentimentProgression(BaseModel):
    """Tracks sentiment changes throughout the call."""
    timestamp: int = Field(description="Seconds into the call")
    sentiment: SentimentType = Field(description="Sentiment at this point")
    trigger: Optional[str] = Field(default=None, description="What caused the sentiment change")


class ContactInfo(BaseModel):
    """Customer contact information extracted from call."""
    name: Optional[str] = Field(default=None, description="Customer name if mentioned")
    email: Optional[str] = Field(default=None, description="Email if provided")
    phone: Optional[str] = Field(default=None, description="Phone number if mentioned")
    account_id: Optional[str] = Field(default=None, description="Account ID if mentioned")
    company: Optional[str] = Field(default=None, description="Company name for B2B customers")


class CustomerContext(BaseModel):
    """Context about the customer from the call."""
    customer_type: CustomerType = Field(default="unknown", description="Type of customer")
    is_frustrated: bool = Field(default=False, description="Whether customer showed frustration")
    is_repeat_caller: bool = Field(default=False, description="Whether this is a repeat issue")
    previous_issues_mentioned: List[str] = Field(default_factory=list, description="Past issues referenced")
    products_mentioned: List[str] = Field(default_factory=list, description="Products/services discussed")
    competitor_mentions: List[str] = Field(default_factory=list, description="Competitors mentioned")


class CustomerNeeds(BaseModel):
    """Customer needs identified during the call."""
    primary_need: str = Field(default="", description="Main reason for call")
    secondary_needs: List[str] = Field(default_factory=list, description="Other requests")
    urgency_level: UrgencyLevel = Field(default="medium", description="How urgent the request is")
    deadline_mentioned: Optional[str] = Field(default=None, description="Any deadline mentioned")


class CustomerFeedback(BaseModel):
    """Feedback extracted from the call."""
    pain_points: List[str] = Field(default_factory=list, description="Specific pain points mentioned")
    feature_requests: List[str] = Field(default_factory=list, description="Features customer requested")
    compliments: List[str] = Field(default_factory=list, description="Positive feedback given")
    complaints: List[str] = Field(default_factory=list, description="Specific complaints made")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions from customer")


class ChurnRisk(BaseModel):
    """Churn risk assessment for the customer."""
    risk_level: ChurnRiskLevel = Field(default="low", description="Overall churn risk level")
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Churn risk score 0-1")
    risk_factors: List[str] = Field(default_factory=list, description="Factors contributing to churn risk")
    retention_actions: List[str] = Field(default_factory=list, description="Recommended retention actions")


class ConversationFlow(BaseModel):
    """Metrics about the conversation flow."""
    opening_quality: float = Field(default=50.0, ge=0, le=100, description="Quality of call opening 0-100")
    problem_identification_time: Optional[int] = Field(default=None, description="Seconds to identify problem")
    resolution_time: Optional[int] = Field(default=None, description="Seconds to resolve")
    closing_quality: float = Field(default=50.0, ge=0, le=100, description="Quality of call closing 0-100")
    dead_air_seconds: float = Field(default=0.0, ge=0, description="Estimated dead air time")
    interruptions_count: int = Field(default=0, ge=0, description="Number of interruptions")


# ========================================
# MAIN ANALYSIS MODELS
# ========================================

class CallAnalysis(BaseModel):
    """Main call analysis results."""
    # Sentiment
    overall_sentiment: SentimentType = Field(default="neutral", description="Overall call sentiment")
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0, description="Sentiment score -1 to 1")
    sentiment_progression: List[SentimentProgression] = Field(default_factory=list, description="Sentiment changes over time")

    # Classification
    primary_category: str = Field(default="general_inquiry", description="Main issue category")
    secondary_categories: List[str] = Field(default_factory=list, description="Additional categories")
    tags: List[str] = Field(default_factory=list, description="Relevant tags")

    # Resolution
    resolution_status: ResolutionStatus = Field(default="unresolved", description="How the call was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Details about resolution")

    # Predictions
    customer_satisfaction_predicted: float = Field(default=3.0, ge=1.0, le=5.0, description="Predicted CSAT 1-5")
    nps_predicted: Optional[int] = Field(default=None, ge=0, le=10, description="Predicted NPS 0-10")

    # Content analysis
    customer_intent: str = Field(default="", description="What did customer want?")
    key_topics: List[str] = Field(default_factory=list, description="Main topics discussed")
    questions_asked: List[str] = Field(default_factory=list, description="Questions customer asked")
    questions_unanswered: List[str] = Field(default_factory=list, description="Questions not fully answered")

    # Action items
    action_items: List[str] = Field(default_factory=list, description="Follow-ups needed")
    commitments_made: List[str] = Field(default_factory=list, description="Promises agent made")

    # Quality
    improvement_suggestions: List[str] = Field(default_factory=list, description="How call could be better")
    knowledge_gaps: List[str] = Field(default_factory=list, description="Topics agent struggled with")

    # Summary
    call_summary: str = Field(default="", description="2-3 sentence summary")
    one_line_summary: str = Field(default="", description="One sentence summary")


class CustomerProfile(BaseModel):
    """Customer profile extracted from the call."""
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    context: CustomerContext = Field(default_factory=CustomerContext)
    needs: CustomerNeeds = Field(default_factory=CustomerNeeds)
    feedback: CustomerFeedback = Field(default_factory=CustomerFeedback)
    churn_risk: ChurnRisk = Field(default_factory=ChurnRisk)

    communication_style: CommunicationStyle = Field(default="neutral", description="Customer's communication style")
    language_preference: str = Field(default="en", description="Preferred language")
    requires_follow_up: bool = Field(default=False, description="Whether follow-up is needed")
    follow_up_reason: Optional[str] = Field(default=None, description="Why follow-up is needed")
    follow_up_deadline: Optional[str] = Field(default=None, description="When to follow up")
    special_notes: List[str] = Field(default_factory=list, description="Important notes about customer")


class AgentPerformance(BaseModel):
    """Agent performance metrics from the call."""
    overall_score: float = Field(default=50.0, ge=0, le=100, description="Overall performance 0-100")
    empathy_score: float = Field(default=50.0, ge=0, le=100, description="Empathy shown 0-100")
    knowledge_score: float = Field(default=50.0, ge=0, le=100, description="Product knowledge 0-100")
    communication_score: float = Field(default=50.0, ge=0, le=100, description="Communication clarity 0-100")
    efficiency_score: float = Field(default=50.0, ge=0, le=100, description="Time efficiency 0-100")

    strengths: List[str] = Field(default_factory=list, description="Agent strengths observed")
    areas_for_improvement: List[str] = Field(default_factory=list, description="Areas to improve")
    training_recommendations: List[str] = Field(default_factory=list, description="Suggested training")


# ========================================
# COMPLETE ANALYSIS RESPONSE
# ========================================

class TranscriptAnalysisResponse(BaseModel):
    """Complete transcript analysis response from LLM."""
    call_analysis: CallAnalysis = Field(default_factory=CallAnalysis)
    customer_profile: CustomerProfile = Field(default_factory=CustomerProfile)
    agent_performance: AgentPerformance = Field(default_factory=AgentPerformance)
    conversation_flow: ConversationFlow = Field(default_factory=ConversationFlow)


# ========================================
# SCHEMA GENERATION
# ========================================

def get_analysis_json_schema() -> str:
    """
    Generate JSON schema from Pydantic models for use in LLM prompts.
    This ensures the schema stays in sync with the models.
    """
    import json
    schema = TranscriptAnalysisResponse.model_json_schema()
    return json.dumps(schema, indent=2)


def get_analysis_schema_summary() -> str:
    """
    Generate a human-readable summary of the expected output structure.
    Useful for system prompts.
    """
    return """
{
  "call_analysis": {
    "overall_sentiment": "positive" | "neutral" | "negative" | "mixed",
    "sentiment_score": float (-1.0 to 1.0),
    "sentiment_progression": [{"timestamp": int, "sentiment": string, "trigger": string}],
    "primary_category": string,
    "secondary_categories": [string],
    "tags": [string],
    "resolution_status": "resolved" | "partially_resolved" | "unresolved" | "escalated" | "follow_up_needed",
    "resolution_notes": string | null,
    "customer_satisfaction_predicted": float (1.0 to 5.0),
    "nps_predicted": int (0 to 10) | null,
    "customer_intent": string,
    "key_topics": [string],
    "questions_asked": [string],
    "questions_unanswered": [string],
    "action_items": [string],
    "commitments_made": [string],
    "improvement_suggestions": [string],
    "knowledge_gaps": [string],
    "call_summary": string,
    "one_line_summary": string
  },
  "customer_profile": {
    "contact_info": {
      "name": string | null,
      "email": string | null,
      "phone": string | null,
      "account_id": string | null,
      "company": string | null
    },
    "context": {
      "customer_type": "new" | "returning" | "vip" | "at_risk" | "unknown",
      "is_frustrated": boolean,
      "is_repeat_caller": boolean,
      "previous_issues_mentioned": [string],
      "products_mentioned": [string],
      "competitor_mentions": [string]
    },
    "needs": {
      "primary_need": string,
      "secondary_needs": [string],
      "urgency_level": "low" | "medium" | "high" | "critical",
      "deadline_mentioned": string | null
    },
    "feedback": {
      "pain_points": [string],
      "feature_requests": [string],
      "compliments": [string],
      "complaints": [string],
      "suggestions": [string]
    },
    "churn_risk": {
      "risk_level": "low" | "medium" | "high",
      "risk_score": float (0.0 to 1.0),
      "risk_factors": [string],
      "retention_actions": [string]
    },
    "communication_style": "formal" | "casual" | "technical" | "emotional",
    "language_preference": string,
    "requires_follow_up": boolean,
    "follow_up_reason": string | null,
    "follow_up_deadline": string | null,
    "special_notes": [string]
  },
  "agent_performance": {
    "overall_score": float (0 to 100),
    "empathy_score": float (0 to 100),
    "knowledge_score": float (0 to 100),
    "communication_score": float (0 to 100),
    "efficiency_score": float (0 to 100),
    "strengths": [string],
    "areas_for_improvement": [string],
    "training_recommendations": [string]
  },
  "conversation_flow": {
    "opening_quality": float (0 to 100),
    "problem_identification_time": int | null,
    "resolution_time": int | null,
    "closing_quality": float (0 to 100),
    "dead_air_seconds": float,
    "interruptions_count": int
  }
}
"""
