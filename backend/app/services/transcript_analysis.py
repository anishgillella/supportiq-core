"""
Transcript Analysis Service

Uses Gemini 2.5 Flash via OpenRouter to analyze call transcripts
and extract structured insights including customer profiles.

Enhanced version with Pydantic models for type-safe structured output.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import ValidationError

from app.services.llm import chat_completion
from app.core.database import get_supabase
from app.core.config import settings
from app.models.analysis import (
    TranscriptAnalysisResponse,
    CallAnalysis,
    CustomerProfile,
    AgentPerformance,
    ConversationFlow,
    get_analysis_schema_summary,
)


# ========================================
# SYSTEM PROMPT WITH PYDANTIC-GENERATED SCHEMA
# ========================================

def get_analysis_system_prompt() -> str:
    """
    Generate the system prompt with schema from Pydantic models.
    This ensures the prompt schema stays in sync with the code.
    """
    schema = get_analysis_schema_summary()

    return f"""You are an expert customer service analyst and customer intelligence specialist.
Analyze the following call transcript and provide comprehensive structured insights.

Your analysis must be returned as valid JSON matching this exact structure:
{schema}

CATEGORY OPTIONS for primary_category:
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
    full_transcript: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze a call transcript and store the results.
    Returns complete analysis with customer profile as a dictionary.

    Args:
        call_id: The internal call ID
        transcript_messages: List of transcript messages
        full_transcript: Optional full transcript text
        user_id: The user ID for customer profile association
        user_email: The logged-in user's email (for customer profile)
        user_name: The logged-in user's name/company (for customer profile)

    Returns:
        Dict containing the validated analysis results, or None if analysis failed.
    """
    try:
        # Format transcript for analysis
        formatted_transcript = format_transcript_for_analysis(transcript_messages, full_transcript)

        if not formatted_transcript or len(formatted_transcript.strip()) < 20:
            print(f"Transcript too short for analysis: {call_id}")
            return None

        # Call LLM for analysis - returns validated Pydantic model
        analysis_model = await get_llm_analysis(formatted_transcript)

        if not analysis_model:
            print(f"Failed to get LLM analysis for call: {call_id}")
            return None

        # Convert Pydantic model to dict for storage and return
        # Using model_dump() preserves all nested structures
        analysis_result = analysis_model.model_dump()

        # Store all analytics data (pass user details for customer profile creation)
        stored = await store_enhanced_analysis(
            call_id, analysis_result, user_id, user_email, user_name
        )

        if stored:
            # Update daily analytics
            await update_daily_analytics(call_id, analysis_result)

            # Update feedback aggregation
            await update_feedback_aggregation(analysis_result, user_id, call_id)

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


async def get_llm_analysis(formatted_transcript: str) -> Optional[TranscriptAnalysisResponse]:
    """
    Send transcript to LLM for comprehensive analysis.

    Returns a validated TranscriptAnalysisResponse Pydantic model,
    ensuring type safety and data validation.
    """
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

        # Get dynamic system prompt with Pydantic-generated schema
        system_prompt = get_analysis_system_prompt()

        response = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            model=settings.analysis_model,
            max_tokens=4096,  # Larger for comprehensive analysis
            temperature=0.2,  # Lower for consistent structured output
            json_mode=True  # Force JSON output for reliable parsing
        )

        # Parse JSON from response
        response_text = response.strip()

        # Handle markdown code blocks (shouldn't happen with json_mode but just in case)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        raw_analysis = json.loads(response_text.strip())

        # Handle backwards compatibility - if top-level has sentiment, wrap it
        if "call_analysis" not in raw_analysis and "overall_sentiment" in raw_analysis:
            raw_analysis = {
                "call_analysis": raw_analysis,
                "customer_profile": {},
                "agent_performance": {},
                "conversation_flow": {}
            }

        # Validate and parse with Pydantic model
        # This ensures all fields have correct types and valid values
        validated_analysis = TranscriptAnalysisResponse.model_validate(raw_analysis)

        print(f"[ANALYSIS] Successfully validated analysis with Pydantic")
        return validated_analysis

    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as JSON: {e}")
        print(f"Response preview: {response[:500] if response else 'None'}")
        return None
    except ValidationError as e:
        print(f"Pydantic validation failed: {e}")
        # Return a default model with whatever we could parse
        try:
            # Try to create a partial model with defaults for invalid fields
            return TranscriptAnalysisResponse()
        except Exception:
            return None
    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


async def store_enhanced_analysis(
    call_id: str,
    analysis: Dict[str, Any],
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None
) -> bool:
    """Store the complete analysis results in the database."""
    try:
        supabase = get_supabase()

        # Extract sections
        call_analysis = analysis.get("call_analysis", analysis)
        customer_profile = analysis.get("customer_profile", {})
        agent_performance = analysis.get("agent_performance", {})
        conversation_flow = analysis.get("conversation_flow", {})

        # ========================================
        # 1. Store Call Analytics
        # ========================================
        analytics_record = {
            "call_id": call_id,

            # Basic sentiment
            "overall_sentiment": call_analysis.get("overall_sentiment", "neutral"),
            "sentiment_score": call_analysis.get("sentiment_score", 0.0),
            "sentiment_progression": call_analysis.get("sentiment_progression", []),

            # Classification
            "primary_category": call_analysis.get("primary_category", "general_inquiry"),
            "secondary_categories": call_analysis.get("secondary_categories", []),
            "tags": call_analysis.get("tags", []),

            # Resolution
            "resolution_status": call_analysis.get("resolution_status", "unresolved"),
            "resolution_notes": call_analysis.get("resolution_notes"),

            # Predictions
            "customer_satisfaction_predicted": call_analysis.get("customer_satisfaction_predicted", 3.0),
            "nps_predicted": call_analysis.get("nps_predicted"),
            "agent_performance_score": agent_performance.get("overall_score", 50.0),

            # Intent & Topics
            "customer_intent": call_analysis.get("customer_intent", ""),
            "key_topics": call_analysis.get("key_topics", []),
            "questions_asked": call_analysis.get("questions_asked", []),
            "questions_unanswered": call_analysis.get("questions_unanswered", []),

            # Actions
            "action_items": call_analysis.get("action_items", []),
            "commitments_made": call_analysis.get("commitments_made", []),

            # Quality
            "improvement_suggestions": call_analysis.get("improvement_suggestions", []),
            "knowledge_gaps": call_analysis.get("knowledge_gaps", []),

            # Summary
            "call_summary": call_analysis.get("call_summary", ""),
            "one_line_summary": call_analysis.get("one_line_summary", ""),

            # Analysis metadata
            "analysis_model": settings.analysis_model,
            "analysis_version": "2.0"
        }

        # Insert analytics
        supabase.table("supportiq_call_analytics").insert(analytics_record).execute()
        print(f"Stored call analytics for {call_id}")

        # ========================================
        # 2. Store Agent Performance
        # ========================================
        if agent_performance:
            perf_record = {
                "call_id": call_id,
                "overall_score": agent_performance.get("overall_score", 0.0),
                "empathy_score": agent_performance.get("empathy_score", 0.0),
                "knowledge_score": agent_performance.get("knowledge_score", 0.0),
                "communication_score": agent_performance.get("communication_score", 0.0),
                "efficiency_score": agent_performance.get("efficiency_score", 0.0),
                "opening_quality": conversation_flow.get("opening_quality", 0.0),
                "closing_quality": conversation_flow.get("closing_quality", 0.0),
                "problem_identification_time_seconds": conversation_flow.get("problem_identification_time"),
                "resolution_time_seconds": conversation_flow.get("resolution_time"),
                "dead_air_seconds": conversation_flow.get("dead_air_seconds", 0.0),
                "interruptions_count": conversation_flow.get("interruptions_count", 0),
                "strengths": agent_performance.get("strengths", []),
                "areas_for_improvement": agent_performance.get("areas_for_improvement", []),
                "training_recommendations": agent_performance.get("training_recommendations", [])
            }

            try:
                supabase.table("supportiq_agent_performance").insert(perf_record).execute()
                print(f"Stored agent performance for {call_id}")
            except Exception as e:
                print(f"Error storing agent performance (table may not exist): {e}")

        # ========================================
        # 3. Update/Create Customer Profile
        # ========================================
        if customer_profile and user_id:
            await update_customer_profile(
                customer_profile, user_id, call_id, user_email, user_name
            )

        # ========================================
        # 4. Update Voice Call Record
        # ========================================
        contact_info = customer_profile.get("contact_info", {})
        if contact_info:
            update_data = {}
            if contact_info.get("phone"):
                update_data["caller_phone"] = contact_info["phone"]

            if update_data:
                try:
                    supabase.table("supportiq_voice_calls").update(update_data).eq("id", call_id).execute()
                except Exception as e:
                    print(f"Error updating call record: {e}")

        return True

    except Exception as e:
        print(f"Error storing enhanced analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


async def update_customer_profile(
    customer_profile: Dict[str, Any],
    user_id: str,
    call_id: str,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None
) -> Optional[str]:
    """
    Update or create a customer profile from call analysis.

    Args:
        customer_profile: Extracted customer profile from AI analysis
        user_id: The user ID for data isolation
        call_id: The call ID to associate with this profile
        user_email: Email of the logged-in user (takes precedence)
        user_name: Name/company of the logged-in user (takes precedence)
    """
    try:
        supabase = get_supabase()

        contact_info = customer_profile.get("contact_info", {})
        context = customer_profile.get("context", {})
        needs = customer_profile.get("needs", {})
        feedback = customer_profile.get("feedback", {})
        churn_risk = customer_profile.get("churn_risk", {})

        # Use logged-in user's email/name if available, otherwise fall back to AI-extracted data
        # This ensures the customer profile is associated with the actual caller
        email = user_email or contact_info.get("email")
        name = user_name or contact_info.get("name")
        phone = contact_info.get("phone")
        account_id = contact_info.get("account_id")

        print(f"[CUSTOMER PROFILE] Creating/updating profile: email={email}, name={name}, phone={phone}")

        existing = None

        if email:
            result = supabase.table("supportiq_customer_profiles").select("*").eq(
                "user_id", user_id
            ).eq("email", email).execute()
            if result.data:
                existing = result.data[0]

        if not existing and phone:
            result = supabase.table("supportiq_customer_profiles").select("*").eq(
                "user_id", user_id
            ).eq("phone", phone).execute()
            if result.data:
                existing = result.data[0]

        if not existing and account_id:
            result = supabase.table("supportiq_customer_profiles").select("*").eq(
                "user_id", user_id
            ).eq("account_id", account_id).execute()
            if result.data:
                existing = result.data[0]

        # Get call data for duration
        call_result = supabase.table("supportiq_voice_calls").select(
            "duration_seconds, started_at"
        ).eq("id", call_id).execute()
        call_data = call_result.data[0] if call_result.data else {}
        call_duration = call_data.get("duration_seconds", 0) or 0
        call_started_at = call_data.get("started_at")

        # Get analytics for satisfaction score
        analytics_result = supabase.table("supportiq_call_analytics").select(
            "customer_satisfaction_predicted, sentiment_score"
        ).eq("call_id", call_id).execute()
        analytics_data = analytics_result.data[0] if analytics_result.data else {}
        satisfaction = analytics_data.get("customer_satisfaction_predicted", 3.0)
        sentiment = analytics_data.get("sentiment_score", 0.0)

        if existing:
            # Update existing profile
            new_total_calls = existing.get("total_calls", 0) + 1
            new_total_duration = existing.get("total_call_duration_seconds", 0) + call_duration

            # Compute new averages
            old_avg_satisfaction = existing.get("avg_satisfaction_score", 0.0)
            new_avg_satisfaction = ((old_avg_satisfaction * (new_total_calls - 1)) + satisfaction) / new_total_calls

            old_avg_sentiment = existing.get("avg_sentiment_score", 0.0)
            new_avg_sentiment = ((old_avg_sentiment * (new_total_calls - 1)) + sentiment) / new_total_calls

            # Merge arrays
            existing_pain_points = existing.get("pain_points", []) or []
            existing_feature_requests = existing.get("feature_requests", []) or []
            existing_complaints = existing.get("complaints", []) or []
            existing_compliments = existing.get("compliments", []) or []
            existing_products = existing.get("products_mentioned", []) or []
            existing_competitors = existing.get("competitor_mentions", []) or []
            existing_notes = existing.get("special_notes", []) or []
            existing_risk_factors = existing.get("churn_risk_factors", []) or []

            update_data = {
                "total_calls": new_total_calls,
                "total_call_duration_seconds": new_total_duration,
                "last_call_at": call_started_at,
                "avg_satisfaction_score": new_avg_satisfaction,
                "avg_sentiment_score": new_avg_sentiment,
                "customer_type": context.get("customer_type", existing.get("customer_type", "unknown")),
                "communication_style": customer_profile.get("communication_style", existing.get("communication_style", "neutral")),
                "churn_risk_level": churn_risk.get("risk_level", existing.get("churn_risk_level", "low")),
                "churn_risk_score": churn_risk.get("risk_score", existing.get("churn_risk_score", 0.0)),
                "requires_follow_up": customer_profile.get("requires_follow_up", False),
                "follow_up_reason": customer_profile.get("follow_up_reason"),
                # Merge arrays (deduplicate)
                "pain_points": list(set(existing_pain_points + feedback.get("pain_points", []))),
                "feature_requests": list(set(existing_feature_requests + feedback.get("feature_requests", []))),
                "complaints": list(set(existing_complaints + feedback.get("complaints", []))),
                "compliments": list(set(existing_compliments + feedback.get("compliments", []))),
                "products_mentioned": list(set(existing_products + context.get("products_mentioned", []))),
                "competitor_mentions": list(set(existing_competitors + context.get("competitor_mentions", []))),
                "special_notes": list(set(existing_notes + customer_profile.get("special_notes", []))),
                "churn_risk_factors": list(set(existing_risk_factors + churn_risk.get("risk_factors", [])))
            }

            # Update name if not set (use user_name if provided, else AI-extracted)
            if not existing.get("name") and name:
                update_data["name"] = name
            if not existing.get("company") and contact_info.get("company"):
                update_data["company"] = contact_info["company"]

            supabase.table("supportiq_customer_profiles").update(update_data).eq(
                "id", existing["id"]
            ).execute()

            print(f"Updated customer profile {existing['id']}")
            return existing["id"]

        else:
            # Create new profile (only if we have some identifier)
            if not (email or phone or account_id):
                print("No identifier found for customer profile, skipping creation")
                return None

            new_profile = {
                "user_id": user_id,
                "name": name,  # Uses user_name if provided, else AI-extracted
                "email": email,  # Uses user_email if provided, else AI-extracted
                "phone": phone,
                "account_id": account_id,
                "company": contact_info.get("company"),
                "customer_type": context.get("customer_type", "unknown"),
                "communication_style": customer_profile.get("communication_style", "neutral"),
                "language_preference": customer_profile.get("language_preference", "en"),
                "total_calls": 1,
                "total_call_duration_seconds": call_duration,
                "first_call_at": call_started_at,
                "last_call_at": call_started_at,
                "avg_satisfaction_score": satisfaction,
                "avg_sentiment_score": sentiment,
                "churn_risk_level": churn_risk.get("risk_level", "low"),
                "churn_risk_score": churn_risk.get("risk_score", 0.0),
                "churn_risk_factors": churn_risk.get("risk_factors", []),
                "pain_points": feedback.get("pain_points", []),
                "feature_requests": feedback.get("feature_requests", []),
                "complaints": feedback.get("complaints", []),
                "compliments": feedback.get("compliments", []),
                "products_mentioned": context.get("products_mentioned", []),
                "competitor_mentions": context.get("competitor_mentions", []),
                "requires_follow_up": customer_profile.get("requires_follow_up", False),
                "follow_up_reason": customer_profile.get("follow_up_reason"),
                "special_notes": customer_profile.get("special_notes", [])
            }

            # Remove None values
            new_profile = {k: v for k, v in new_profile.items() if v is not None}

            try:
                result = supabase.table("supportiq_customer_profiles").insert(new_profile).execute()
                if result.data:
                    print(f"Created customer profile {result.data[0]['id']}")
                    return result.data[0]["id"]
            except Exception as e:
                print(f"Error creating customer profile (table may not exist): {e}")

            return None

    except Exception as e:
        print(f"Error updating customer profile: {e}")
        import traceback
        traceback.print_exc()
        return None


async def update_feedback_aggregation(
    analysis: Dict[str, Any],
    user_id: Optional[str],
    call_id: str
) -> bool:
    """Update the feedback aggregation table with new feedback items."""
    try:
        if not user_id:
            return False

        supabase = get_supabase()

        customer_profile = analysis.get("customer_profile", {})
        call_analysis = analysis.get("call_analysis", {})
        feedback = customer_profile.get("feedback", {})

        # Feedback types to aggregate
        feedback_items = [
            ("pain_point", feedback.get("pain_points", [])),
            ("feature_request", feedback.get("feature_requests", [])),
            ("complaint", feedback.get("complaints", [])),
            ("compliment", feedback.get("compliments", [])),
            ("knowledge_gap", call_analysis.get("knowledge_gaps", []))
        ]

        category = call_analysis.get("primary_category", "general_inquiry")

        for feedback_type, items in feedback_items:
            for item_text in items:
                if not item_text or len(item_text.strip()) < 3:
                    continue

                item_text = item_text.strip()

                # Check if exists
                existing = supabase.table("supportiq_feedback_aggregation").select("*").eq(
                    "user_id", user_id
                ).eq("feedback_type", feedback_type).eq("feedback_text", item_text).execute()

                if existing.data:
                    # Update existing
                    record = existing.data[0]
                    call_ids = record.get("call_ids", []) or []
                    if call_id not in call_ids:
                        call_ids.append(call_id)

                    supabase.table("supportiq_feedback_aggregation").update({
                        "occurrence_count": record.get("occurrence_count", 0) + 1,
                        "last_mentioned_at": datetime.utcnow().isoformat(),
                        "call_ids": call_ids
                    }).eq("id", record["id"]).execute()
                else:
                    # Create new
                    try:
                        supabase.table("supportiq_feedback_aggregation").insert({
                            "user_id": user_id,
                            "feedback_type": feedback_type,
                            "feedback_text": item_text,
                            "occurrence_count": 1,
                            "first_mentioned_at": datetime.utcnow().isoformat(),
                            "last_mentioned_at": datetime.utcnow().isoformat(),
                            "call_ids": [call_id],
                            "category": category
                        }).execute()
                    except Exception as e:
                        print(f"Error inserting feedback (table may not exist): {e}")

        return True

    except Exception as e:
        print(f"Error updating feedback aggregation: {e}")
        return False


async def update_daily_analytics(call_id: str, analysis: Dict[str, Any]) -> bool:
    """Update the daily aggregated analytics."""
    try:
        supabase = get_supabase()

        # Get call date and user_id
        call_result = supabase.table("supportiq_voice_calls").select(
            "started_at, duration_seconds, caller_id"
        ).eq("id", call_id).execute()

        if not call_result.data:
            return False

        started_at = call_result.data[0]["started_at"]
        user_id = call_result.data[0].get("caller_id")

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

        # ========================================
        # Update Global Daily Analytics (user_id = null)
        # ========================================
        await _update_daily_record(supabase, call_date, None, duration, sentiment, resolution, category, call_analysis)

        # ========================================
        # Update User-Specific Daily Analytics
        # ========================================
        if user_id:
            await _update_daily_record(supabase, call_date, user_id, duration, sentiment, resolution, category, call_analysis)

        return True

    except Exception as e:
        print(f"Error updating daily analytics: {e}")
        return False


async def _update_daily_record(
    supabase,
    call_date: str,
    user_id: Optional[str],
    duration: int,
    sentiment: str,
    resolution: str,
    category: str,
    call_analysis: Dict[str, Any]
) -> None:
    """Helper to update a single daily analytics record."""
    # Get or create daily record
    query = supabase.table("supportiq_analytics_daily").select("*").eq("date", call_date)

    if user_id:
        query = query.eq("user_id", user_id)
    else:
        query = query.is_("user_id", "null")

    existing = query.execute()

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

        # Update category breakdown
        categories = record.get("category_breakdown", {}) or {}
        categories[category] = categories.get(category, 0) + 1
        updates["category_breakdown"] = categories

        # Update average sentiment score
        sentiment_score = call_analysis.get("sentiment_score", 0.0)
        old_avg = record.get("avg_sentiment_score", 0.0)
        updates["avg_sentiment_score"] = ((old_avg * (new_total - 1)) + sentiment_score) / new_total

        supabase.table("supportiq_analytics_daily").update(updates).eq("id", record["id"]).execute()
    else:
        sentiment_score = call_analysis.get("sentiment_score", 0.0)
        new_record = {
            "date": call_date,
            "user_id": user_id,
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
            "avg_sentiment_score": sentiment_score,
            "category_breakdown": {category: 1}
        }
        supabase.table("supportiq_analytics_daily").insert(new_record).execute()


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

async def reanalyze_call(call_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Re-analyze an existing call with the enhanced analysis."""
    supabase = get_supabase()

    # Get transcript
    transcript_result = supabase.table("supportiq_call_transcripts").select(
        "transcript"
    ).eq("call_id", call_id).execute()

    if not transcript_result.data:
        return None

    messages = transcript_result.data[0].get("transcript", [])

    # Get user_id if not provided
    if not user_id:
        call_result = supabase.table("supportiq_voice_calls").select(
            "caller_id"
        ).eq("id", call_id).execute()
        if call_result.data:
            user_id = call_result.data[0].get("caller_id")

    # Delete existing analysis
    supabase.table("supportiq_call_analytics").delete().eq("call_id", call_id).execute()

    try:
        supabase.table("supportiq_agent_performance").delete().eq("call_id", call_id).execute()
    except:
        pass

    return await analyze_transcript(call_id, messages, user_id=user_id)


async def get_aggregated_feedback(
    user_id: str,
    feedback_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get aggregated feedback items for a user."""
    try:
        supabase = get_supabase()

        query = supabase.table("supportiq_feedback_aggregation").select("*").eq(
            "user_id", user_id
        ).order("occurrence_count", desc=True).limit(limit)

        if feedback_type:
            query = query.eq("feedback_type", feedback_type)

        result = query.execute()
        return result.data or []

    except Exception as e:
        print(f"Error getting aggregated feedback: {e}")
        return []
