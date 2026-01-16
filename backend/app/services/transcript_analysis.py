"""
Transcript Analysis Service

Uses Gemini 2.5 Flash via OpenRouter to analyze call transcripts
and extract structured insights including customer profiles.

Enhanced version with 2 focused LLM calls for better accuracy:
- Call 1 (Quick Triage): For immediate ticket creation + core analytics
- Call 2 (Deep Analysis): For dashboard, customer profiles, agent coaching

Both calls run in parallel for optimal latency.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
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
    QuickTriageResponse,
    DeepAnalysisResponse,
    get_analysis_schema_summary,
    get_quick_triage_schema,
    get_deep_analysis_schema,
)
from app.services.ticket_service import create_ticket_from_call


# ========================================
# FOCUSED SYSTEM PROMPTS FOR 2-CALL ARCHITECTURE
# ========================================

def get_quick_triage_prompt() -> str:
    """
    System prompt for Call 1: Quick triage.
    Focused on ticket creation essentials + core analytics.
    """
    schema = get_quick_triage_schema()

    return f"""You are an expert customer service analyst. Quickly analyze this call transcript and provide a triage assessment.

Focus on: sentiment, category, resolution status, key topics, summary, and urgency.

Return your analysis as valid JSON matching this exact structure:
{schema}

CATEGORY OPTIONS:
- account_access: Login, password, 2FA issues
- billing: Payments, invoices, refunds, subscriptions
- technical_support: Bugs, errors, how-to questions
- product_inquiry: Features, pricing, comparisons
- complaint: Service issues, dissatisfaction
- feedback: Suggestions, praise
- general_inquiry: Hours, contact, other
- cancellation: Account/subscription cancellation
- onboarding: New user setup, getting started
- upgrade: Plan upgrades, add-ons

URGENCY GUIDELINES:
- critical: Customer threatening to leave, major service outage, security issue
- high: Frustrated customer, unresolved billing issue, time-sensitive request
- medium: Standard support request, minor issue
- low: General inquiry, positive feedback, resolved issue

SCORING:
- sentiment_score: -1.0 (very negative) to 1.0 (very positive)
- customer_satisfaction_predicted: 1 (terrible) to 5 (excellent)

CUSTOMER EFFORT SCORE (1-5):
- 1: Effortless - Issue resolved quickly, no repeats needed
- 2: Low effort - Minor clarification needed, smooth interaction
- 3: Moderate - Some back and forth required, acceptable experience
- 4: High effort - Customer had to repeat information, multiple attempts
- 5: Very high effort - Frustrating experience, transfers, unresolved

ESCALATION INDICATORS:
- was_escalated: True if call was transferred to supervisor/manager/specialist
- escalation_reason: Brief reason (e.g., "billing dispute", "technical issue beyond agent scope")
- transfer_count: Number of times customer was transferred during call

Return ONLY valid JSON, no markdown code blocks."""


def get_deep_analysis_prompt() -> str:
    """
    System prompt for Call 2: Deep analysis.
    Focused on customer profile, agent performance, conversation quality.
    """
    schema = get_deep_analysis_schema()

    return f"""You are an expert customer intelligence and agent coaching specialist. Analyze this call transcript in depth.

Focus on: customer profile details, agent performance metrics, conversation flow, and improvement areas.

Return your analysis as valid JSON matching this exact structure:
{schema}

CUSTOMER TYPE:
- new: First-time caller, unfamiliar with product
- returning: Has called before, knows the basics
- vip: High-value customer, premium support
- at_risk: Shows signs of frustration or churn intent
- unknown: Not enough information

CHURN RISK FACTORS:
- Mentions of cancellation or leaving
- Comparison to competitors
- Multiple unresolved issues
- Frustrated tone throughout
- Long wait times mentioned
- Repeated same problem

AGENT SCORES (0-100):
- 90-100: Excellent performance
- 70-89: Good, minor improvements possible
- 50-69: Average, needs coaching
- 30-49: Below average, requires training
- 0-29: Poor, immediate intervention needed

HANDLE TIME BREAKDOWN:
Estimate from transcript flow:
- talk_time_seconds: Total active speaking time (agent + customer)
- hold_time_seconds: Time on hold (mentions of "please hold", waiting)
- silence_time_seconds: Extended pauses (from dead_air analysis)
- agent_talk_percentage: Agent's share of conversation (0-100)
- customer_talk_percentage: Customer's share of conversation (0-100)

