"""
Transcript Analysis Service

Uses Gemini 2.5 Flash via OpenRouter to analyze call transcripts
and extract structured insights including customer profiles.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.llm import chat_completion
from app.core.database import get_supabase
from app.core.config import settings


# ========================================
# ENHANCED ANALYSIS PROMPT WITH CUSTOMER EXTRACTION
# ========================================

ANALYSIS_SYSTEM_PROMPT = """You are an expert customer service analyst and customer intelligence specialist.
Analyze the following call transcript and provide comprehensive structured insights.

Your analysis must be returned as valid JSON with the following structure:

{
  "call_analysis": {
    "overall_sentiment": "positive" | "neutral" | "negative" | "mixed",
    "sentiment_score": <float from -1.0 to 1.0>,
    "sentiment_progression": [
      {"timestamp": <seconds>, "sentiment": "positive" | "neutral" | "negative", "trigger": "<what caused change>"}
    ],
    "primary_category": "<main issue category>",
    "secondary_categories": ["<other categories>"],
    "tags": ["<relevant tags>"],
    "resolution_status": "resolved" | "partially_resolved" | "unresolved" | "escalated" | "follow_up_needed",
    "resolution_notes": "<details about resolution>",
    "customer_satisfaction_predicted": <float from 1.0 to 5.0>,
    "nps_predicted": <int from 0 to 10>,
    "customer_intent": "<what did customer want?>",
    "key_topics": ["<topic1>", "<topic2>"],
    "questions_asked": ["<questions customer asked>"],
    "questions_unanswered": ["<questions not fully answered>"],
    "action_items": ["<follow-ups needed>"],
    "commitments_made": ["<promises agent made>"],
    "improvement_suggestions": ["<how call could be better>"],
    "knowledge_gaps": ["<topics agent struggled with>"],
    "call_summary": "<2-3 sentence summary>",
    "one_line_summary": "<one sentence summary>"
  },
  "customer_profile": {
    "contact_info": {
      "name": "<customer name if mentioned>" | null,
      "email": "<email if provided>" | null,
      "phone": "<phone if mentioned>" | null,
      "account_id": "<account ID if mentioned>" | null,
      "company": "<company name if B2B>" | null
    },
    "context": {
      "customer_type": "new" | "returning" | "vip" | "at_risk" | "unknown",
      "is_frustrated": <boolean>,
      "is_repeat_caller": <boolean>,
      "previous_issues_mentioned": ["<past issues referenced>"],
      "products_mentioned": ["<products/services discussed>"],
      "competitor_mentions": ["<competitors mentioned>"]
    },
    "needs": {
      "primary_need": "<main reason for call>",
      "secondary_needs": ["<other requests>"],
      "urgency_level": "low" | "medium" | "high" | "critical",
      "deadline_mentioned": "<any deadline mentioned>" | null
    },
    "feedback": {
      "pain_points": ["<specific pain points>"],
      "feature_requests": ["<features requested>"],
      "compliments": ["<positive feedback>"],
      "complaints": ["<specific complaints>"],
      "suggestions": ["<suggestions made>"]
    },
    "churn_risk": {
      "risk_level": "low" | "medium" | "high",
      "risk_score": <float from 0.0 to 1.0>,
      "risk_factors": ["<why customer might churn>"],
      "retention_actions": ["<recommended actions>"]
    },
    "communication_style": "formal" | "casual" | "technical" | "emotional",
    "language_preference": "en",
    "requires_follow_up": <boolean>,
    "follow_up_reason": "<why follow-up needed>" | null,
    "follow_up_deadline": "<when to follow up>" | null,
    "special_notes": ["<important notes about customer>"]
  },
  "agent_performance": {
    "overall_score": <float from 0 to 100>,
    "empathy_score": <float from 0 to 100>,
    "knowledge_score": <float from 0 to 100>,
    "communication_score": <float from 0 to 100>,
    "efficiency_score": <float from 0 to 100>,
    "strengths": ["<agent strengths>"],
    "areas_for_improvement": ["<areas to improve>"],
    "training_recommendations": ["<training suggestions>"]
  },
  "conversation_flow": {
    "opening_quality": <float from 0 to 100>,
    "problem_identification_time": <seconds or null>,
    "resolution_time": <seconds or null>,
    "closing_quality": <float from 0 to 100>,
    "dead_air_seconds": <estimated seconds>,
    "interruptions_count": <number>
  }
}

