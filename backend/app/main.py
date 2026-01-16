from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, progress, admin, users, knowledge, chat, vapi, voice_calls, analytics, tickets

app = FastAPI(
    title="SupportIQ Onboarding API",
    description="Backend API for SupportIQ user onboarding wizard",
    version="1.0.0",
)

# CORS middleware - includes localhost for dev and production URL from env
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(progress.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(vapi.router, prefix="/api/v1")
app.include_router(voice_calls.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "SupportIQ Onboarding API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
