from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.upload import router as upload_router
from app.config import get_settings


settings = get_settings()
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RAG Notebook", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
