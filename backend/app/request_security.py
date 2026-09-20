from fastapi import HTTPException, Request, status

from .config import settings


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def validate_request_origin(request: Request) -> None:
    if request.method in SAFE_METHODS or not request.url.path.startswith("/api/"):
        return
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = {item.strip().rstrip("/") for item in settings.allowed_origins.split(",") if item.strip()}
    if origin.rstrip("/") not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origine de requête non autorisée")
