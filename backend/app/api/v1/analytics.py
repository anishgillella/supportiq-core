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
