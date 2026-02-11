from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.upload import router as upload_router
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.services.auth_service import decode_session_token


app = FastAPI(title="RAG Notebook", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    settings = get_settings()
    token = request.cookies.get(settings.jwt_cookie_name)
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    try:
        payload = decode_session_token(token)
        user_id = payload.get("sub")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse("index.html", {"request": request, "user_email": user.email})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
