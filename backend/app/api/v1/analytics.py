"""
Analytics API Router

Endpoints for retrieving aggregated analytics and dashboard data.
Enhanced with real customer insights and feedback aggregation.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.database import get_supabase
from app.core.security import get_current_user, TokenData
from app.models.voice import (
    AnalyticsDashboard,
    OverviewStats,
    SentimentBreakdown,
    CategoryBreakdown,
    TrendDataPoint,
    TopIssue,
    RecentCall,
    CumulativeDashboard,
    CumulativeOverview,
    CustomerInsightsSummary,
    AgentLeaderboard,
    FeedbackItem,
    CustomerProfileSummary,
    CustomerProfileDetail,
    CustomerListResponse,
    HighRiskCustomer,
    ActionItemSummary,
    EnhancedAnalyticsSummary
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get comprehensive analytics dashboard data for the current user.

    Each user only sees analytics for their own calls (data isolation).
    """
    supabase = get_supabase()
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get calls with analytics - filtered by user
    result = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_analytics(*)"
    ).eq("caller_id", current_user.user_id).gte(
        "started_at", start_date.isoformat()
    ).order(
        "started_at", desc=True
    ).execute()

    calls = result.data or []

    # Calculate overview stats
    total_calls = len(calls)
    total_duration = sum(c.get("duration_seconds", 0) or 0 for c in calls)
    avg_duration = total_duration / total_calls if total_calls > 0 else 0

    # Get analytics data
    analytics_list = []
    for call in calls:
        analytics = call.get("supportiq_call_analytics")
        if analytics:
            if isinstance(analytics, list) and analytics:
                analytics_list.append(analytics[0])
            elif isinstance(analytics, dict):
                analytics_list.append(analytics)

    # Resolution rate
    resolved = sum(1 for a in analytics_list if a.get("resolution_status") == "resolved")
    resolution_rate = (resolved / len(analytics_list) * 100) if analytics_list else 0

    # Sentiment
    sentiment_scores = [
        a.get("sentiment_score", 0)
        for a in analytics_list
        if a.get("sentiment_score") is not None
    ]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # Sentiment breakdown
    sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    for a in analytics_list:
        s = a.get("overall_sentiment", "neutral")
        if s in sentiment_breakdown:
            sentiment_breakdown[s] += 1

    # Category breakdown
    category_counts = {}
    for a in analytics_list:
        cat = a.get("primary_category", "unknown")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Calls today and this week
    today = datetime.utcnow().date()
    calls_today = 0
    for c in calls:
        try:
            call_date = c["started_at"]
            if isinstance(call_date, str):
                call_date = datetime.fromisoformat(call_date.replace("Z", "+00:00")).date()
            if call_date == today:
                calls_today += 1
        except:
            pass

    # Build trends (daily aggregates)
    trends = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days - i - 1)).date()
        day_calls = []
        for c in calls:
            try:
                call_date = c["started_at"]
                if isinstance(call_date, str):
                    call_date = datetime.fromisoformat(call_date.replace("Z", "+00:00")).date()
                if call_date == day:
                    day_calls.append(c)
            except:
                pass

        # Get analytics for day's calls
        day_analytics = []
        for c in day_calls:
            analytics = c.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    day_analytics.append(analytics[0])
                elif isinstance(analytics, dict):
                    day_analytics.append(analytics)

        day_resolved = sum(1 for a in day_analytics if a.get("resolution_status") == "resolved")
        day_sentiments = [
            a.get("sentiment_score", 0)
            for a in day_analytics
            if a.get("sentiment_score") is not None
        ]

        trends.append(TrendDataPoint(
            date=day.isoformat(),
            calls=len(day_calls),
            avg_sentiment=sum(day_sentiments) / len(day_sentiments) if day_sentiments else 0,
            resolution_rate=(day_resolved / len(day_analytics) * 100) if day_analytics else 0
        ))

    # Top issues (by category)
    top_issues = sorted(
        [TopIssue(category=k, count=v) for k, v in category_counts.items()],
        key=lambda x: x.count,
        reverse=True
    )[:5]

    # Recent calls (last 5)
    recent_calls = []
    for c in calls[:5]:
        analytics = c.get("supportiq_call_analytics")
        sentiment = None
        if analytics:
            if isinstance(analytics, list) and analytics:
                sentiment = analytics[0].get("overall_sentiment")
            elif isinstance(analytics, dict):
                sentiment = analytics.get("overall_sentiment")

        recent_calls.append(RecentCall(
            id=c["id"],
            started_at=c["started_at"],
            duration=c.get("duration_seconds"),
            status=c["status"],
            sentiment=sentiment
        ))

    return AnalyticsDashboard(
        overview=OverviewStats(
            total_calls=total_calls,
            avg_duration_seconds=avg_duration,
            resolution_rate=resolution_rate,
            avg_sentiment_score=avg_sentiment,
            calls_today=calls_today,
            calls_this_week=total_calls  # Already filtered by days
        ),
        sentiment=SentimentBreakdown(**sentiment_breakdown),
        categories=CategoryBreakdown(categories=category_counts),
        trends=trends,
        top_issues=top_issues,
        recent_calls=recent_calls
    )


@router.get("/overview")
async def get_overview_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get quick overview statistics only.
    """
    dashboard = await get_dashboard(days=days)
    return dashboard.overview


@router.get("/sentiment")
async def get_sentiment_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get sentiment breakdown only.
    """
    dashboard = await get_dashboard(days=days)
    return dashboard.sentiment


