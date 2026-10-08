from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import health, search

app = FastAPI(title=settings.app_name)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health.router, prefix="/api")
app.include_router(search.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.app_name} API"}
