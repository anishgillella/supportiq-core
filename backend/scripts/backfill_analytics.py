#!/usr/bin/env python3
"""
Backfill Analytics Script

Processes existing calls that don't have analytics and/or tickets.
Runs the full analysis pipeline including:
- Transcript analysis (2-call LLM architecture)
- Ticket creation
- Customer profile updates
- Daily analytics aggregation
- Feedback aggregation

Usage:
    # Dry run - see what would be processed
    python -m scripts.backfill_analytics --dry-run

    # Process all calls without analytics
    python -m scripts.backfill_analytics

    # Process with limit
    python -m scripts.backfill_analytics --limit 50

    # Process specific user's calls only
    python -m scripts.backfill_analytics --user-id <uuid>

    # Force reprocess (delete existing analytics first)
    python -m scripts.backfill_analytics --force

    # Adjust concurrency
    python -m scripts.backfill_analytics --concurrency 3
"""

import asyncio
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, "/Users/anishgillella/conductor/workspaces/supportiq-core/irvine-v2/backend")

from app.core.database import get_supabase
from app.services.transcript_analysis import analyze_transcript


async def get_calls_without_analytics(
    user_id: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all calls that don't have analytics records.

    Returns calls with their transcripts and user info.
    """
    supabase = get_supabase()

    # Get all call IDs that already have analytics
    analytics_result = supabase.table("supportiq_call_analytics").select("call_id").execute()
    analyzed_call_ids = {row["call_id"] for row in (analytics_result.data or [])}

    # Build query for calls
    query = supabase.table("supportiq_voice_calls").select(
        "id, caller_id, caller_phone, status, started_at, ended_at, duration_seconds"
    ).eq("status", "completed")  # Only process completed calls

    if user_id:
        query = query.eq("caller_id", user_id)

    # Order by oldest first so we process in chronological order
    query = query.order("started_at", desc=False)

    if limit:
        # Fetch more than limit since we'll filter out analyzed ones
        query = query.limit(limit * 2)

    calls_result = query.execute()

    if not calls_result.data:
        return []

    # Filter out calls that already have analytics
    unanalyzed_calls = [
        call for call in calls_result.data
        if call["id"] not in analyzed_call_ids
    ]

    if limit:
        unanalyzed_calls = unanalyzed_calls[:limit]

    return unanalyzed_calls


async def get_calls_without_tickets(
    user_id: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all calls that have analytics but don't have tickets.
    """
    supabase = get_supabase()

    # Get all call IDs that already have tickets
    tickets_result = supabase.table("supportiq_tickets").select("call_id").execute()
    ticketed_call_ids = {row["call_id"] for row in (tickets_result.data or [])}

    # Get calls with analytics but no tickets
    query = supabase.table("supportiq_call_analytics").select(
        "call_id"
    )

    analytics_result = query.execute()

    if not analytics_result.data:
        return []

    # Filter to calls without tickets
    calls_needing_tickets = [
        {"id": row["call_id"]} for row in analytics_result.data
        if row["call_id"] not in ticketed_call_ids
    ]

    if user_id:
        # Further filter by user_id
        valid_call_ids = set()
        for call in calls_needing_tickets:
            call_result = supabase.table("supportiq_voice_calls").select("id").eq(
                "id", call["id"]
            ).eq("caller_id", user_id).execute()
            if call_result.data:
                valid_call_ids.add(call["id"])

        calls_needing_tickets = [c for c in calls_needing_tickets if c["id"] in valid_call_ids]

    if limit:
        calls_needing_tickets = calls_needing_tickets[:limit]

    return calls_needing_tickets


async def get_transcript_for_call(call_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get transcript messages for a call."""
    supabase = get_supabase()

    result = supabase.table("supportiq_call_transcripts").select(
        "transcript"
    ).eq("call_id", call_id).execute()

    if result.data and result.data[0].get("transcript"):
        return result.data[0]["transcript"]

    return None


async def get_user_info(user_id: str) -> Dict[str, Any]:
    """Get user email and name for a user ID."""
    supabase = get_supabase()

    result = supabase.table("supportiq_users").select(
        "email, company_name"
    ).eq("id", user_id).execute()

    if result.data:
        return {
            "email": result.data[0].get("email"),
            "name": result.data[0].get("company_name")
        }

    return {"email": None, "name": None}


async def process_call(
    call: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    stats: Dict[str, int]
) -> bool:
    """
    Process a single call through the analysis pipeline.

    Returns True if successful, False otherwise.
    """
    call_id = call["id"]
    user_id = call.get("caller_id")

    async with semaphore:
        try:
            # Get transcript
            transcript = await get_transcript_for_call(call_id)

            if not transcript:
                print(f"  [SKIP] Call {call_id[:8]}... has no transcript")
                stats["skipped"] += 1
                return False

            if len(transcript) < 2:
                print(f"  [SKIP] Call {call_id[:8]}... has insufficient transcript ({len(transcript)} messages)")
                stats["skipped"] += 1
                return False

            # Get user info
            user_info = {"email": None, "name": None}
            if user_id:
                user_info = await get_user_info(user_id)

            print(f"  [PROCESSING] Call {call_id[:8]}... ({len(transcript)} messages)")

            # Run analysis
            result = await analyze_transcript(
                call_id=call_id,
                transcript_messages=transcript,
                user_id=user_id,
                user_email=user_info["email"],
                user_name=user_info["name"]
            )

            if result:
                print(f"  [SUCCESS] Call {call_id[:8]}... analyzed successfully")
                stats["success"] += 1
                return True
            else:
                print(f"  [FAILED] Call {call_id[:8]}... analysis returned None")
                stats["failed"] += 1
                return False

        except Exception as e:
            print(f"  [ERROR] Call {call_id[:8]}... - {str(e)}")
            stats["failed"] += 1
            return False


async def backfill_analytics(
    dry_run: bool = False,
    limit: Optional[int] = None,
    user_id: Optional[str] = None,
    force: bool = False,
    concurrency: int = 5
):
    """
    Main backfill function.

    Args:
        dry_run: If True, only show what would be processed
        limit: Maximum number of calls to process
        user_id: Only process calls for this user
        force: If True, reprocess calls that already have analytics
        concurrency: Maximum number of parallel LLM calls
    """
    print("\n" + "=" * 60)
    print("SupportIQ Analytics Backfill Script")
    print("=" * 60)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Concurrency: {concurrency}")
    if limit:
        print(f"Limit: {limit} calls")
    if user_id:
        print(f"User filter: {user_id}")
    if force:
        print("Force mode: Will reprocess existing analytics")
    print()

    supabase = get_supabase()

    # Get calls to process
    if force:
        # Get all completed calls
        query = supabase.table("supportiq_voice_calls").select(
            "id, caller_id, caller_phone, status, started_at, ended_at, duration_seconds"
        ).eq("status", "completed").order("started_at", desc=False)

        if user_id:
            query = query.eq("caller_id", user_id)
        if limit:
            query = query.limit(limit)

        result = query.execute()
        calls_to_process = result.data or []
    else:
        calls_to_process = await get_calls_without_analytics(user_id, limit)

    total_calls = len(calls_to_process)

    print(f"Found {total_calls} calls to process")

    if total_calls == 0:
        print("\nNo calls need processing. All calls already have analytics!")
        return

    # Show sample of calls in dry run
    if dry_run:
        print("\nCalls that would be processed:")
        print("-" * 40)
        for i, call in enumerate(calls_to_process[:10]):
            started = call.get("started_at", "unknown")[:19] if call.get("started_at") else "unknown"
            duration = call.get("duration_seconds", 0) or 0
            print(f"  {i+1}. {call['id'][:8]}... | {started} | {duration}s")

        if total_calls > 10:
            print(f"  ... and {total_calls - 10} more")

        print("\nTo process these calls, run without --dry-run flag")
        return

    # Process calls with progress tracking
    print("\nProcessing calls...")
    print("-" * 40)

    semaphore = asyncio.Semaphore(concurrency)
    stats = {"success": 0, "failed": 0, "skipped": 0}

    # If force mode, delete existing analytics first
    if force:
        print("\nDeleting existing analytics for reprocessing...")
        for call in calls_to_process:
            try:
                supabase.table("supportiq_call_analytics").delete().eq("call_id", call["id"]).execute()
                supabase.table("supportiq_tickets").delete().eq("call_id", call["id"]).execute()
            except Exception as e:
                print(f"  Warning: Could not delete existing data for {call['id'][:8]}...: {e}")

    # Process in batches for better progress visibility
    batch_size = 10
    for batch_start in range(0, total_calls, batch_size):
        batch_end = min(batch_start + batch_size, total_calls)
        batch = calls_to_process[batch_start:batch_end]

        print(f"\nBatch {batch_start // batch_size + 1}/{(total_calls + batch_size - 1) // batch_size} (calls {batch_start + 1}-{batch_end})")

        # Process batch with controlled concurrency
        tasks = [
            process_call(call, semaphore, stats)
            for call in batch
        ]

        await asyncio.gather(*tasks)

        # Progress update
        processed = stats["success"] + stats["failed"] + stats["skipped"]
        print(f"\nProgress: {processed}/{total_calls} ({processed * 100 // total_calls}%)")
        print(f"  Success: {stats['success']} | Failed: {stats['failed']} | Skipped: {stats['skipped']}")

    # Final summary
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nResults:")
    print(f"  Total calls processed: {total_calls}")
    print(f"  Successful: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Skipped (no transcript): {stats['skipped']}")

    if stats["failed"] > 0:
        print(f"\n⚠️  {stats['failed']} calls failed to process. Check logs for details.")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill analytics and tickets for existing calls"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of calls to process"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Only process calls for this user ID"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess calls even if they already have analytics"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Maximum number of parallel LLM calls (default: 5)"
    )

    args = parser.parse_args()

    # Run the backfill
    asyncio.run(backfill_analytics(
        dry_run=args.dry_run,
        limit=args.limit,
        user_id=args.user_id,
        force=args.force,
        concurrency=args.concurrency
    ))


if __name__ == "__main__":
    main()