CONVERSATION QUALITY METRICS:
- avg_agent_response_time_seconds: How quickly agent responds on average
- clarity_score (0-100): How clear and understandable was communication
- jargon_usage_count: Count of technical terms that may confuse customer
- empathy_phrases_count: Count of phrases like "I understand", "I'm sorry", "I appreciate"
- words_per_minute: Estimate speaking rate for both agent and customer

ESCALATION DETAILS:
- escalation_level: none, tier_1, tier_2, tier_3, manager, specialist
- escalation_resolved: Whether escalation actually solved the issue
- escalated_to_department: Department/team escalated to (billing, technical, management, etc.)

COMPETITIVE INTELLIGENCE:
- competitors_mentioned: List specific competitor names mentioned
- switching_intent_detected: True if customer expressed interest in alternatives
- price_sensitivity_level: none/low/medium/high based on price discussions
- competitor_comparison_requests: Specific comparisons customer asked about

PRODUCT ANALYTICS:
- products_discussed: Specific products, plans, or services discussed
- features_requested: Features customer asked about or wished for
- features_problematic: Features causing issues for the customer
- upsell_opportunity_detected: Customer showed interest in upgrades/premium features
- cross_sell_suggestions: Other products/services that might benefit customer

Be thorough in extracting customer information. Even small details matter for building customer profiles.
Return ONLY valid JSON, no markdown code blocks."""


# Legacy prompt for backwards compatibility
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
# MAIN ANALYSIS FUNCTION (2-CALL ARCHITECTURE)
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
    Analyze a call transcript using 2 focused LLM calls in parallel.

    Call 1 (Quick Triage): Sentiment, category, resolution, summary → Ticket creation
    Call 2 (Deep Analysis): Customer profile, agent performance → Dashboard updates

    Args:
        call_id: The internal call ID
        transcript_messages: List of transcript messages
        full_transcript: Optional full transcript text
        user_id: The user ID for customer profile association
        user_email: The logged-in user's email (for customer profile)
        user_name: The logged-in user's name/company (for customer profile)

    Returns:
        Dict containing the combined analysis results, or None if analysis failed.
    """
    try:
        # Format transcript for analysis
        formatted_transcript = format_transcript_for_analysis(transcript_messages, full_transcript)

        if not formatted_transcript or len(formatted_transcript.strip()) < 20:
            print(f"Transcript too short for analysis: {call_id}")
            return None

        print(f"[ANALYSIS] Starting 2-call parallel analysis for {call_id}")

        # Run both LLM calls in parallel
        triage_result, deep_result = await asyncio.gather(
            get_quick_triage(formatted_transcript),
            get_deep_analysis(formatted_transcript),
            return_exceptions=True
        )

        # Handle exceptions from parallel calls
        if isinstance(triage_result, Exception):
            print(f"[ANALYSIS] Quick triage failed: {triage_result}")
            triage_result = None
        if isinstance(deep_result, Exception):
            print(f"[ANALYSIS] Deep analysis failed: {deep_result}")
            deep_result = None

        # We need at least the triage for ticket creation
        if not triage_result:
            print(f"[ANALYSIS] Failed to get quick triage for call: {call_id}")
            return None

        print(f"[ANALYSIS] Both LLM calls completed for {call_id}")

        # Combine results into unified format
        analysis_result = combine_analysis_results(triage_result, deep_result)

        # ========================================
        # CREATE TICKET (from triage data)
        # ========================================
        triage_dict = triage_result.model_dump() if triage_result else {}

        # Get customer contact info from deep analysis if available
        customer_phone = None
        if deep_result:
            contact_info = deep_result.customer_profile.contact_info
            customer_phone = contact_info.phone

        ticket = await create_ticket_from_call(
            call_id=call_id,
            user_id=user_id,
            analysis=triage_dict,
            customer_email=user_email,
            customer_name=user_name,
            customer_phone=customer_phone,
        )

        if ticket:
            print(f"[TICKET] Created ticket {ticket['id']} from quick triage")
        else:
            print(f"[TICKET] No ticket created for call {call_id}")

        # ========================================
        # STORE ALL ANALYTICS DATA
        # ========================================
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


