from fastapi import FastAPI

from backend.app.routers import health, summaries


app = FastAPI(title="Radiohead Backend API", version="0.1.0")

app.include_router(health.router)
app.include_router(summaries.router)