CATEGORY OPTIONS:
- account_access: Login, password, 2FA
- billing: Payments, invoices, refunds, subscriptions
- technical_support: Bugs, errors, how-to
- product_inquiry: Features, pricing, comparisons
- complaint: Service issues, dissatisfaction
- feedback: Suggestions, praise
- general_inquiry: Hours, contact, other
- cancellation: Account/subscription cancellation
- onboarding: New user setup, getting started
- upgrade: Plan upgrades, add-ons

CHURN RISK FACTORS TO CONSIDER:
- Mentions of cancellation or leaving
- Comparison to competitors
- Multiple unresolved issues
- Frustrated tone throughout
- Long wait times mentioned
- Repeated same problem

SCORING GUIDELINES:

Sentiment Score (-1.0 to 1.0):
- -1.0 = Very negative (angry, frustrated throughout)
- 0.0 = Neutral (no strong emotions)
- 1.0 = Very positive (happy, satisfied)

Customer Satisfaction (1-5):
- 5 = Issue resolved quickly, exceeded expectations
- 4 = Satisfied, issue resolved
- 3 = Neutral, issue somewhat addressed
- 2 = Dissatisfied, issue not fully resolved
- 1 = Very dissatisfied, bad experience

Agent Scores (0-100):
- 90-100 = Excellent
- 70-89 = Good
- 50-69 = Average
- 30-49 = Below average
- 0-29 = Poor

