"""
Analytics API Router

Endpoints for retrieving aggregated analytics and dashboard data.
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_supabase
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
    AgentLeaderboard
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get comprehensive analytics dashboard data.
    """
    supabase = get_supabase()
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get calls with analytics
    result = supabase.table("supportiq_voice_calls").select(
        "*, supportiq_call_analytics(*)"
    ).gte("started_at", start_date.isoformat()).order(
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

    # Customer insights (aggregate pain points, feature requests, etc.)
    # This would need the full analysis stored - for now, we'll use placeholders
    customer_insights = CustomerInsightsSummary(
        total_unique_customers=total_calls,  # Simplified - each call = 1 customer for now
        repeat_caller_rate=0.0,
        avg_calls_per_customer=1.0,
        top_pain_points=[],
        top_feature_requests=[],
        top_complaints=[],
        high_risk_customers=0,
        avg_churn_risk=0.0
    )

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
