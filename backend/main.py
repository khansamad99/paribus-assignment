from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import hospitals
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="A high-performance bulk processing system for hospital records with concurrent processing, real-time progress tracking, and enhanced CSV validation",
    version=settings.APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals.router, prefix="/hospitals", tags=["hospitals"])

@app.get("/")
async def root():
    return {"message": "Hospital Bulk Processing API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}