def combine_analysis_results(
    triage: Optional[QuickTriageResponse],
    deep: Optional[DeepAnalysisResponse]
) -> Dict[str, Any]:
    """
    Combine results from both LLM calls into the unified format
    expected by downstream storage functions.
    """
    result = {
        "call_analysis": {},
        "customer_profile": {},
        "agent_performance": {},
        "conversation_flow": {}
    }

    # From Quick Triage (Call 1)
    if triage:
        result["call_analysis"] = {
            "overall_sentiment": triage.overall_sentiment,
            "sentiment_score": triage.sentiment_score,
            "primary_category": triage.primary_category,
            "secondary_categories": triage.secondary_categories,
            "tags": triage.tags,
            "resolution_status": triage.resolution_status,
            "resolution_notes": triage.resolution_notes,
            "customer_satisfaction_predicted": triage.customer_satisfaction_predicted,
            "customer_intent": triage.customer_intent,
            "key_topics": triage.key_topics,
            "action_items": triage.action_items,
            "call_summary": triage.call_summary,
            "one_line_summary": triage.one_line_summary,
            "urgency_level": triage.urgency_level,
            "requires_immediate_attention": triage.requires_immediate_attention,
            # NEW: Customer Effort Score
            "customer_effort_score": triage.customer_effort_score,
            "customer_had_to_repeat": triage.customer_had_to_repeat,
            "transfer_count": triage.transfer_count,
            # NEW: Escalation flags
            "was_escalated": triage.was_escalated,
            "escalation_reason": triage.escalation_reason,
        }

    # From Deep Analysis (Call 2)
    if deep:
        # Add deep analysis fields to call_analysis
        result["call_analysis"]["sentiment_progression"] = [
            sp.model_dump() for sp in deep.sentiment_progression
        ]
        result["call_analysis"]["nps_predicted"] = deep.nps_predicted
        result["call_analysis"]["questions_asked"] = deep.questions_asked
        result["call_analysis"]["questions_unanswered"] = deep.questions_unanswered
        result["call_analysis"]["commitments_made"] = deep.commitments_made
        result["call_analysis"]["improvement_suggestions"] = deep.improvement_suggestions
        result["call_analysis"]["knowledge_gaps"] = deep.knowledge_gaps

        # Customer profile
        result["customer_profile"] = deep.customer_profile.model_dump()

        # Agent performance
        result["agent_performance"] = deep.agent_performance.model_dump()

        # Conversation flow
        result["conversation_flow"] = deep.conversation_flow.model_dump()

        # NEW GRANULAR ANALYTICS
        result["handle_time_breakdown"] = deep.handle_time_breakdown.model_dump()
        result["escalation_details"] = deep.escalation_details.model_dump()
        result["conversation_quality"] = deep.conversation_quality.model_dump()
        result["competitive_intelligence"] = deep.competitive_intelligence.model_dump()
        result["product_analytics"] = deep.product_analytics.model_dump()
    else:
        # Provide defaults if deep analysis failed
        result["call_analysis"]["sentiment_progression"] = []
        result["call_analysis"]["nps_predicted"] = None
        result["call_analysis"]["questions_asked"] = []
        result["call_analysis"]["questions_unanswered"] = []
        result["call_analysis"]["commitments_made"] = []
        result["call_analysis"]["improvement_suggestions"] = []
        result["call_analysis"]["knowledge_gaps"] = []
        # Defaults for new granular analytics
        result["handle_time_breakdown"] = {}
        result["escalation_details"] = {}
        result["conversation_quality"] = {}
        result["competitive_intelligence"] = {}
        result["product_analytics"] = {}

    return result


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


# ========================================
# 2-CALL LLM FUNCTIONS
# ========================================

async def get_quick_triage(formatted_transcript: str) -> Optional[QuickTriageResponse]:
    """
    Call 1: Quick triage for immediate ticket creation.

    Focuses on: sentiment, category, resolution, key topics, summary, urgency.
    Faster and more accurate due to focused scope.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": f"""Quickly analyze this customer service call transcript for triage.

TRANSCRIPT:
{formatted_transcript}

