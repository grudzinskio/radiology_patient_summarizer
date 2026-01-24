import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from routers import health, summaries
from services.summaries.entity_extraction.spacy import SpacyComponent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    logger.info("Loading heavy NLP models...")
    # Load the heavy NLP model at startup
    SpacyComponent.load_model()
    logger.info("Startup complete. Application ready.")
    yield
    logger.info("Application shutting down...")
    # Clean up if needed (not needed for this)



app = FastAPI(title="Radiohead Backend API", version="0.1.0", lifespan=lifespan)

# Redirect to docs for FastAPI noobs
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app.include_router(health.router)
app.include_router(summaries.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
