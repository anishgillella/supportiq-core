from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, progress, admin, users, knowledge, chat

app = FastAPI(
    title="SupportIQ Onboarding API",
    description="Backend API for SupportIQ user onboarding wizard",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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


@app.get("/")
async def root():
    return {"message": "SupportIQ Onboarding API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