Provide your triage assessment as JSON only."""
            }
        ]

        system_prompt = get_quick_triage_prompt()

        response = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            model=settings.analysis_model,
            max_tokens=2048,  # Smaller, focused output
            temperature=0.2,
            json_mode=True
        )

        response_text = _clean_json_response(response)
        raw_triage = json.loads(response_text)

        validated_triage = QuickTriageResponse.model_validate(raw_triage)
        print(f"[TRIAGE] Quick triage completed successfully")
        return validated_triage

    except json.JSONDecodeError as e:
        print(f"[TRIAGE] Failed to parse response as JSON: {e}")
        return None
    except ValidationError as e:
        print(f"[TRIAGE] Pydantic validation failed: {e}")
        try:
            return QuickTriageResponse()
        except Exception:
            return None
    except Exception as e:
        print(f"[TRIAGE] Error in quick triage: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_deep_analysis(formatted_transcript: str) -> Optional[DeepAnalysisResponse]:
    """
    Call 2: Deep analysis for dashboard and coaching.

    Focuses on: customer profile, agent performance, conversation flow.
    More thorough analysis for long-term insights.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this customer service call transcript in depth.
Focus on customer profile, agent performance, and conversation quality.

TRANSCRIPT:
{formatted_transcript}

Provide your deep analysis as JSON only."""
            }
        ]

        system_prompt = get_deep_analysis_prompt()

        response = await chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            model=settings.analysis_model,
            max_tokens=3072,  # Larger for detailed profile/performance data
            temperature=0.2,
            json_mode=True
        )

        response_text = _clean_json_response(response)
        raw_analysis = json.loads(response_text)

        validated_analysis = DeepAnalysisResponse.model_validate(raw_analysis)
        print(f"[DEEP] Deep analysis completed successfully")
        return validated_analysis

    except json.JSONDecodeError as e:
        print(f"[DEEP] Failed to parse response as JSON: {e}")
        return None
    except ValidationError as e:
        print(f"[DEEP] Pydantic validation failed: {e}")
        try:
            return DeepAnalysisResponse()
        except Exception:
            return None
    except Exception as e:
        print(f"[DEEP] Error in deep analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def _clean_json_response(response: str) -> str:
    """Clean markdown code blocks from LLM response."""
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text.strip()


# ========================================
# LEGACY SINGLE-CALL FUNCTION (kept for compatibility)
# ========================================

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

            # NEW: Customer Effort Score
            "customer_effort_score": call_analysis.get("customer_effort_score", 3),
            "customer_had_to_repeat": call_analysis.get("customer_had_to_repeat", False),
            "transfer_count": call_analysis.get("transfer_count", 0),

            # NEW: Escalation tracking
            "was_escalated": call_analysis.get("was_escalated", False),
            "escalation_reason": call_analysis.get("escalation_reason"),
            "escalation_level": analysis.get("escalation_details", {}).get("escalation_level"),
            "escalation_resolved": analysis.get("escalation_details", {}).get("escalation_resolved"),
            "escalated_to_department": analysis.get("escalation_details", {}).get("escalated_to_department"),

            # NEW: Granular analytics as JSONB
            "handle_time_breakdown": analysis.get("handle_time_breakdown", {}),
            "conversation_quality": analysis.get("conversation_quality", {}),
            "competitive_intelligence": analysis.get("competitive_intelligence", {}),
            "product_analytics": analysis.get("product_analytics", {}),

            # Analysis metadata
            "analysis_model": settings.analysis_model,
            "analysis_version": "2.1"  # Updated version for new fields
        }

        # Insert analytics
        supabase.table("supportiq_call_analytics").insert(analytics_record).execute()
        print(f"Stored call analytics for {call_id}")

        # ========================================
        # 2. Store Agent Performance
        # ========================================
        # Extract handle time breakdown
        handle_time = analysis.get("handle_time_breakdown", {})

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
                "training_recommendations": agent_performance.get("training_recommendations", []),
                # NEW: Handle time breakdown
                "talk_time_seconds": handle_time.get("talk_time_seconds", 0),
                "hold_time_seconds": handle_time.get("hold_time_seconds", 0),
                "escalations_initiated": 1 if call_analysis.get("was_escalated") else 0,
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