Be thorough in extracting customer information. Even small details matter for building customer profiles.
Return ONLY valid JSON, no other text or markdown code blocks."""


# ========================================
# MAIN ANALYSIS FUNCTION
# ========================================

async def analyze_transcript(
    call_id: str,
    transcript_messages: List[Dict[str, Any]],
    full_transcript: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze a call transcript and store the results.
    Returns complete analysis with customer profile.
    """
    try:
        # Format transcript for analysis
        formatted_transcript = format_transcript_for_analysis(transcript_messages, full_transcript)

        if not formatted_transcript or len(formatted_transcript.strip()) < 20:
            print(f"Transcript too short for analysis: {call_id}")
            return None

        # Call LLM for analysis
        analysis_result = await get_llm_analysis(formatted_transcript)

        if not analysis_result:
            print(f"Failed to get LLM analysis for call: {call_id}")
            return None

        # Store analytics in database
        stored = await store_analysis(call_id, analysis_result)

        if stored:
            # Update daily analytics
            await update_daily_analytics(call_id, analysis_result)

        return analysis_result

    except Exception as e:
        print(f"Error analyzing transcript for call {call_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ========================================
# HELPER FUNCTIONS
# ========================================

def format_transcript_for_analysis(
    messages: List[Dict[str, Any]],
    full_transcript: Optional[str] = None
) -> str:
    """Format transcript messages into readable format."""
    if not messages and full_transcript:
        return full_transcript

    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Map VAPI roles
        if role in ("ASSISTANT", "BOT", "AI"):
            role = "AGENT"
        elif role == "USER":
            role = "CUSTOMER"

        time_str = f"[{timestamp}s]" if timestamp else ""
        lines.append(f"{role} {time_str}: {content}")

    return "\n".join(lines)


async def get_llm_analysis(formatted_transcript: str) -> Optional[Dict[str, Any]]:
    """Send transcript to Gemini 2.5 Flash for comprehensive analysis."""
    try:
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this customer service call transcript thoroughly.
Extract all customer information, sentiment, and provide detailed agent performance analysis.

TRANSCRIPT:
{formatted_transcript}

Provide your complete analysis as JSON only."""
            }
        ]

        response = await chat_completion(
            messages=messages,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            model=settings.analysis_model,
            max_tokens=4096,  # Larger for comprehensive analysis
            temperature=0.2  # Lower for consistent structured output
        )

        # Parse JSON from response
        response_text = response.strip()

        # Handle markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        analysis = json.loads(response_text.strip())

        # Validate structure
        if "call_analysis" not in analysis:
            # Try to use top-level as call_analysis (backwards compat)
            if "overall_sentiment" in analysis:
                analysis = {"call_analysis": analysis, "customer_profile": {}, "agent_performance": {}}

        return analysis

    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as JSON: {e}")
        print(f"Response preview: {response[:500] if response else 'None'}")
        return None
    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        return None


async def store_analysis(call_id: str, analysis: Dict[str, Any]) -> bool:
    """Store the analysis results in the database."""
    try:
        supabase = get_supabase()

        # Extract sections
        call_analysis = analysis.get("call_analysis", analysis)
        customer_profile = analysis.get("customer_profile", {})
        agent_performance = analysis.get("agent_performance", {})
        conversation_flow = analysis.get("conversation_flow", {})

        record = {
            "call_id": call_id,

            # Basic sentiment
            "overall_sentiment": call_analysis.get("overall_sentiment", "neutral"),
            "sentiment_score": call_analysis.get("sentiment_score", 0.0),
            "sentiment_progression": call_analysis.get("sentiment_progression", []),

            # Classification
            "primary_category": call_analysis.get("primary_category", "general_inquiry"),
            "secondary_categories": call_analysis.get("secondary_categories", []),

            # Resolution
            "resolution_status": call_analysis.get("resolution_status", "unresolved"),

            # Predictions
            "customer_satisfaction_predicted": call_analysis.get("customer_satisfaction_predicted", 3.0),
            "agent_performance_score": agent_performance.get("overall_score", 50.0),

            # Intent & Topics
            "customer_intent": call_analysis.get("customer_intent", ""),
            "key_topics": call_analysis.get("key_topics", []),
            "action_items": call_analysis.get("action_items", []),
            "improvement_suggestions": call_analysis.get("improvement_suggestions", []),

            # Summary
            "call_summary": call_analysis.get("call_summary", ""),

            # Analysis metadata
            "analysis_model": settings.analysis_model,
            "analysis_version": "2.0"
        }

        # Insert analytics
        supabase.table("supportiq_call_analytics").insert(record).execute()

        # Store customer profile separately if we have a customer_profiles table
        # For now, we'll add it to the call record metadata
        if customer_profile:
            try:
                supabase.table("supportiq_voice_calls").update({
                    "caller_phone": customer_profile.get("contact_info", {}).get("phone"),
                }).eq("id", call_id).execute()
            except:
                pass

        return True

    except Exception as e:
        print(f"Error storing analysis: {e}")
        return False


async def update_daily_analytics(call_id: str, analysis: Dict[str, Any]) -> bool:
    """Update the daily aggregated analytics."""
    try:
        supabase = get_supabase()

        # Get call date
        call_result = supabase.table("supportiq_voice_calls").select(
            "started_at, duration_seconds"
        ).eq("id", call_id).execute()

        if not call_result.data:
            return False

        started_at = call_result.data[0]["started_at"]
        if isinstance(started_at, str):
            call_date = datetime.fromisoformat(
                started_at.replace("Z", "+00:00")
            ).date().isoformat()
        else:
            call_date = started_at.date().isoformat()

        duration = call_result.data[0].get("duration_seconds", 0) or 0

        # Extract values
        call_analysis = analysis.get("call_analysis", analysis)
        sentiment = call_analysis.get("overall_sentiment", "neutral")
        resolution = call_analysis.get("resolution_status", "unresolved")
        category = call_analysis.get("primary_category", "general_inquiry")

        # Get or create daily record
        existing = supabase.table("supportiq_analytics_daily").select("*").eq(
            "date", call_date
        ).is_("user_id", "null").execute()

        if existing.data:
            record = existing.data[0]
            new_total = record["total_calls"] + 1
            new_duration = record["total_duration_seconds"] + duration

            updates = {
                "total_calls": new_total,
                "completed_calls": record["completed_calls"] + 1,
                "total_duration_seconds": new_duration,
                "avg_duration_seconds": new_duration / new_total,
                "resolved_calls": record["resolved_calls"] + (1 if resolution == "resolved" else 0),
                "escalated_calls": record["escalated_calls"] + (1 if resolution == "escalated" else 0),
                "positive_calls": record["positive_calls"] + (1 if sentiment == "positive" else 0),
                "neutral_calls": record["neutral_calls"] + (1 if sentiment == "neutral" else 0),
                "negative_calls": record["negative_calls"] + (1 if sentiment == "negative" else 0),
                "resolution_rate": (record["resolved_calls"] + (1 if resolution == "resolved" else 0)) / new_total * 100,
            }

            categories = record.get("category_breakdown", {}) or {}
            categories[category] = categories.get(category, 0) + 1
            updates["category_breakdown"] = categories

            supabase.table("supportiq_analytics_daily").update(updates).eq("id", record["id"]).execute()
        else:
            new_record = {
                "date": call_date,
                "user_id": None,
                "total_calls": 1,
                "completed_calls": 1,
                "abandoned_calls": 0,
                "total_duration_seconds": duration,
                "avg_duration_seconds": float(duration),
                "resolved_calls": 1 if resolution == "resolved" else 0,
                "escalated_calls": 1 if resolution == "escalated" else 0,
                "resolution_rate": 100.0 if resolution == "resolved" else 0.0,
                "positive_calls": 1 if sentiment == "positive" else 0,
                "neutral_calls": 1 if sentiment == "neutral" else 0,
                "negative_calls": 1 if sentiment == "negative" else 0,
                "avg_sentiment_score": call_analysis.get("sentiment_score", 0.0),
                "category_breakdown": {category: 1}
            }
            supabase.table("supportiq_analytics_daily").insert(new_record).execute()

        return True

    except Exception as e:
        print(f"Error updating daily analytics: {e}")
        return False


# ========================================
# CUSTOMER PROFILE EXTRACTION (STANDALONE)
# ========================================

async def extract_customer_profile(
    transcript_messages: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Extract just the customer profile from a transcript.
    Useful for updating CRM or customer database.
    """
    formatted = format_transcript_for_analysis(transcript_messages)

    customer_prompt = """Extract customer information from this call transcript.
Focus on:
- Contact details (name, email, phone, account ID)
- Customer context (type, frustration, previous issues)
- Needs and urgency
- Feedback (pain points, feature requests, complaints)
- Churn risk assessment

Return as JSON with the customer_profile structure only."""

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": f"{customer_prompt}\n\nTRANSCRIPT:\n{formatted}"}],
            model=settings.analysis_model,
            max_tokens=2048,
            temperature=0.2
        )

        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        return json.loads(response_text)

    except Exception as e:
        print(f"Error extracting customer profile: {e}")
        return None


# ========================================
# BATCH / UTILITY FUNCTIONS
# ========================================

async def reanalyze_call(call_id: str) -> Optional[Dict[str, Any]]:
    """Re-analyze an existing call with the enhanced analysis."""
    supabase = get_supabase()

    transcript_result = supabase.table("supportiq_call_transcripts").select(
        "transcript"
    ).eq("call_id", call_id).execute()

    if not transcript_result.data:
        return None

    messages = transcript_result.data[0].get("transcript", [])

    # Delete existing analysis
    supabase.table("supportiq_call_analytics").delete().eq("call_id", call_id).execute()

    return await analyze_transcript(call_id, messages)