@router.get("/categories")
async def get_category_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get category breakdown only.
    """
    dashboard = await get_dashboard(days=days)
    return dashboard.categories


@router.get("/trends")
async def get_trends(days: int = Query(7, ge=1, le=90)):
    """
    Get daily trends data.
    """
    dashboard = await get_dashboard(days=days)
    return {"trends": dashboard.trends}


@router.get("/cumulative", response_model=CumulativeDashboard)
async def get_cumulative_dashboard():
    """
    Get all-time cumulative analytics dashboard.
    Includes historical trends, customer insights, and agent performance.
    """
    supabase = get_supabase()

    # Get ALL calls with analytics
    result = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_analytics(*)"
    ).order("started_at", desc=True).execute()

    all_calls = result.data or []

    # Calculate cumulative stats
    total_calls = len(all_calls)
    total_duration = sum(c.get("duration_seconds", 0) or 0 for c in all_calls)
    avg_duration = total_duration / total_calls if total_calls > 0 else 0

    # Get all analytics
    all_analytics = []
    for call in all_calls:
        analytics = call.get("supportiq_call_analytics")
        if analytics:
            if isinstance(analytics, list) and analytics:
                all_analytics.append(analytics[0])
            elif isinstance(analytics, dict):
                all_analytics.append(analytics)

    # Resolution stats
    total_resolved = sum(1 for a in all_analytics if a.get("resolution_status") == "resolved")
    total_escalated = sum(1 for a in all_analytics if a.get("resolution_status") == "escalated")
    resolution_rate = (total_resolved / len(all_analytics) * 100) if all_analytics else 0

    # Sentiment stats
    sentiment_scores = [a.get("sentiment_score", 0) for a in all_analytics if a.get("sentiment_score") is not None]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # CSAT stats
    csat_scores = [a.get("customer_satisfaction_predicted", 3.0) for a in all_analytics]
    avg_csat = sum(csat_scores) / len(csat_scores) if csat_scores else 0

    # Agent scores
    agent_scores = [a.get("agent_performance_score", 50.0) for a in all_analytics]
    avg_agent_score = sum(agent_scores) / len(agent_scores) if agent_scores else 0

    # Time-based counts
    now = datetime.utcnow()
    today = now.date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    calls_today = 0
    calls_this_week = 0
    calls_this_month = 0
    calls_last_week = 0

    for c in all_calls:
        try:
            call_date = c["started_at"]
            if isinstance(call_date, str):
                call_date = datetime.fromisoformat(call_date.replace("Z", "+00:00")).date()

            if call_date == today:
                calls_today += 1
            if call_date >= week_ago:
                calls_this_week += 1
            if call_date >= month_ago:
                calls_this_month += 1
            if week_ago - timedelta(days=7) <= call_date < week_ago:
                calls_last_week += 1
        except:
            pass

    # Week over week comparison
    calls_vs_last_week = ((calls_this_week - calls_last_week) / calls_last_week * 100) if calls_last_week > 0 else 0

    # Sentiment breakdown
    sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    for a in all_analytics:
        s = a.get("overall_sentiment", "neutral")
        if s in sentiment_breakdown:
            sentiment_breakdown[s] += 1

    # Category breakdown
    category_counts = {}
    for a in all_analytics:
        cat = a.get("primary_category", "unknown")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Top issues all time
    top_issues_all_time = sorted(
        [TopIssue(category=k, count=v) for k, v in category_counts.items()],
        key=lambda x: x.count,
        reverse=True
    )[:10]

    # Weekly trends (last 12 weeks)
    weekly_trends = []
    for week_offset in range(12):
        week_start = today - timedelta(days=today.weekday() + 7 * week_offset)
        week_end = week_start + timedelta(days=6)

        week_calls = []
        for c in all_calls:
            try:
                call_date = c["started_at"]
                if isinstance(call_date, str):
                    call_date = datetime.fromisoformat(call_date.replace("Z", "+00:00")).date()
                if week_start <= call_date <= week_end:
                    week_calls.append(c)
            except:
                pass

        week_analytics = []
        for c in week_calls:
            analytics = c.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    week_analytics.append(analytics[0])
                elif isinstance(analytics, dict):
                    week_analytics.append(analytics)

        week_resolved = sum(1 for a in week_analytics if a.get("resolution_status") == "resolved")
        week_sentiments = [a.get("sentiment_score", 0) for a in week_analytics if a.get("sentiment_score") is not None]

        weekly_trends.append(TrendDataPoint(
            date=week_start.isoformat(),
            calls=len(week_calls),
            avg_sentiment=sum(week_sentiments) / len(week_sentiments) if week_sentiments else 0,
            resolution_rate=(week_resolved / len(week_analytics) * 100) if week_analytics else 0
        ))

    weekly_trends.reverse()  # Oldest first

    # Monthly trends (last 6 months)
    monthly_trends = []
    for month_offset in range(6):
        month_start = (today.replace(day=1) - timedelta(days=30 * month_offset)).replace(day=1)
        if month_offset == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)

        month_calls = []
        for c in all_calls:
            try:
                call_date = c["started_at"]
                if isinstance(call_date, str):
                    call_date = datetime.fromisoformat(call_date.replace("Z", "+00:00")).date()
                if month_start <= call_date <= month_end:
                    month_calls.append(c)
            except:
                pass

        month_analytics = []
        for c in month_calls:
            analytics = c.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    month_analytics.append(analytics[0])
                elif isinstance(analytics, dict):
                    month_analytics.append(analytics)

        month_resolved = sum(1 for a in month_analytics if a.get("resolution_status") == "resolved")
        month_sentiments = [a.get("sentiment_score", 0) for a in month_analytics if a.get("sentiment_score") is not None]

        monthly_trends.append(TrendDataPoint(
            date=month_start.isoformat(),
            calls=len(month_calls),
            avg_sentiment=sum(month_sentiments) / len(month_sentiments) if month_sentiments else 0,
            resolution_rate=(month_resolved / len(month_analytics) * 100) if month_analytics else 0
        ))

    monthly_trends.reverse()

    # Agent leaderboard (by agent_type)
    agent_stats = {}
    for c in all_calls:
        agent_type = c.get("agent_type", "general")
        if agent_type not in agent_stats:
            agent_stats[agent_type] = {"calls": 0, "scores": [], "resolutions": [], "csats": []}

        agent_stats[agent_type]["calls"] += 1

        analytics = c.get("supportiq_call_analytics")
        if analytics:
            if isinstance(analytics, list) and analytics:
                analytics = analytics[0]
            if isinstance(analytics, dict):
                agent_stats[agent_type]["scores"].append(analytics.get("agent_performance_score", 50))
                agent_stats[agent_type]["resolutions"].append(1 if analytics.get("resolution_status") == "resolved" else 0)
                agent_stats[agent_type]["csats"].append(analytics.get("customer_satisfaction_predicted", 3))

    agent_leaderboard = []
    for agent_type, stats in agent_stats.items():
        agent_leaderboard.append(AgentLeaderboard(
            agent_type=agent_type,
            total_calls=stats["calls"],
            avg_score=sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0,
            avg_resolution_rate=(sum(stats["resolutions"]) / len(stats["resolutions"]) * 100) if stats["resolutions"] else 0,
            avg_csat=sum(stats["csats"]) / len(stats["csats"]) if stats["csats"] else 0
        ))

    agent_leaderboard.sort(key=lambda x: x.avg_score, reverse=True)

    # Customer insights - get real aggregated data
    customer_insights = await get_customer_insights()

    # Recent calls
    recent_calls = []
    for c in all_calls[:10]:
        analytics = c.get("supportiq_call_analytics")
        sentiment = None
        if analytics:
            if isinstance(analytics, list) and analytics:
                sentiment = analytics[0].get("overall_sentiment")
            elif isinstance(analytics, dict):
                sentiment = analytics.get("overall_sentiment")

        recent_calls.append(RecentCall(
            id=c["id"],
            started_at=c["started_at"],
            duration=c.get("duration_seconds"),
            status=c["status"],
            sentiment=sentiment
        ))

    return CumulativeDashboard(
        overview=CumulativeOverview(
            total_calls=total_calls,
            total_duration_seconds=total_duration,
            avg_duration_seconds=avg_duration,
            total_resolved=total_resolved,
            total_escalated=total_escalated,
            resolution_rate=resolution_rate,
            avg_sentiment_score=avg_sentiment,
            avg_csat=avg_csat,
            avg_agent_score=avg_agent_score,
            calls_today=calls_today,
            calls_this_week=calls_this_week,
            calls_this_month=calls_this_month,
            calls_vs_last_week=calls_vs_last_week,
            resolution_vs_last_week=0.0,
            sentiment_vs_last_week=0.0
        ),
        sentiment=SentimentBreakdown(**sentiment_breakdown),
        categories=CategoryBreakdown(categories=category_counts),
        customer_insights=customer_insights,
        agent_leaderboard=agent_leaderboard,
        weekly_trends=weekly_trends,
        monthly_trends=monthly_trends,
        top_issues_all_time=top_issues_all_time,
        recent_calls=recent_calls
    )


# ========================================
# HELPER FUNCTIONS
# ========================================

async def get_customer_insights() -> CustomerInsightsSummary:
    """Get aggregated customer insights from the database."""
    try:
        supabase = get_supabase()

        # Get customer profile stats
        try:
            profiles_result = supabase.table("supportiq_customer_profiles").select(
                "id, total_calls, churn_risk_level, churn_risk_score"
            ).execute()
            profiles = profiles_result.data or []
        except:
            profiles = []

        total_unique_customers = len(profiles)
        total_profile_calls = sum(p.get("total_calls", 0) for p in profiles)
        avg_calls_per_customer = total_profile_calls / total_unique_customers if total_unique_customers > 0 else 1.0

        # Count repeat callers (more than 1 call)
        repeat_callers = sum(1 for p in profiles if p.get("total_calls", 0) > 1)
        repeat_caller_rate = (repeat_callers / total_unique_customers * 100) if total_unique_customers > 0 else 0.0

        # High risk customers
        high_risk_customers = sum(1 for p in profiles if p.get("churn_risk_level") == "high")
        churn_scores = [p.get("churn_risk_score", 0) for p in profiles if p.get("churn_risk_score")]
        avg_churn_risk = sum(churn_scores) / len(churn_scores) if churn_scores else 0.0

        # Get aggregated feedback
        top_pain_points = []
        top_feature_requests = []
        top_complaints = []

        try:
            # Pain points
            pain_result = supabase.table("supportiq_feedback_aggregation").select(
                "feedback_text, occurrence_count"
            ).eq("feedback_type", "pain_point").order(
                "occurrence_count", desc=True
            ).limit(5).execute()

            for item in (pain_result.data or []):
                top_pain_points.append({
                    "text": item["feedback_text"],
                    "count": item["occurrence_count"]
                })

            # Feature requests
            feature_result = supabase.table("supportiq_feedback_aggregation").select(
                "feedback_text, occurrence_count"
            ).eq("feedback_type", "feature_request").order(
                "occurrence_count", desc=True
            ).limit(5).execute()

            for item in (feature_result.data or []):
                top_feature_requests.append({
                    "text": item["feedback_text"],
                    "count": item["occurrence_count"]
                })

            # Complaints
            complaint_result = supabase.table("supportiq_feedback_aggregation").select(
                "feedback_text, occurrence_count"
            ).eq("feedback_type", "complaint").order(
                "occurrence_count", desc=True
            ).limit(5).execute()

            for item in (complaint_result.data or []):
                top_complaints.append({
                    "text": item["feedback_text"],
                    "count": item["occurrence_count"]
                })
        except Exception as e:
            print(f"Error getting feedback aggregation: {e}")

        return CustomerInsightsSummary(
            total_unique_customers=total_unique_customers,
            repeat_caller_rate=repeat_caller_rate,
            avg_calls_per_customer=avg_calls_per_customer,
            top_pain_points=top_pain_points,
            top_feature_requests=top_feature_requests,
            top_complaints=top_complaints,
            high_risk_customers=high_risk_customers,
            avg_churn_risk=avg_churn_risk
        )

    except Exception as e:
        print(f"Error getting customer insights: {e}")
        return CustomerInsightsSummary()


# ========================================
# NEW ENDPOINTS
# ========================================

@router.get("/customers", response_model=CustomerListResponse)
async def get_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, description="Filter by churn risk level"),
    customer_type: Optional[str] = Query(None, description="Filter by customer type"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get paginated list of customer profiles.
    """
    try:
        supabase = get_supabase()

        query = supabase.table("supportiq_customer_profiles").select(
            "*", count="exact"
        ).eq("user_id", current_user.user_id)

        if risk_level:
            query = query.eq("churn_risk_level", risk_level)
        if customer_type:
            query = query.eq("customer_type", customer_type)

        offset = (page - 1) * page_size
        query = query.order("last_call_at", desc=True).range(offset, offset + page_size - 1)

        result = query.execute()

        customers = []
        for c in (result.data or []):
            customers.append(CustomerProfileSummary(
                id=c["id"],
                name=c.get("name"),
                email=c.get("email"),
                phone=c.get("phone"),
                customer_type=c.get("customer_type", "unknown"),
                total_calls=c.get("total_calls", 0),
                avg_satisfaction=c.get("avg_satisfaction_score", 0.0),
                churn_risk_level=c.get("churn_risk_level", "low"),
                churn_risk_score=c.get("churn_risk_score", 0.0),
                last_call_at=c.get("last_call_at")
            ))

        return CustomerListResponse(
            customers=customers,
            total=result.count or 0,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        print(f"Error getting customers: {e}")
        return CustomerListResponse(customers=[], total=0, page=page, page_size=page_size)


@router.get("/customers/{customer_id}", response_model=CustomerProfileDetail)
async def get_customer_detail(
    customer_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get detailed customer profile.
    """
    supabase = get_supabase()

    result = supabase.table("supportiq_customer_profiles").select("*").eq(
        "id", customer_id
    ).eq("user_id", current_user.user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Customer not found")

    c = result.data[0]

    return CustomerProfileDetail(
        id=c["id"],
        name=c.get("name"),
        email=c.get("email"),
        phone=c.get("phone"),
        account_id=c.get("account_id"),
        company=c.get("company"),
        customer_type=c.get("customer_type", "unknown"),
        communication_style=c.get("communication_style", "neutral"),
        total_calls=c.get("total_calls", 0),
        total_call_duration_seconds=c.get("total_call_duration_seconds", 0),
        first_call_at=c.get("first_call_at"),
        last_call_at=c.get("last_call_at"),
        avg_satisfaction=c.get("avg_satisfaction_score", 0.0),
        avg_sentiment_score=c.get("avg_sentiment_score", 0.0),
        churn_risk_level=c.get("churn_risk_level", "low"),
        churn_risk_score=c.get("churn_risk_score", 0.0),
        churn_risk_factors=c.get("churn_risk_factors", []),
        pain_points=c.get("pain_points", []),
        feature_requests=c.get("feature_requests", []),
        complaints=c.get("complaints", []),
        compliments=c.get("compliments", []),
        products_mentioned=c.get("products_mentioned", []),
        competitor_mentions=c.get("competitor_mentions", []),
        requires_follow_up=c.get("requires_follow_up", False),
        follow_up_reason=c.get("follow_up_reason"),
        special_notes=c.get("special_notes", []),
        tags=c.get("tags", [])
    )


@router.get("/high-risk-customers", response_model=List[HighRiskCustomer])
async def get_high_risk_customers(
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get customers with high churn risk.
    """
    try:
        supabase = get_supabase()

        result = supabase.table("supportiq_customer_profiles").select("*").eq(
            "user_id", current_user.user_id
        ).eq("churn_risk_level", "high").order(
            "churn_risk_score", desc=True
        ).limit(limit).execute()

        customers = []
        for c in (result.data or []):
            customers.append(HighRiskCustomer(
                id=c["id"],
                name=c.get("name"),
                email=c.get("email"),
                phone=c.get("phone"),
                churn_risk_score=c.get("churn_risk_score", 0.0),
                churn_risk_factors=c.get("churn_risk_factors", []),
                recommended_actions=[],  # Could add retention_actions from churn_risk
                last_call_at=c.get("last_call_at"),
                total_calls=c.get("total_calls", 0)
            ))

        return customers

    except Exception as e:
        print(f"Error getting high risk customers: {e}")
        return []


@router.get("/feedback", response_model=List[FeedbackItem])
async def get_feedback_items(
    feedback_type: Optional[str] = Query(None, description="pain_point, feature_request, complaint, compliment, knowledge_gap"),
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get aggregated feedback items.
    """
    try:
        supabase = get_supabase()

        query = supabase.table("supportiq_feedback_aggregation").select("*").eq(
            "user_id", current_user.user_id
        ).order("occurrence_count", desc=True).limit(limit)

        if feedback_type:
            query = query.eq("feedback_type", feedback_type)

        result = query.execute()

        items = []
        for f in (result.data or []):
            items.append(FeedbackItem(
                text=f["feedback_text"],
                count=f.get("occurrence_count", 1),
                category=f.get("category"),
                first_mentioned=f.get("first_mentioned_at"),
                last_mentioned=f.get("last_mentioned_at")
            ))

        return items

    except Exception as e:
        print(f"Error getting feedback: {e}")
        return []


@router.get("/action-items", response_model=List[ActionItemSummary])
async def get_pending_action_items(
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get pending action items and commitments from recent calls.
    """
    try:
        supabase = get_supabase()

        # Get calls with action items
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(action_items, commitments_made)"
        ).eq("caller_id", current_user.user_id).order(
            "started_at", desc=True
        ).limit(limit).execute()

        items = []
        for call in (result.data or []):
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]

                action_items = analytics.get("action_items", []) or []
                commitments = analytics.get("commitments_made", []) or []

                if action_items or commitments:
                    items.append(ActionItemSummary(
                        call_id=call["id"],
                        call_date=call["started_at"],
                        customer_name=None,  # Would need to join with customer profile
                        action_items=action_items,
                        commitments_made=commitments,
                        follow_up_deadline=None
                    ))

        return items

    except Exception as e:
        print(f"Error getting action items: {e}")
        return []


@router.get("/knowledge-gaps", response_model=List[FeedbackItem])
async def get_knowledge_gaps(
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get aggregated knowledge gaps (topics agents struggled with).
    """
    try:
        supabase = get_supabase()

        result = supabase.table("supportiq_feedback_aggregation").select("*").eq(
            "user_id", current_user.user_id
        ).eq("feedback_type", "knowledge_gap").order(
            "occurrence_count", desc=True
        ).limit(limit).execute()

        items = []
        for f in (result.data or []):
            items.append(FeedbackItem(
                text=f["feedback_text"],
                count=f.get("occurrence_count", 1),
                category=f.get("category"),
                first_mentioned=f.get("first_mentioned_at"),
                last_mentioned=f.get("last_mentioned_at")
            ))

        return items

    except Exception as e:
        print(f"Error getting knowledge gaps: {e}")
        return []


# ========================================
# NEW GRANULAR ANALYTICS ENDPOINTS
# ========================================

@router.get("/time-based")
async def get_time_based_analytics(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get time-based analytics including hourly distribution and peak hours.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with analytics
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, duration_seconds, supportiq_call_analytics(call_hour, call_day_of_week, is_peak_hour, sentiment_score, resolution_status)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        # Hourly distribution
        hourly_distribution = {i: {"calls": 0, "avg_sentiment": 0.0, "sentiments": []} for i in range(24)}

        # Day of week distribution
        day_distribution = {
            "Monday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Tuesday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Wednesday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Thursday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Friday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Saturday": {"calls": 0, "avg_duration": 0.0, "durations": []},
            "Sunday": {"calls": 0, "avg_duration": 0.0, "durations": []},
        }

        for call in calls:
            # Parse start time
            started_at = call.get("started_at")
            if isinstance(started_at, str):
                try:
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    hour = dt.hour
                    day_name = dt.strftime("%A")

                    # Update hourly
                    hourly_distribution[hour]["calls"] += 1

                    # Get sentiment from analytics
                    analytics = call.get("supportiq_call_analytics")
                    if analytics:
                        if isinstance(analytics, list) and analytics:
                            analytics = analytics[0]
                        if isinstance(analytics, dict):
                            sentiment = analytics.get("sentiment_score")
                            if sentiment is not None:
                                hourly_distribution[hour]["sentiments"].append(sentiment)

                    # Update day of week
                    if day_name in day_distribution:
                        day_distribution[day_name]["calls"] += 1
                        duration = call.get("duration_seconds", 0) or 0
                        if duration > 0:
                            day_distribution[day_name]["durations"].append(duration)
                except Exception:
                    pass

        # Calculate averages
        for hour_data in hourly_distribution.values():
            if hour_data["sentiments"]:
                hour_data["avg_sentiment"] = sum(hour_data["sentiments"]) / len(hour_data["sentiments"])
            del hour_data["sentiments"]

        for day_data in day_distribution.values():
            if day_data["durations"]:
                day_data["avg_duration"] = sum(day_data["durations"]) / len(day_data["durations"])
            del day_data["durations"]

        # Find peak hours (top 3 by call volume)
        peak_hours = sorted(
            [(hour, data["calls"]) for hour, data in hourly_distribution.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "hourly_distribution": hourly_distribution,
            "day_of_week_distribution": day_distribution,
            "peak_hours": [{"hour": h, "calls": c} for h, c in peak_hours],
            "total_calls": len(calls),
            "days_analyzed": days
        }

    except Exception as e:
        print(f"Error getting time-based analytics: {e}")
        return {
            "hourly_distribution": {},
            "day_of_week_distribution": {},
            "peak_hours": [],
            "total_calls": 0,
            "days_analyzed": days
        }


@router.get("/effort-scores")
async def get_effort_score_analytics(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get Customer Effort Score (CES) distribution and trends.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with CES data
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(customer_effort_score, customer_had_to_repeat, transfer_count, resolution_status)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        # CES distribution (1-5)
        ces_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        all_ces_scores = []
        repeat_count = 0
        transfer_counts = []

        # Daily CES trend
        daily_ces = {}

        for call in calls:
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]
                if isinstance(analytics, dict):
                    ces = analytics.get("customer_effort_score", 3)
                    ces = max(1, min(5, ces))  # Clamp to 1-5
                    ces_distribution[ces] += 1
                    all_ces_scores.append(ces)

                    if analytics.get("customer_had_to_repeat"):
                        repeat_count += 1

                    transfer = analytics.get("transfer_count", 0)
                    if transfer:
                        transfer_counts.append(transfer)

                    # Daily trend
                    started_at = call.get("started_at")
                    if isinstance(started_at, str):
                        try:
                            date_str = started_at[:10]
                            if date_str not in daily_ces:
                                daily_ces[date_str] = []
                            daily_ces[date_str].append(ces)
                        except Exception:
                            pass

        # Calculate metrics
        avg_ces = sum(all_ces_scores) / len(all_ces_scores) if all_ces_scores else 3.0
        repeat_rate = (repeat_count / len(calls) * 100) if calls else 0
        avg_transfers = sum(transfer_counts) / len(transfer_counts) if transfer_counts else 0

        # Daily trend
        ces_trend = []
        for date_str in sorted(daily_ces.keys()):
            scores = daily_ces[date_str]
            ces_trend.append({
                "date": date_str,
                "avg_ces": sum(scores) / len(scores),
                "calls": len(scores)
            })

        return {
            "ces_distribution": ces_distribution,
            "average_ces": round(avg_ces, 2),
            "repeat_rate_percent": round(repeat_rate, 1),
            "average_transfers": round(avg_transfers, 2),
            "total_calls_with_repeats": repeat_count,
            "ces_trend": ces_trend,
            "total_calls": len(calls),
            "ces_breakdown": {
                "effortless": ces_distribution[1] + ces_distribution[2],
                "moderate": ces_distribution[3],
                "high_effort": ces_distribution[4] + ces_distribution[5]
            }
        }

    except Exception as e:
        print(f"Error getting effort score analytics: {e}")
        return {
            "ces_distribution": {},
            "average_ces": 3.0,
            "repeat_rate_percent": 0,
            "average_transfers": 0,
            "total_calls_with_repeats": 0,
            "ces_trend": [],
            "total_calls": 0,
            "ces_breakdown": {"effortless": 0, "moderate": 0, "high_effort": 0}
        }


@router.get("/escalation-analytics")
async def get_escalation_analytics(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get escalation rates, reasons, and department breakdown.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with escalation data
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(was_escalated, escalation_reason, escalation_level, escalation_resolved, escalated_to_department, primary_category)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        total_calls = len(calls)
        escalated_calls = 0
        escalation_reasons = {}
        escalation_levels = {}
        departments = {}
        categories_escalated = {}
        resolved_escalations = 0

        for call in calls:
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]
                if isinstance(analytics, dict):
                    if analytics.get("was_escalated"):
                        escalated_calls += 1

                        # Count resolved
                        if analytics.get("escalation_resolved"):
                            resolved_escalations += 1

                        # Reasons
                        reason = analytics.get("escalation_reason")
                        if reason:
                            escalation_reasons[reason] = escalation_reasons.get(reason, 0) + 1

                        # Levels
                        level = analytics.get("escalation_level")
                        if level and level != "none":
                            escalation_levels[level] = escalation_levels.get(level, 0) + 1

                        # Departments
                        dept = analytics.get("escalated_to_department")
                        if dept:
                            departments[dept] = departments.get(dept, 0) + 1

                        # Categories that lead to escalation
                        category = analytics.get("primary_category")
                        if category:
                            categories_escalated[category] = categories_escalated.get(category, 0) + 1

        escalation_rate = (escalated_calls / total_calls * 100) if total_calls > 0 else 0
        resolution_rate = (resolved_escalations / escalated_calls * 100) if escalated_calls > 0 else 0

        # Sort and get top items
        top_reasons = sorted(escalation_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
        top_departments = sorted(departments.items(), key=lambda x: x[1], reverse=True)[:10]
        top_categories = sorted(categories_escalated.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_calls": total_calls,
            "escalated_calls": escalated_calls,
            "escalation_rate_percent": round(escalation_rate, 1),
            "escalation_resolution_rate_percent": round(resolution_rate, 1),
            "escalation_levels": escalation_levels,
            "top_escalation_reasons": [{"reason": r, "count": c} for r, c in top_reasons],
            "top_departments": [{"department": d, "count": c} for d, c in top_departments],
            "categories_leading_to_escalation": [{"category": cat, "count": c} for cat, c in top_categories]
        }

    except Exception as e:
        print(f"Error getting escalation analytics: {e}")
        return {
            "total_calls": 0,
            "escalated_calls": 0,
            "escalation_rate_percent": 0,
            "escalation_resolution_rate_percent": 0,
            "escalation_levels": {},
            "top_escalation_reasons": [],
            "top_departments": [],
            "categories_leading_to_escalation": []
        }


@router.get("/competitive-intelligence")
async def get_competitive_intelligence(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get aggregated competitive intelligence from calls.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with competitive intelligence
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(competitive_intelligence)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        competitor_mentions = {}
        comparison_requests = {}
        switching_intent_count = 0
        price_sensitivity = {"none": 0, "low": 0, "medium": 0, "high": 0}
        calls_with_competitor_mentions = 0

        for call in calls:
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]
                if isinstance(analytics, dict):
                    ci = analytics.get("competitive_intelligence", {})
                    if isinstance(ci, dict):
                        # Competitors mentioned
                        competitors = ci.get("competitors_mentioned", [])
                        if competitors:
                            calls_with_competitor_mentions += 1
                            for comp in competitors:
                                competitor_mentions[comp] = competitor_mentions.get(comp, 0) + 1

                        # Comparison requests
                        comparisons = ci.get("competitor_comparison_requests", [])
                        for comp in comparisons:
                            comparison_requests[comp] = comparison_requests.get(comp, 0) + 1

                        # Switching intent
                        if ci.get("switching_intent_detected"):
                            switching_intent_count += 1

                        # Price sensitivity
                        sensitivity = ci.get("price_sensitivity_level", "none")
                        if sensitivity in price_sensitivity:
                            price_sensitivity[sensitivity] += 1

        total_calls = len(calls)
        competitor_mention_rate = (calls_with_competitor_mentions / total_calls * 100) if total_calls > 0 else 0
        switching_intent_rate = (switching_intent_count / total_calls * 100) if total_calls > 0 else 0

        # Sort competitors by mention count
        top_competitors = sorted(competitor_mentions.items(), key=lambda x: x[1], reverse=True)[:10]
        top_comparisons = sorted(comparison_requests.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_calls": total_calls,
            "calls_with_competitor_mentions": calls_with_competitor_mentions,
            "competitor_mention_rate_percent": round(competitor_mention_rate, 1),
            "switching_intent_rate_percent": round(switching_intent_rate, 1),
            "switching_intent_count": switching_intent_count,
            "top_competitors": [{"name": c, "mentions": m} for c, m in top_competitors],
            "top_comparison_requests": [{"comparison": c, "count": cnt} for c, cnt in top_comparisons],
            "price_sensitivity_distribution": price_sensitivity
        }

    except Exception as e:
        print(f"Error getting competitive intelligence: {e}")
        return {
            "total_calls": 0,
            "calls_with_competitor_mentions": 0,
            "competitor_mention_rate_percent": 0,
            "switching_intent_rate_percent": 0,
            "switching_intent_count": 0,
            "top_competitors": [],
            "top_comparison_requests": [],
            "price_sensitivity_distribution": {}
        }


@router.get("/product-analytics")
async def get_product_analytics(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get product and feature analytics from calls.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with product analytics
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(product_analytics)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        products_discussed = {}
        features_requested = {}
        features_problematic = {}
        upsell_opportunities = 0
        cross_sell_suggestions = {}

        for call in calls:
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]
                if isinstance(analytics, dict):
                    pa = analytics.get("product_analytics", {})
                    if isinstance(pa, dict):
                        # Products discussed
                        for product in pa.get("products_discussed", []):
                            products_discussed[product] = products_discussed.get(product, 0) + 1

                        # Features requested
                        for feature in pa.get("features_requested", []):
                            features_requested[feature] = features_requested.get(feature, 0) + 1

                        # Problematic features
                        for feature in pa.get("features_problematic", []):
                            features_problematic[feature] = features_problematic.get(feature, 0) + 1

                        # Upsell opportunities
                        if pa.get("upsell_opportunity_detected"):
                            upsell_opportunities += 1

                        # Cross-sell suggestions
                        for suggestion in pa.get("cross_sell_suggestions", []):
                            cross_sell_suggestions[suggestion] = cross_sell_suggestions.get(suggestion, 0) + 1

        total_calls = len(calls)
        upsell_rate = (upsell_opportunities / total_calls * 100) if total_calls > 0 else 0

        # Sort and get top items
        top_products = sorted(products_discussed.items(), key=lambda x: x[1], reverse=True)[:10]
        top_features_requested = sorted(features_requested.items(), key=lambda x: x[1], reverse=True)[:10]
        top_features_problematic = sorted(features_problematic.items(), key=lambda x: x[1], reverse=True)[:10]
        top_cross_sell = sorted(cross_sell_suggestions.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_calls": total_calls,
            "upsell_opportunities": upsell_opportunities,
            "upsell_opportunity_rate_percent": round(upsell_rate, 1),
            "top_products_discussed": [{"product": p, "mentions": m} for p, m in top_products],
            "top_features_requested": [{"feature": f, "requests": r} for f, r in top_features_requested],
            "top_problematic_features": [{"feature": f, "issues": i} for f, i in top_features_problematic],
            "top_cross_sell_suggestions": [{"suggestion": s, "count": c} for s, c in top_cross_sell]
        }

    except Exception as e:
        print(f"Error getting product analytics: {e}")
        return {
            "total_calls": 0,
            "upsell_opportunities": 0,
            "upsell_opportunity_rate_percent": 0,
            "top_products_discussed": [],
            "top_features_requested": [],
            "top_problematic_features": [],
            "top_cross_sell_suggestions": []
        }


@router.get("/conversation-quality")
async def get_conversation_quality_analytics(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get conversation quality metrics across calls.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with conversation quality data
        result = supabase.table("supportiq_voice_calls").select(
            "id, started_at, supportiq_call_analytics(conversation_quality, handle_time_breakdown)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        clarity_scores = []
        empathy_counts = []
        jargon_counts = []
        response_times = []
        agent_wpm = []
        customer_wpm = []
        talk_percentages = []
        hold_times = []

        for call in calls:
            analytics = call.get("supportiq_call_analytics")
            if analytics:
                if isinstance(analytics, list) and analytics:
                    analytics = analytics[0]
                if isinstance(analytics, dict):
                    # Conversation quality
                    cq = analytics.get("conversation_quality", {})
                    if isinstance(cq, dict):
                        if cq.get("clarity_score"):
                            clarity_scores.append(cq["clarity_score"])
                        if cq.get("empathy_phrases_count"):
                            empathy_counts.append(cq["empathy_phrases_count"])
                        if cq.get("jargon_usage_count") is not None:
                            jargon_counts.append(cq["jargon_usage_count"])
                        if cq.get("avg_agent_response_time_seconds"):
                            response_times.append(cq["avg_agent_response_time_seconds"])
                        if cq.get("words_per_minute_agent"):
                            agent_wpm.append(cq["words_per_minute_agent"])
                        if cq.get("words_per_minute_customer"):
                            customer_wpm.append(cq["words_per_minute_customer"])

                    # Handle time breakdown
                    ht = analytics.get("handle_time_breakdown", {})
                    if isinstance(ht, dict):
                        if ht.get("agent_talk_percentage"):
                            talk_percentages.append(ht["agent_talk_percentage"])
                        if ht.get("hold_time_seconds"):
                            hold_times.append(ht["hold_time_seconds"])

        total_calls = len(calls)

        return {
            "total_calls": total_calls,
            "average_clarity_score": round(sum(clarity_scores) / len(clarity_scores), 1) if clarity_scores else 0,
            "average_empathy_phrases": round(sum(empathy_counts) / len(empathy_counts), 1) if empathy_counts else 0,
            "average_jargon_usage": round(sum(jargon_counts) / len(jargon_counts), 1) if jargon_counts else 0,
            "average_response_time_seconds": round(sum(response_times) / len(response_times), 1) if response_times else 0,
            "average_agent_wpm": round(sum(agent_wpm) / len(agent_wpm), 0) if agent_wpm else 0,
            "average_customer_wpm": round(sum(customer_wpm) / len(customer_wpm), 0) if customer_wpm else 0,
            "average_agent_talk_percentage": round(sum(talk_percentages) / len(talk_percentages), 1) if talk_percentages else 50,
            "average_hold_time_seconds": round(sum(hold_times) / len(hold_times), 0) if hold_times else 0,
            "calls_with_high_clarity": len([s for s in clarity_scores if s >= 80]),
            "calls_with_low_clarity": len([s for s in clarity_scores if s < 60])
        }

    except Exception as e:
        print(f"Error getting conversation quality analytics: {e}")
        return {
            "total_calls": 0,
            "average_clarity_score": 0,
            "average_empathy_phrases": 0,
            "average_jargon_usage": 0,
            "average_response_time_seconds": 0,
            "average_agent_wpm": 0,
            "average_customer_wpm": 0,
            "average_agent_talk_percentage": 50,
            "average_hold_time_seconds": 0,
            "calls_with_high_clarity": 0,
            "calls_with_low_clarity": 0
        }


@router.get("/agent-performance-summary")
async def get_agent_performance_summary(
    days: int = Query(30, ge=1, le=90),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get aggregated agent performance metrics.
    """
    try:
        supabase = get_supabase()
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get calls with agent performance
        result = supabase.table("supportiq_voice_calls").select(
            "id, supportiq_agent_performance(*)"
        ).eq("caller_id", current_user.user_id).gte(
            "started_at", start_date.isoformat()
        ).execute()

        calls = result.data or []

        # Aggregate performance
        all_scores = {
            "overall": [],
            "empathy": [],
            "knowledge": [],
            "communication": [],
            "efficiency": [],
            "opening": [],
            "closing": []
        }

        all_strengths = {}
        all_improvements = {}
        all_training = {}

        for call in calls:
            perf = call.get("supportiq_agent_performance")
            if perf:
                if isinstance(perf, list) and perf:
                    perf = perf[0]
                elif not isinstance(perf, dict):
                    continue

                if perf.get("overall_score"):
                    all_scores["overall"].append(perf["overall_score"])
                if perf.get("empathy_score"):
                    all_scores["empathy"].append(perf["empathy_score"])
                if perf.get("knowledge_score"):
                    all_scores["knowledge"].append(perf["knowledge_score"])
                if perf.get("communication_score"):
                    all_scores["communication"].append(perf["communication_score"])
                if perf.get("efficiency_score"):
                    all_scores["efficiency"].append(perf["efficiency_score"])
                if perf.get("opening_quality"):
                    all_scores["opening"].append(perf["opening_quality"])
                if perf.get("closing_quality"):
                    all_scores["closing"].append(perf["closing_quality"])

                for s in (perf.get("strengths") or []):
                    all_strengths[s] = all_strengths.get(s, 0) + 1
                for i in (perf.get("areas_for_improvement") or []):
                    all_improvements[i] = all_improvements.get(i, 0) + 1
                for t in (perf.get("training_recommendations") or []):
                    all_training[t] = all_training.get(t, 0) + 1

        # Calculate averages
        avg_scores = {
            key: sum(vals) / len(vals) if vals else 0.0
            for key, vals in all_scores.items()
        }

        # Sort and get top items
        top_strengths = sorted(all_strengths.items(), key=lambda x: x[1], reverse=True)[:5]
        top_improvements = sorted(all_improvements.items(), key=lambda x: x[1], reverse=True)[:5]
        top_training = sorted(all_training.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_calls_analyzed": len([c for c in calls if c.get("supportiq_agent_performance")]),
            "average_scores": avg_scores,
            "top_strengths": [{"text": s[0], "count": s[1]} for s in top_strengths],
            "top_areas_for_improvement": [{"text": i[0], "count": i[1]} for i in top_improvements],
            "top_training_recommendations": [{"text": t[0], "count": t[1]} for t in top_training]
        }

    except Exception as e:
        print(f"Error getting agent performance summary: {e}")
        return {
            "total_calls_analyzed": 0,
            "average_scores": {},
            "top_strengths": [],
            "top_areas_for_improvement": [],
            "top_training_recommendations": []
        }
