from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import hospitals

app = FastAPI(
    title="Hospital Bulk Processing API",
    description="A bulk processing system for hospital records",
    version="1.0.0"
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