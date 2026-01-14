from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # CORS
    frontend_url: str = "http://localhost:3000"

    # AI/LLM Configuration
    openrouter_api_key: str = ""
    openai_api_key: str = ""  # For embeddings
    pinecone_api_key: str = ""
    pinecone_host: str = "https://supportiq-h9p6mw5.svc.aped-4627-b74a.pinecone.io"
    pinecone_index_name: str = "supportiq"

    # Parallel AI (for website scraping)
    parallel_api_key: str = ""

    # Model settings
    llm_model: str = "anthropic/claude-3.5-sonnet"  # OpenRouter model
    embedding_model: str = "text-embedding-3-small"  # OpenAI embedding model
    embedding_dimensions: int = 1024  # Must match Pinecone index dimensions

    # VAPI Configuration
    vapi_api_key: str = ""
    vapi_public_key: str = ""
    vapi_assistant_id: str = ""

    # Analysis model (for transcript analysis)
    analysis_model: str = "google/gemini-2.5-flash-preview"

    class Config:
        env_file = "/Users/anishgillella/conductor/workspaces/supportiq-core/.env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
