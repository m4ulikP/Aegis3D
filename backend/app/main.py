from fastapi import FastAPI

from app.api import api_router

app = FastAPI(
    title="Aegis3D Backend API",
    description="Generic Structural Event & Health Monitoring Platform API",
    version="0.1.0",
)

app.include_router(api_router)
