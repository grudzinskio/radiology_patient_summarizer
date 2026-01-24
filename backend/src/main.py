import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from contextlib import asynccontextmanager
from routers import health, summaries
from services.summaries.entity_extraction.pipeline_components.spacy_component import SpacyComponent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the heavy NLP model at startup
    SpacyComponent.load_model()
    yield
    # Clean up if needed (not needed for this)


app = FastAPI(title="Radiohead Backend API", version="0.1.0", lifespan=lifespan)

# Redirect to docs for FastAPI noobs
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app.include_router(health.router)
app.include_router(summaries.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
