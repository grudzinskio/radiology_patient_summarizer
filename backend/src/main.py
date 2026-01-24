import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from routers import health, summaries


app = FastAPI(title="Radiohead Backend API", version="0.1.0")

# Redirect to docs for FastAPI noobs
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app.include_router(health.router)
app.include_router(summaries.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
