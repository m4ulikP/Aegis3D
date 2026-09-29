import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router

app = FastAPI(
    title="Aegis3D Backend API",
    description="Generic Structural Event & Health Monitoring Platform API",
    version="0.1.0",
)

# Configure CORS for Next.js frontend: http://localhost:3000 by default, plus optional LAN/remote origins from env
default_origins = ["http://localhost:3000"]
env_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
origins = list(dict.fromkeys(default_origins + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
