from supabase import create_client, Client
from .config import settings

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("Supabase URL and Key must be set in environment variables")
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def get_supabase_admin() -> Client:
    """Get Supabase client with service role key for admin operations"""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase URL and Service Key must be set")
    return create_client(settings.supabase_url, settings.supabase_service_key)
